"""``/reload-model`` endpoint: hot-swaps the serving model set after a retrain.

``retrain.py`` overwrites the ``.pkl`` files and then POSTs here (authenticated
with the internal shared secret) so the running API picks up the new model
without a restart. The swap targets the shared ``serving_state.STATE`` that
``/predict`` and ``/importance`` actually read, and the response reports a
monotonically increasing version so the caller can confirm the swap landed.
"""

import hmac
import os

from   flask                    import jsonify, request

import serving_state

__all__ = ["register_reload_endpoint"]


def _short_checksum(snapshot):
    """Short model checksum for a snapshot, or ``"unknown"`` when unavailable."""
    metadata = getattr(snapshot, "metadata", None)
    return metadata.short_checksum if metadata is not None else "unknown"


def register_reload_endpoint(app):
    """Attach ``/reload-model`` and ``/model-status`` to ``app``."""

    @app.route("/reload-model", methods=["POST"])
    @idempotent
    def reload_model():
        provided = request.headers.get("X-Internal-Secret", "")
        internal_secret = os.getenv("INTERNAL_SECRET", "")
        # Timing-safe compare so the secret can't be recovered byte-by-byte.
        if not internal_secret or not hmac.compare_digest(provided, internal_secret):
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Invalid or missing internal secret",
                    }
                ),
                401,
            )

        previous = serving_state.STATE.snapshot()
        try:
            snapshot = serving_state.STATE.reload()
        except Exception as e:
            app.logger.exception("Model reload failed")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Failed to reload models: {e}",
                    }
                ),
                500,
            )

        # Structured provenance audit line (issue #1007 part 2) so a reload is
        # traceable in the logs: which version bump, and which model bytes went
        # in and out. "unknown" covers snapshots taken before metadata existed.
        old_checksum = _short_checksum(previous)
        new_checksum = _short_checksum(snapshot)
        app.logger.info(
            "model reloaded v%d -> v%d (checksum %s -> %s)",
            previous.version,
            snapshot.version,
            old_checksum,
            new_checksum,
        )

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Models reloaded successfully",
                    "version": snapshot.version,
                }
            ),
            200,
        )

    @app.route("/model-status", methods=["GET"])
    def model_status():
        snapshot = serving_state.STATE.snapshot()
        return (
            jsonify(
                {
                    "version": snapshot.version,
                    "model_loaded": snapshot.model is not None,
                    "vectorizer_loaded": snapshot.vectorizer is not None,
                    "label_encoder_loaded": snapshot.label_encoder is not None,
                }
            ),
            200,
        )

    return app

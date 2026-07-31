"""Coverage for the model registry and /model-info (issue #1007, part 1).

The pure ``build_metadata`` tests fingerprint temp files and need no ML deps.
The /model-info shape test imports ``api`` lazily and skips when the app can't
be imported (e.g. an environment missing an optional model/threat-intel dep).
"""

import hashlib
import json
import os
from   pathlib                  import Path
import sys

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

os.environ.setdefault("MODEL_PATH", str(BASE_DIR / "linear_svm_model.pkl"))
os.environ.setdefault("VECTORIZER_PATH", str(BACKEND_DIR / "tfidf_vectorizer.pkl"))
os.environ.setdefault("LABEL_ENCODER_PATH", str(BASE_DIR / "label_encoder.pkl"))
os.environ.setdefault("URL_MODEL_PATH", str(BACKEND_DIR / "url_detector.pkl"))
os.environ.setdefault("URL_VECTORIZER_PATH", str(BACKEND_DIR / "url_vectorizer.pkl"))

sys.path.insert(0, str(BACKEND_DIR))

import model_registry # noqa: E402


def _make_artifacts(root, *, model=b"model-v1", vec=b"vec-v1", le=b"le-v1"):
    """Write the three artifact files under ``root`` and return their paths."""
    model_path = root / "linear_svm_model.pkl"
    vec_path = root / "tfidf_vectorizer.pkl"
    le_path = root / "label_encoder.pkl"
    model_path.write_bytes(model)
    vec_path.write_bytes(vec)
    le_path.write_bytes(le)
    return model_path, vec_path, le_path


def _build(model_path, vec_path, le_path):
    return model_registry.build_metadata(
        model_path=str(model_path),
        vectorizer_path=str(vec_path),
        label_encoder_path=str(le_path),
    )


class TestBuildMetadata:
    def test_checksums_match_sha256_and_are_stable(self, tmp_path):
        model_path, vec_path, le_path = _make_artifacts(tmp_path)

        first = _build(model_path, vec_path, le_path)
        second = _build(model_path, vec_path, le_path)

        assert first.model.sha256 == hashlib.sha256(b"model-v1").hexdigest()
        # Identical bytes -> identical checksums across independent builds.
        assert first.checksums == second.checksums
        assert first.short_checksum == first.model.sha256[:12]
        assert first.model.size_bytes == len(b"model-v1")

    def test_checksum_varies_when_bytes_change(self, tmp_path):
        model_path, vec_path, le_path = _make_artifacts(tmp_path)
        before = _build(model_path, vec_path, le_path)

        model_path.write_bytes(b"model-v2-retrained")
        after = _build(model_path, vec_path, le_path)

        assert after.model.sha256 != before.model.sha256
        assert after.short_checksum != before.short_checksum
        # Untouched artifacts keep their fingerprints.
        assert after.vectorizer.sha256 == before.vectorizer.sha256

    def test_reads_model_card_sidecar_when_present(self, tmp_path):
        model_path, vec_path, le_path = _make_artifacts(tmp_path)
        card = {
            "trained_at": "2026-07-20T12:00:00Z",
            "metrics": {"accuracy": 0.98},
            "labels": ["ham", "spam", "smishing"],
        }
        (tmp_path / model_registry.MODEL_CARD_FILENAME).write_text(json.dumps(card))

        meta = _build(model_path, vec_path, le_path)

        assert meta.trained_at == "2026-07-20T12:00:00Z"
        assert meta.metrics == {"accuracy": 0.98}
        assert meta.labels == ["ham", "spam", "smishing"]

    def test_missing_model_card_leaves_fields_none(self, tmp_path):
        meta = _build(*_make_artifacts(tmp_path))

        assert meta.trained_at is None
        assert meta.metrics is None
        assert meta.labels is None

    def test_malformed_model_card_is_tolerated(self, tmp_path):
        model_path, vec_path, le_path = _make_artifacts(tmp_path)
        (tmp_path / model_registry.MODEL_CARD_FILENAME).write_text("{ not json")

        meta = _build(model_path, vec_path, le_path)

        # Provenance is advisory; a broken card must not break fingerprinting.
        assert meta.trained_at is None
        assert meta.checksums["model"] == hashlib.sha256(b"model-v1").hexdigest()

    def test_to_dict_is_json_serialisable_and_complete(self, tmp_path):
        meta = _build(*_make_artifacts(tmp_path))
        as_dict = meta.to_dict()

        json.dumps(as_dict)  # must not raise
        assert set(as_dict) >= {
            "model",
            "vectorizer",
            "label_encoder",
            "short_checksum",
            "trained_at",
            "metrics",
            "labels",
        }


@pytest.fixture
def client():
    try:
        import api as api_module  # noqa: E402
    except Exception as exc:  # pragma: no cover - env without ML deps/models
        pytest.skip(f"api import unavailable: {exc}")
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c


class TestModelInfoEndpoint:
    def test_model_info_is_public_and_well_shaped(self, client):
        res = client.get("/model-info")
        assert res.status_code == 200

        body = res.get_json()
        assert set(body) == {"version", "checksums", "metadata"}
        assert isinstance(body["version"], int)
        assert set(body["checksums"]) == {"model", "vectorizer", "label_encoder"}
        assert body["metadata"]["short_checksum"] == body["checksums"]["model"][:12]

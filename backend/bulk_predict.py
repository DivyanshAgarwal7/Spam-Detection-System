"""Bulk file prediction endpoints (issue #1021).

Scoring runs against a single :class:`serving_state.ServingSnapshot` taken at the
start of each request, so an in-flight ``/reload-model`` hot-swap can never pair
a new model with an old vectorizer part-way through a file. Inference is
row-isolated: an empty, over-length or un-transformable row is recorded in a
structured ``skipped`` list with a typed reason instead of aborting the whole
upload, and responses (JSON and exported CSV) carry the serving model
``version`` for provenance.

Caps are configurable via the environment, mirroring ``BULK_PREDICT_BATCH_SIZE``:
``BULK_PREDICT_MAX_ROWS`` bounds the total data rows accepted (exceeding it is a
fatal, typed error) and ``BULK_PREDICT_MAX_ROW_LEN`` bounds a single row's length
(over-length rows are skipped, not fatal).

Clients that prefer not to buffer a large result set can opt into an NDJSON
stream (``?stream=ndjson`` or ``Accept: application/x-ndjson``): the same rows
are scored and emitted one newline-delimited JSON object at a time. The default
(buffered JSON) response is unchanged.
"""

import csv
import io
import json
import os

import numpy as np

from   flask                    import (Blueprint, Response, jsonify, request,
                                        send_file, stream_with_context)

from   errors                   import ApiError, ErrorCode
from   rate_limiting            import RateLimitPolicy, rate_limit
import serving_state

__all__ = ["bulk_predict_bp"]

bulk_predict_bp = Blueprint("bulk_predict", __name__)

NDJSON_MIMETYPE = "application/x-ndjson"

# Longest row message echoed back in a skip record; full over-length payloads
# would bloat the response, so only a preview is returned for context.
_SKIP_PREVIEW_LEN = 200


def _int_env(name, default):
    """Read a positive int cap from the environment, falling back on garbage."""
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _resolve_snapshot():
    """Return a coherent serving snapshot or raise a typed, fatal error.

    A missing snapshot means the process never finished loading (or a reload is
    mid-flight with no objects installed); scoring against ``None`` would 500,
    so surface it as a typed 503 the client can branch on.
    """
    state = serving_state.STATE
    snapshot = state.snapshot() if state is not None else None
    if (
        snapshot is None
        or snapshot.model is None
        or snapshot.vectorizer is None
        or snapshot.label_encoder is None
    ):
        raise ApiError(
            ErrorCode.BULK_MODEL_UNAVAILABLE,
            "Model dependencies are not loaded.",
            503,
        )
    return snapshot


def _wants_ndjson():
    """True when the caller opted into the NDJSON streaming response."""
    if request.args.get("stream", "").lower() == "ndjson":
        return True
    accept = request.headers.get("Accept", "")
    return NDJSON_MIMETYPE in accept.lower()


def _skip_record(index, message, code, detail):
    return {
        "row": index,
        "message": (message or "")[:_SKIP_PREVIEW_LEN],
        "reason": code.value,
        "detail": detail,
    }


def _extract_rows(file):
    """Return ``(rows, error)`` where rows is a list of ``(index, raw_value)``.

    ``index`` is the 1-based data-row position (useful for the client to locate
    a skipped row); ``raw_value`` may be ``None``/blank and is validated later.
    Fatal, file-level problems (bad type, size, structure) come back as the
    ``error`` string so the caller can map them to the legacy status codes.
    """
    filename = file.filename.lower() if file.filename else ""
    if not (filename.endswith(".csv") or filename.endswith(".txt")):
        return None, "Unsupported file type. Only CSV and TXT files are supported."

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 2 * 1024 * 1024:  # 2MB limit
        return None, "File size exceeds the limit of 2MB."
    if file_size == 0:
        return None, "Empty file uploaded."

    try:
        text_wrapper = io.TextIOWrapper(file.stream, encoding="utf-8", errors="replace")
    except Exception:
        return None, "Failed to read uploaded file."

    rows = []
    if filename.endswith(".csv"):
        try:
            reader = csv.DictReader(text_wrapper)
            fieldnames = reader.fieldnames
            if not fieldnames:
                return None, "Invalid CSV file structure or missing headers."
            col_name = None
            for h in fieldnames:
                if h and h.strip().lower() in ("text", "message"):
                    col_name = h
                    break
            if not col_name:
                return (
                    None,
                    "CSV file must contain either a 'text' or 'message' column.",
                )
            for index, row in enumerate(reader, start=1):
                rows.append((index, row.get(col_name)))
        except Exception as e:
            return None, f"Failed to parse CSV: {str(e)}"
    else:  # TXT file: one message per non-blank line.
        index = 0
        for line in text_wrapper:
            stripped = line.strip()
            if not stripped:
                continue
            index += 1
            rows.append((index, stripped))

    return rows, None


def _partition_rows(rows, max_row_len):
    """Split extracted rows into scorable rows and typed per-row skips."""
    valid_rows = []
    skipped = []
    for index, value in rows:
        if value is None or not value.strip():
            skipped.append(
                _skip_record(
                    index, value, ErrorCode.BULK_ROW_EMPTY, "Empty row skipped."
                )
            )
            continue
        msg = value.strip()
        if len(msg) > max_row_len:
            skipped.append(
                _skip_record(
                    index,
                    msg,
                    ErrorCode.BULK_ROW_TOO_LONG,
                    f"Row exceeds maximum length of {max_row_len} characters.",
                )
            )
            continue
        valid_rows.append((index, msg))
    return valid_rows, skipped


def _predict_batch(messages, snapshot):
    """Score a batch of messages against ``snapshot`` and shape the results.

    Raises on any transform/predict failure; callers isolate failures by
    retrying the offending batch one row at a time.
    """
    text_vectors = snapshot.vectorizer.transform(messages)
    predictions = snapshot.model.predict(text_vectors)
    final_outputs = snapshot.label_encoder.inverse_transform(predictions)
    decisions = snapshot.model.decision_function(text_vectors)

    batch_results = []
    for i, (msg, pred) in enumerate(zip(messages, final_outputs)):
        pred_str = str(pred)
        dec_score = float(np.max(np.abs(decisions[i])))
        prob = 1.0 / (1.0 + np.exp(-dec_score))
        conf_score = round(prob * 100, 2)

        if conf_score >= 80:
            conf_level = "high"
        elif conf_score >= 60:
            conf_level = "medium"
        else:
            conf_level = "low"

        batch_results.append(
            {
                "message": msg,
                "prediction": pred_str,
                "result": pred_str,
                "confidence": round(conf_score / 100.0, 4),
                "confidence_score": conf_score,
                "decision_score": dec_score,
                "confidence_level": conf_level,
            }
        )
    return batch_results


def _score_batch_isolated(chunk, snapshot):
    """Score one chunk, degrading to per-row scoring if the batch call fails.

    Returns ``(results, skipped)`` for the chunk so healthy rows survive a
    single poison row that would otherwise raise for the whole batch.
    """
    messages = [msg for _, msg in chunk]
    try:
        return _predict_batch(messages, snapshot), []
    except Exception:
        results = []
        skipped = []
        for index, msg in chunk:
            try:
                results.extend(_predict_batch([msg], snapshot))
            except Exception:
                skipped.append(
                    _skip_record(
                        index,
                        msg,
                        ErrorCode.BULK_ROW_UNPROCESSABLE,
                        "Row could not be transformed or scored.",
                    )
                )
        return results, skipped


def _score_rows(valid_rows, snapshot, batch_size):
    """Score pre-validated rows in batches, isolating per-row failures."""
    results = []
    skipped = []
    for start in range(0, len(valid_rows), batch_size):
        chunk = valid_rows[start : start + batch_size]
        chunk_results, chunk_skipped = _score_batch_isolated(chunk, snapshot)
        results.extend(chunk_results)
        skipped.extend(chunk_skipped)
        messages = [msg for _, msg in chunk]
        try:
            results.extend(_predict_batch(messages, snapshot))
        except Exception:
            for index, msg in chunk:
                try:
                    results.extend(_predict_batch([msg], snapshot))
                except Exception:
                    skipped.append(
                        _skip_record(
                            index,
                            msg,
                            ErrorCode.BULK_ROW_UNPROCESSABLE,
                            "Row could not be transformed or scored.",
                        )
                    )
    return results, skipped


def parse_and_predict_file(file, snapshot):
    """Parse an uploaded file and score it against ``snapshot``.

    Returns ``(results, skipped, error)``. ``error`` is a non-empty string only
    for fatal, file-level problems the legacy handlers map to 400/413; row-level
    problems never populate ``error`` -- they go into ``skipped``.
    """
    rows, error = _extract_rows(file)
    if error:
        return None, None, error
    if not rows:
        return None, None, "No valid messages found in the file."

    _enforce_row_cap(rows)

    max_row_len = _int_env("BULK_PREDICT_MAX_ROW_LEN", 10000)
    valid_rows, skipped = _partition_rows(rows, max_row_len)

    batch_size = _int_env("BULK_PREDICT_BATCH_SIZE", 256)
    results, score_skipped = _score_rows(valid_rows, snapshot, batch_size)
    skipped.extend(score_skipped)
    return results, skipped, None


def _enforce_row_cap(rows):
    max_rows = _int_env("BULK_PREDICT_MAX_ROWS", 10000)
    if len(rows) > max_rows:
        raise ApiError(
            ErrorCode.BULK_TOO_MANY_ROWS,
            f"File contains {len(rows)} rows, exceeding the limit of {max_rows}.",
            413,
        )

    max_row_len = _int_env("BULK_PREDICT_MAX_ROW_LEN", 10000)
    valid_rows = []
    skipped = []
    for index, value in rows:
        if value is None or not value.strip():
            skipped.append(
                _skip_record(
                    index, value, ErrorCode.BULK_ROW_EMPTY, "Empty row skipped."
                )
            )
            continue
        msg = value.strip()
        if len(msg) > max_row_len:
            skipped.append(
                _skip_record(
                    index,
                    msg,
                    ErrorCode.BULK_ROW_TOO_LONG,
                    f"Row exceeds maximum length of {max_row_len} characters.",
                )
            )
            continue
        valid_rows.append((index, msg))

    batch_size = _int_env("BULK_PREDICT_BATCH_SIZE", 256)
    results, score_skipped = _score_rows(valid_rows, snapshot, batch_size)
    skipped.extend(score_skipped)
    return results, skipped, None


def _summarize(results):
    total = len(results)
    spam_count = sum(
        1 for r in results if r["prediction"].lower() not in ("ham", "safe")
    )
    non_spam_count = total - spam_count
    spam_pct = round((spam_count / total) * 100, 2) if total > 0 else 0.0
    return total, spam_count, non_spam_count, spam_pct


def _iter_ndjson(rows, snapshot):
    """Yield the bulk result set as newline-delimited JSON, row by row.

    The stream opens with a ``meta`` line (model version + row count), then one
    ``result`` line per scored row, then any ``skipped`` lines, and closes with
    a ``summary`` line. Scoring is done in batches for speed but flushed a row
    at a time so the client can start consuming before the whole file is done.
    """
    max_row_len = _int_env("BULK_PREDICT_MAX_ROW_LEN", 10000)
    batch_size = _int_env("BULK_PREDICT_BATCH_SIZE", 256)
    valid_rows, skipped = _partition_rows(rows, max_row_len)

    yield json.dumps(
        {"type": "meta", "model_version": snapshot.version, "total_rows": len(rows)}
    ) + "\n"

    total = 0
    spam_count = 0
    for start in range(0, len(valid_rows), batch_size):
        chunk = valid_rows[start : start + batch_size]
        chunk_results, chunk_skipped = _score_batch_isolated(chunk, snapshot)
        skipped.extend(chunk_skipped)
        for r in chunk_results:
            total += 1
            if r["prediction"].lower() not in ("ham", "safe"):
                spam_count += 1
            yield json.dumps({"type": "result", **r}) + "\n"

    for s in skipped:
        yield json.dumps({"type": "skipped", **s}) + "\n"

    spam_pct = round((spam_count / total) * 100, 2) if total > 0 else 0.0
    yield json.dumps(
        {
            "type": "summary",
            "total_messages": total,
            "spam_count": spam_count,
            "non_spam_count": total - spam_count,
            "spam_percentage": spam_pct,
            "skipped_count": len(skipped),
            "model_version": snapshot.version,
        }
    ) + "\n"


@bulk_predict_bp.route("/bulk-predict", methods=["POST"])
@rate_limit(RateLimitPolicy.BULK)
def bulk_predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    snapshot = _resolve_snapshot()

    if _wants_ndjson():
        rows, error = _extract_rows(file)
        if error:
            status_code = 413 if "exceeds the limit" in error.lower() else 400
            return jsonify({"error": error}), status_code
        if not rows:
            return jsonify({"error": "No valid messages found in the file."}), 400
        # Enforce the row cap before opening the stream so it still surfaces as
        # a normal typed error rather than mid-stream.
        _enforce_row_cap(rows)
        return Response(
            stream_with_context(_iter_ndjson(rows, snapshot)),
            mimetype=NDJSON_MIMETYPE,
            headers={"X-Model-Version": str(snapshot.version)},
        )

    results, skipped, error = parse_and_predict_file(file, snapshot)
    if error:
        status_code = 413 if "exceeds the limit" in error.lower() else 400
        return jsonify({"error": error}), status_code

    total, spam_count, non_spam_count, spam_pct = _summarize(results)

    return jsonify(
        {
            "total_messages": total,
            "spam_count": spam_count,
            "non_spam_count": non_spam_count,
            "spam_percentage": spam_pct,
            "model_version": snapshot.version,
            "results": results,
            "skipped": skipped,
            "skipped_count": len(skipped),
        }
    )


@bulk_predict_bp.route("/bulk-predict/export", methods=["POST"])
@rate_limit(RateLimitPolicy.BULK)
def bulk_predict_export():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    snapshot = _resolve_snapshot()
    results, _skipped, error = parse_and_predict_file(file, snapshot)
    if error:
        status_code = 413 if "exceeds the limit" in error.lower() else 400
        return jsonify({"error": error}), status_code

    try:
        output_io = io.StringIO()
        writer = csv.writer(output_io)
        writer.writerow(
            [
                "message",
                "prediction",
                "result",
                "confidence_score",
                "decision_score",
                "confidence_level",
                "model_version",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r["message"],
                    r["prediction"],
                    r["result"],
                    r["confidence_score"],
                    r["decision_score"],
                    r["confidence_level"],
                    snapshot.version,
                ]
            )

        output_io.seek(0)
        mem = io.BytesIO(output_io.getvalue().encode("utf-8"))

        response = send_file(
            mem,
            mimetype="text/csv",
            as_attachment=True,
            download_name="bulk_spam_predictions.csv",
        )
        response.headers["X-Model-Version"] = str(snapshot.version)
        return response
    except Exception as e:
        return jsonify({"error": f"Failed to generate CSV report: {str(e)}"}), 500

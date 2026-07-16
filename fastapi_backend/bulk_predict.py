"""
Bulk prediction for the FastAPI backend (Issue #129).

backend/bulk_predict.py is a Flask Blueprint that reads the model/vectorizer/
label_encoder off Flask's `current_app`. That pattern doesn't exist in
FastAPI, so the FastAPI backend (fastapi_backend/main.py) never had a
/bulk-predict route at all — uploading a CSV there returns 404.

This is a native FastAPI implementation of the same feature, scoped to
fastapi_backend/ only (per maintainer note on the issue: "This just for
FastAPI as FastAPI backend folder is there"). It does not attempt to share
code with the Flask blueprint — the two frameworks handle app-level state
too differently for that to be worth it.

Model/vectorizer/label_encoder are read from `request.app.state`, which
main.py populates at startup. This mirrors what current_app did for the
Flask version, using FastAPI's own mechanism instead of a global import.

Route contract (same as backend/bulk_predict.py):
    POST /bulk-predict          -> {success, total_messages, spam_count,
                                     non_spam_count, spam_percentage, results}
    POST /bulk-predict/export   -> CSV file download
"""

import csv
import io
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["bulk-predict"])

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB — matches the limit used elsewhere in this project


def _extract_messages(filename: Optional[str], content: bytes) -> List[str]:
    """Parses uploaded bytes into a list of message strings.

    Same rules as backend/bulk_predict.py:
      - .csv: requires a 'text' or 'message' column (case-insensitive)
      - .txt: one message per non-empty line
    """
    name = (filename or "").lower()
    if not (name.endswith(".csv") or name.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Unsupported file type. Only CSV and TXT files are supported.")

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File size exceeds the limit of 2MB.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        # utf-8-sig strips a leading BOM if present (common from Excel exports
        # and Windows tools like PowerShell's `Out-File -Encoding utf8`) and
        # behaves identically to utf-8 when no BOM exists. Plain utf-8 left
        # the BOM attached to the first header cell (e.g. "\ufefftext"),
        # which silently failed the column-name match below.
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Corrupted or invalid text encoding.")

    messages: List[str] = []

    if name.endswith(".csv"):
        f = io.StringIO(text)
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise HTTPException(status_code=400, detail="Invalid CSV file structure or missing headers.")

        col_name = None
        for h in fieldnames:
            if h and h.strip().lower() in ("text", "message"):
                col_name = h
                break

        if not col_name:
            raise HTTPException(status_code=400, detail="CSV file must contain either a 'text' or 'message' column.")

        for row in reader:
            val = row.get(col_name)
            if val is not None and val.strip():
                messages.append(val.strip())
    else:
        lines = text.splitlines()
        messages = [line.strip() for line in lines if line.strip()]

    if not messages:
        raise HTTPException(status_code=400, detail="No valid messages found in the file.")

    return messages


def _predict_messages(messages: List[str], vectorizer, model, label_encoder) -> List[dict]:
    if not vectorizer or not model or not label_encoder:
        # This means main.py failed to populate app.state — a startup/config
        # problem, not a bad request, hence 500 rather than 400.
        raise HTTPException(status_code=500, detail="ML model dependencies are not loaded.")

    try:
        text_vectors = vectorizer.transform(messages)
        predictions = model.predict(text_vectors)
        final_outputs = label_encoder.inverse_transform(predictions)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model prediction error: {str(exc)}")

    return [{"message": msg, "prediction": str(pred)} for msg, pred in zip(messages, final_outputs)]


async def _read_upload(file: Optional[UploadFile]) -> bytes:
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    return await file.read()


def _get_ml_objects(request: Request):
    vectorizer = getattr(request.app.state, "vectorizer", None)
    model = getattr(request.app.state, "model", None)
    label_encoder = getattr(request.app.state, "label_encoder", None)
    return vectorizer, model, label_encoder


@router.post("/bulk-predict")
async def bulk_predict(request: Request, file: Optional[UploadFile] = File(None)):
    """Batch spam classification for a CSV or TXT upload."""
    content = await _read_upload(file)
    messages = _extract_messages(file.filename, content)

    vectorizer, model, label_encoder = _get_ml_objects(request)
    results = _predict_messages(messages, vectorizer, model, label_encoder)

    total = len(results)
    spam_count = sum(1 for r in results if r["prediction"].lower() not in ("ham", "safe"))
    non_spam_count = total - spam_count
    spam_pct = round((spam_count / total) * 100, 2) if total > 0 else 0.0

    return {
        "success": True,
        "total_messages": total,
        "spam_count": spam_count,
        "non_spam_count": non_spam_count,
        "spam_percentage": spam_pct,
        "results": results,
    }


@router.post("/bulk-predict/export")
async def bulk_predict_export(request: Request, file: Optional[UploadFile] = File(None)):
    """Same as /bulk-predict but streams the results back as a downloadable CSV."""
    content = await _read_upload(file)
    messages = _extract_messages(file.filename, content)

    vectorizer, model, label_encoder = _get_ml_objects(request)
    results = _predict_messages(messages, vectorizer, model, label_encoder)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["message", "prediction"])
    for r in results:
        writer.writerow([r["message"], r["prediction"]])
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_spam_predictions.csv"},
    )
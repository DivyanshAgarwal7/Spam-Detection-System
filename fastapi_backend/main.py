import os
import joblib
import time
import logging
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from backend.xai_service import XAIService
from backend.config import FRONTEND_URL, BASE_URL, PORT

# ── Configure Logging ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spam_detection_logger")

# ── Resolve model paths relative to this file ────────────────────────────────
# FIX: Use pathlib.Path so the app works regardless of the working directory.
# Previously, hardcoded relative strings like "linear_svm_model.pkl" would
# break whenever the process was not launched from the repo root.
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Load ML models ────────────────────────────────────────────────────────────
# FIX: label_encoder.pkl was never loaded here, causing /predict to return
# a raw integer (0, 1, 2) instead of a human-readable label string like
# "ham", "spam", or "smishing". The frontend's string comparisons
# (result === "ham") would always evaluate to false with the old code.
model         = joblib.load(BASE_DIR / "linear_svm_model.pkl")
vectorizer    = joblib.load(BASE_DIR / "backend" / "tfidf_vectorizer.pkl")
label_encoder = joblib.load(BASE_DIR / "label_encoder.pkl")

xai_service = XAIService(model=model, vectorizer=vectorizer, label_encoder=label_encoder)

app = FastAPI(title="Spam Detection System")

# ── CORS setup ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        os.getenv("FRONTEND_DEV_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Logging Middleware ────────────────────────────────────────────────────────
import os
import logging
from fastapi.responses import JSONResponse

# ── Internal secret gate ──────────────────────────────────────────────────────
INTERNAL_SECRET_MIN_LENGTH = 32

def _load_internal_secret() -> str:
    secret = os.getenv("INTERNAL_SECRET")
    if not secret:
        raise RuntimeError(
            "INTERNAL_SECRET is not set. This shared secret authenticates "
            "requests from the trusted backend and is mandatory. Generate "
            "one with `python -c \"import secrets; print(secrets.token_urlsafe(32))\"` "
            "and set it (identically) for both the Node and FastAPI services."
        )
    if len(secret) < INTERNAL_SECRET_MIN_LENGTH:
        raise RuntimeError(
            f"INTERNAL_SECRET is too short ({len(secret)} characters); it must be at least {INTERNAL_SECRET_MIN_LENGTH} characters."
        )
    return secret

INTERNAL_SECRET = _load_internal_secret()
PUBLIC_PATHS = {"/", "/health"}

import secrets

@app.middleware("http")
async def enforce_internal_secret(request: Request, call_next):
    # Allow CORS preflight and public health checks
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    provided = request.headers.get("X-Internal-Secret")
    if not provided or not secrets.compare_digest(provided, INTERNAL_SECRET):
        return JSONResponse(status_code=403, content={"error": "Forbidden: requests must originate from the trusted backend"})
    return await call_next(request)

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = request.url.path
    client_host = request.client.host if request.client else "unknown"
    
    logger.info(f"Incoming request: {method} {path} from {client_host}")

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000  # Duration in milliseconds
    status_code = response.status_code
    
    logger.info(f"Completed request: {method} {path} | Status: {status_code} | Duration: {process_time:.2f}ms")
    
    # Inject processing metrics into response headers for visibility
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response

# ── Request schema ────────────────────────────────────────────────────────────
class PredictIn(BaseModel):
    text: str
    type: str

# ── Prediction route ──────────────────────────────────────────────────────────
@app.post("/predict")
def predict(body: PredictIn):
    """
    Classify a message as ham, spam, or smishing.

    Returns:
        prediction (str): Human-readable label — "ham", "spam", or "smishing".
        confidence (float): SVM decision-function score for the winning class.
                            Higher absolute value = more confident prediction.
    """
    try:
        vectorized_text = vectorizer.transform([body.text])

        # Get the raw predicted class index (0, 1, or 2)
        raw_prediction = model.predict(vectorized_text)[0]

        # FIX: Convert class index → string label using the label encoder
        label = label_encoder.inverse_transform([raw_prediction])[0]

        # Compute decision scores and confidence
        decision_scores = model.decision_function(vectorized_text)[0]
        # Decision score is the raw distance for the winning class
        decision_score = float(np.max(np.abs(decision_scores)))
        # Convert to pseudo‑probability (same approach as Flask)
        prob = 1.0 / (1.0 + np.exp(-decision_score))
        confidence_score = round(prob * 100, 2)
        # Determine confidence level
        if confidence_score >= 80:
            confidence_level = "high"
        elif confidence_score >= 60:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        # Return response with standardized fields
        return {
            "result": label,            # e.g. "ham", "spam", "smishing"
            "prediction": label,       # legacy key
            "confidence_score": confidence_score,
            "decision_score": decision_score,
            "confidence_level": confidence_level,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Health / root ─────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status":   "ok",
        "message":  "Spam Detection API is running",
        "base_url": BASE_URL,
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# ── Routers ───────────────────────────────────────────────────────────────────
# EMAIL DATABASE ROUTES (Issue #13)
from fastapi_backend.emails import router as emails_router
# from fastapi_backend.database import init_db  # Uncomment once DB is configured
# init_db()
app.include_router(emails_router)

# EXPORT ROUTES (Issue #23)
from fastapi_backend.export import router as export_router
app.include_router(export_router)

# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_backend.main:app", host="0.0.0.0", port=PORT, reload=True)
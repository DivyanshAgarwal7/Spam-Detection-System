import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

os.environ.setdefault("MODEL_PATH", str(BASE_DIR / "linear_svm_model.pkl"))
os.environ.setdefault("VECTORIZER_PATH", str(BACKEND_DIR / "tfidf_vectorizer.pkl"))
os.environ.setdefault("LABEL_ENCODER_PATH", str(BASE_DIR / "label_encoder.pkl"))
os.environ.setdefault("URL_MODEL_PATH", str(BACKEND_DIR / "url_detector.pkl"))
os.environ.setdefault("URL_VECTORIZER_PATH", str(BACKEND_DIR / "url_vectorizer.pkl"))

sys.path.insert(0, str(BACKEND_DIR))

import api as api_module  # noqa: E402
from utils.spamSeverity import calculate_spam_severity


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c


def test_spam_severity_engine_detects_high_risk_message():
    severity = calculate_spam_severity(
        "Urgent! Verify your password now and enter the OTP at http://bit.ly/abc123"
    )

    assert 0 <= severity["score"] <= 10
    assert severity["level"] in {"Low", "Moderate", "High", "Critical"}
    assert isinstance(severity["indicators"], list)
    assert severity["breakdown"]["total_score"] == severity["score"]
    assert any(indicator in severity["indicators"] for indicator in ["Password Request", "Urgent Language", "Suspicious URL"])


def test_spam_severity_engine_returns_low_score_for_safe_message():
    severity = calculate_spam_severity("Hello, I will meet you for lunch tomorrow afternoon.")

    assert severity["score"] <= 2
    assert severity["level"] == "Low"
    assert severity["indicators"] == []


def test_spam_severity_engine_handles_empty_and_whitespace_input():
    assert calculate_spam_severity("") == {
        "score": 0.0,
        "level": "Low",
        "indicators": [],
        "breakdown": {
            "url_risk": 0.0,
            "keyword_risk": 0.0,
            "formatting_risk": 0.0,
            "urgency_risk": 0.0,
            "social_engineering_risk": 0.0,
            "total_score": 0.0,
        },
    }
    assert calculate_spam_severity("   \n\t  ")["score"] == 0.0


def test_spam_severity_engine_marks_moderate_score_for_multiple_signals():
    severity = calculate_spam_severity("Please verify your account immediately and click here.")

    assert severity["score"] >= 3.0
    assert severity["level"] == "Moderate"


def test_predict_endpoint_includes_severity_payload(client):
    response = client.post("/predict", json={"text": "Verify your password now!", "type": "message"})

    assert response.status_code == 200
    data = response.get_json()
    assert "severity" in data
    severity = data["severity"]
    assert isinstance(severity, dict)
    assert 0 <= severity["score"] <= 10
    assert severity["level"] in {"Low", "Moderate", "High", "Critical"}
    assert "indicators" in severity
    assert "breakdown" in severity

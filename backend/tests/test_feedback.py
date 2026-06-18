import csv
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


@pytest.fixture
def client(tmp_path, monkeypatch):
    feedback_file = tmp_path / "feedback_store.csv"
    monkeypatch.setattr(api_module, "FEEDBACK_FILE", str(feedback_file))
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c, feedback_file


class TestFeedback:
    """Covers the /feedback endpoint added for #58."""

    def test_valid_correction_creates_csv_with_header(self, client):
        c, feedback_file = client
        res = c.post("/feedback", json={
            "text": "Win a free prize now!",
            "predicted_label": "ham",
            "correct_label": "spam",
        })
        assert res.status_code == 201
        assert res.get_json() == {"message": "Feedback recorded. Thank you!"}

        with open(feedback_file, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        assert rows[0] == ["text", "predicted_label", "correct_label", "submitted_at"]
        assert rows[1][:3] == ["Win a free prize now!", "ham", "spam"]

    def test_confirming_correct_prediction(self, client):
        c, feedback_file = client
        res = c.post("/feedback", json={
            "text": "Let's catch up tomorrow",
            "predicted_label": "ham",
            "correct_label": "ham",
        })
        assert res.status_code == 201

        with open(feedback_file, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        assert rows[1][1] == "ham"
        assert rows[1][2] == "ham"

    def test_appends_multiple_rows_without_duplicate_headers(self, client):
        c, feedback_file = client
        for label in ("spam", "smishing", "ham"):
            res = c.post("/feedback", json={
                "text": f"sample {label}",
                "predicted_label": "ham",
                "correct_label": label,
            })
            assert res.status_code == 201

        with open(feedback_file, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        assert len(rows) == 4  # header + 3 feedback rows
        assert rows[0] == ["text", "predicted_label", "correct_label", "submitted_at"]

    def test_invalid_label_rejected(self, client):
        c, feedback_file = client
        res = c.post("/feedback", json={
            "text": "some text",
            "predicted_label": "ham",
            "correct_label": "offensive",
        })
        assert res.status_code == 400
        assert res.get_json() == {"error": "Invalid feedback data"}
        assert not feedback_file.exists()

    def test_missing_text_rejected(self, client):
        c, feedback_file = client
        res = c.post("/feedback", json={
            "predicted_label": "ham",
            "correct_label": "spam",
        })
        assert res.status_code == 400
        assert res.get_json() == {"error": "Invalid feedback data"}
        assert not feedback_file.exists()

    def test_missing_correct_label_rejected(self, client):
        c, feedback_file = client
        res = c.post("/feedback", json={
            "text": "some text",
            "predicted_label": "ham",
        })
        assert res.status_code == 400
        assert res.get_json() == {"error": "Invalid feedback data"}
        assert not feedback_file.exists()

import io
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
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c

class TestBulkPredict:
    def test_csv_upload_success_text_column(self, client):
        csv_data = "text\nCongratulations! You won a free prize\nMeeting tomorrow at 10am\nClaim your reward now\n"
        data = {
            "file": (io.BytesIO(csv_data.encode("utf-8")), "test.csv")
        }
        res = client.post("/bulk-predict", data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["total_messages"] == 3
        assert "spam_count" in json_data
        assert "non_spam_count" in json_data
        assert "spam_percentage" in json_data
        assert len(json_data["results"]) == 3
        assert json_data["results"][0]["message"] == "Congratulations! You won a free prize"
        assert "prediction" in json_data["results"][0]

    def test_csv_upload_success_message_column(self, client):
        csv_data = "message\nCongratulations! You won a free prize\nMeeting tomorrow at 10am\n"
        data = {
            "file": (io.BytesIO(csv_data.encode("utf-8")), "test.csv")
        }
        res = client.post("/bulk-predict", data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["total_messages"] == 2

    def test_txt_upload_success(self, client):
        txt_data = "Congratulations! You won a free prize\n\nMeeting tomorrow at 10am\nClaim your reward now\n"
        data = {
            "file": (io.BytesIO(txt_data.encode("utf-8")), "test.txt")
        }
        res = client.post("/bulk-predict", data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["total_messages"] == 3

    def test_invalid_file_type(self, client):
        data = {
            "file": (io.BytesIO(b"some content"), "test.pdf")
        }
        res = client.post("/bulk-predict", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        assert "Unsupported file type" in res.get_json()["error"]

    def test_missing_text_column(self, client):
        csv_data = "invalid_col\nCongratulations! You won a free prize\n"
        data = {
            "file": (io.BytesIO(csv_data.encode("utf-8")), "test.csv")
        }
        res = client.post("/bulk-predict", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        assert "must contain either a 'text' or 'message' column" in res.get_json()["error"]

    def test_empty_file(self, client):
        data = {
            "file": (io.BytesIO(b""), "test.csv")
        }
        res = client.post("/bulk-predict", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        assert "Empty file" in res.get_json()["error"]

    def test_file_too_large(self, client):
        # 2MB limit. Create string payload > 2MB.
        large_data = "text\n" + ("message\n" * 300000)
        data = {
            "file": (io.BytesIO(large_data.encode("utf-8")), "test.csv")
        }
        res = client.post("/bulk-predict", data=data, content_type="multipart/form-data")
        assert res.status_code == 413
        assert "exceeds the limit" in res.get_json()["error"]

    def test_export_success(self, client):
        csv_data = "text\nCongratulations! You won a free prize\nMeeting tomorrow at 10am\n"
        data = {
            "file": (io.BytesIO(csv_data.encode("utf-8")), "test.csv")
        }
        res = client.post("/bulk-predict/export", data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        assert res.headers["Content-Type"].startswith("text/csv")
        assert "attachment" in res.headers["Content-Disposition"]
        
        body = res.data.decode("utf-8")
        assert "message,prediction" in body
        assert "Congratulations! You won a free prize" in body

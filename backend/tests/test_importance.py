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


class TestImportance:
    """Covers the /importance endpoint."""

    def test_importance_endpoint_returns_features(self, client):
        res = client.get("/importance")
        assert res.status_code == 200
        
        data = res.get_json()
        assert "top_features" in data
        assert isinstance(data["top_features"], list)
        
        # Verify the structure of returned features
        if len(data["top_features"]) > 0:
            feature_item = data["top_features"][0]
            assert "feature" in feature_item
            assert "importance" in feature_item
            assert isinstance(feature_item["feature"], str)
            assert isinstance(feature_item["importance"], float)

import os
import sys
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

# Ensure env variables are set for testing ML modules
os.environ.setdefault("MODEL_PATH", str(BASE_DIR / "linear_svm_model.pkl"))
os.environ.setdefault("VECTORIZER_PATH", str(BACKEND_DIR / "tfidf_vectorizer.pkl"))
os.environ.setdefault("LABEL_ENCODER_PATH", str(BASE_DIR / "label_encoder.pkl"))
os.environ.setdefault("URL_MODEL_PATH", str(BACKEND_DIR / "url_detector.pkl"))
os.environ.setdefault("URL_VECTORIZER_PATH", str(BACKEND_DIR / "url_vectorizer.pkl"))

sys.path.insert(0, str(BACKEND_DIR))

import api as api_module
import spam_insights

@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c

class TestSpamInsights:
    def test_tokenize(self):
        text = "Hello world! This is a test message. Claim free prize."
        tokens = spam_insights.tokenize(text)
        assert "hello" in tokens
        assert "world" in tokens
        assert "claim" in tokens
        assert "free" in tokens
        # Punctuation should be stripped
        assert "world!" not in tokens

    def test_fallback_analytics_structure(self):
        # When dataset is empty/less than 5, get_spam_insights should return fallbacks
        res = spam_insights.get_spam_insights(limit=5)
        assert "top_keywords" in res
        assert "trending_phrases" in res
        assert "recent_suspicious_terms" in res
        assert "category_indicators" in res
        
        assert len(res["top_keywords"]) <= 5
        assert len(res["trending_phrases"]) <= 5
        assert len(res["recent_suspicious_terms"]) <= 5

    def test_get_spam_insights_with_category_filter(self):
        res = spam_insights.get_spam_insights(limit=5, category="spam")
        assert len(res["top_keywords"]) <= 5
        
    def test_api_endpoint_insights_success(self, client):
        response = client.get("/spam-insights")
        assert response.status_code == 200
        data = response.get_json()
        assert "top_keywords" in data
        assert "trending_phrases" in data
        assert "recent_suspicious_terms" in data
        assert "category_indicators" in data

    def test_api_endpoint_insights_limit_param(self, client):
        response = client.get("/spam-insights?limit=3")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["top_keywords"]) <= 3

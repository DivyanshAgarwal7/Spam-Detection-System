"""Structured JSON logging + redaction contract for the ML API (issue #1006).

Part 1 guarantees every emitted line is a JSON object carrying a ``request_id``
that propagates from the ``X-Request-ID`` header. Part 2 guarantees secrets and
personal data (internal secret, OAuth tokens, API keys, emails / message
bodies) never reach the sink in the clear.

The module-level unit tests exercise ``logging_config`` directly and do not
import the Flask app, so they run even where an optional app dependency is
missing. The propagation test drives the app's access log through a real
request.
"""

import io
import json
import logging
import os
from   pathlib                  import Path
import sys

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))

from   logging_config           import (JsonLogFormatter, REDACTED,
                                        RedactionFilter, RequestIdFilter)

KNOWN_SECRET = "super-secret-internal-value-do-not-log-1234567890"
KNOWN_TOKEN = "ya29.a0AfB_byC_fake_oauth_access_token_value"
KNOWN_EMAIL = "victim.user@example.com"


def _emit(record, *, redact_secrets=None):
    """Run a record through the production filters + formatter, return JSON."""
    RequestIdFilter().filter(record)
    if redact_secrets is not None:
        RedactionFilter(extra_secrets=redact_secrets).filter(record)
    return json.loads(JsonLogFormatter().format(record))


def _record(msg, **extra):
    record = logging.LogRecord("ml_api", logging.INFO, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formatter_emits_valid_json_with_core_fields():
    data = _emit(_record("hello"))
    assert data["msg"] == "hello"
    assert data["level"] == "INFO"
    assert data["logger"] == "ml_api"
    # Outside a request context the id falls back to a stable placeholder.
    assert data["request_id"] == "-"


def test_structured_extras_are_top_level_fields():
    data = _emit(_record("request", method="GET", path="/health", status=200))
    assert data["method"] == "GET"
    assert data["path"] == "/health"
    assert data["status"] == 200


def test_redaction_scrubs_secret_token_and_email():
    msg = (
        f"connect user={KNOWN_EMAIL} "
        f"access_token={KNOWN_TOKEN} "
        f"X-Internal-Secret: {KNOWN_SECRET}"
    )
    raw = json.dumps(_emit(_record(msg), redact_secrets=[KNOWN_SECRET]))
    assert KNOWN_SECRET not in raw
    assert KNOWN_TOKEN not in raw
    assert KNOWN_EMAIL not in raw
    assert REDACTED in raw


def test_redaction_scrubs_string_extras():
    data = _emit(
        _record("oauth", email=KNOWN_EMAIL, refresh_token=KNOWN_TOKEN),
        redact_secrets=[],
    )
    assert data["email"] == REDACTED
    assert KNOWN_TOKEN not in json.dumps(data)


def test_redaction_scrubs_bare_literal_secret_without_a_key():
    # A secret logged with no recognisable key still goes via the literal list.
    data = _emit(_record(f"boot with {KNOWN_SECRET}"), redact_secrets=[KNOWN_SECRET])
    assert KNOWN_SECRET not in json.dumps(data)


class TestAccessLogPropagation:
    """Drive the app so the access log stamps the header-supplied request id."""

    @pytest.fixture(scope="class")
    def api_module(self):
        os.environ.setdefault("MODEL_PATH", str(BASE_DIR / "linear_svm_model.pkl"))
        os.environ.setdefault(
            "VECTORIZER_PATH", str(BACKEND_DIR / "tfidf_vectorizer.pkl")
        )
        os.environ.setdefault("LABEL_ENCODER_PATH", str(BASE_DIR / "label_encoder.pkl"))
        os.environ.setdefault("URL_MODEL_PATH", str(BACKEND_DIR / "url_detector.pkl"))
        os.environ.setdefault(
            "URL_VECTORIZER_PATH", str(BACKEND_DIR / "url_vectorizer.pkl")
        )
        import api as api_module

        return api_module

    @pytest.fixture
    def client(self, api_module):
        api_module.app.config["TESTING"] = True
        with api_module.app.test_client() as c:
            yield c

    def test_request_id_propagates_from_header(self, client):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonLogFormatter())
        handler.addFilter(RequestIdFilter())
        access_logger = logging.getLogger("ml_api.access")
        access_logger.addHandler(handler)
        try:
            client.get("/health", headers={"X-Request-ID": "known-req-42"})
        finally:
            access_logger.removeHandler(handler)

        lines = [ln for ln in stream.getvalue().splitlines() if ln.strip()]
        assert lines, "access log emitted no line"
        record = json.loads(lines[-1])
        assert record["request_id"] == "known-req-42"
        assert record["path"] == "/health"
        assert record["method"] == "GET"

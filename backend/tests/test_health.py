"""Health-probe and graceful-shutdown coverage (issue #1009).

Verifies the split liveness/readiness contract: /health/live is a pure
process-up signal that ignores dependencies, /health/ready reflects serving
state, dependency health and the drain flag, and /health stays a
backward-compatible static alias.
"""

import os
from   pathlib                  import Path
import sys

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

os.environ.setdefault("MODEL_PATH", str(BASE_DIR / "linear_svm_model.pkl"))
os.environ.setdefault("VECTORIZER_PATH", str(BACKEND_DIR / "tfidf_vectorizer.pkl"))
os.environ.setdefault("LABEL_ENCODER_PATH", str(BASE_DIR / "label_encoder.pkl"))
os.environ.setdefault("URL_MODEL_PATH", str(BASE_DIR / "url_detector.pkl"))
os.environ.setdefault("URL_VECTORIZER_PATH", str(BASE_DIR / "url_vectorizer.pkl"))

sys.path.insert(0, str(BACKEND_DIR))

try:
    import api as api_module  # noqa: E402
except Exception as exc:  # pragma: no cover - env without ML deps/models
    pytest.skip(f"api import unavailable: {exc}", allow_module_level=True)

from   errors                   import ErrorCode # noqa: E402
import serving_state # noqa: E402


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_drain():
    """Keep the module-level drain flag from leaking across tests."""
    api_module.draining = False
    yield
    api_module.draining = False


@pytest.fixture
def no_serving_state():
    original = serving_state.STATE
    serving_state.STATE = None
    yield
    serving_state.STATE = original


def test_health_live_is_200_independent_of_dependencies(client, no_serving_state):
    # Liveness must stay green even with serving state torn down: it reports
    # only that the process can answer, so an orchestrator won't restart the pod
    # for a dependency problem.
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.get_json()["status"] == "alive"


def test_health_ready_200_when_healthy(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ready"
    assert all(body["checks"].values())


def test_health_ready_503_when_serving_state_missing(client, no_serving_state):
    res = client.get("/health/ready")
    assert res.status_code == 503
    body = res.get_json()
    assert body["error_detail"]["code"] == ErrorCode.NOT_READY
    assert body["checks"]["serving_state"] is False


def test_health_ready_503_when_dependency_down(client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("spam-words DB unavailable")

    monkeypatch.setattr(api_module.imap_store, "get_db_connection", boom)
    res = client.get("/health/ready")
    assert res.status_code == 503
    body = res.get_json()
    assert body["error_detail"]["code"] == ErrorCode.NOT_READY
    assert body["checks"]["spam_words_db"] is False


def test_begin_drain_flips_ready_to_503(client):
    assert client.get("/health/ready").status_code == 200
    api_module.begin_drain()
    res = client.get("/health/ready")
    assert res.status_code == 503
    body = res.get_json()
    assert body["status"] == "draining"
    assert body["error_detail"]["code"] == ErrorCode.NOT_READY


def test_setting_draining_flag_flips_ready_to_503(client):
    # The flag is a plain module attribute so operators/tests can toggle it
    # directly, not only via begin_drain().
    api_module.draining = True
    assert client.get("/health/ready").status_code == 503


def test_health_alias_unchanged(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_inflight_counter_settles_to_zero(client):
    client.get("/health/live")
    client.get("/health/ready")
    assert api_module.inflight_requests() == 0

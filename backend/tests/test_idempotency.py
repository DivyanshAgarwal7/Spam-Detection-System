"""Tests for the idempotency-key layer added for issue #1022.

The decorator is exercised against a minimal self-contained Flask app rather
than the full ML API, so the behaviour under test (passthrough, replay, payload
conflict) is isolated from unrelated request-validation and model-loading
machinery. TTL expiry is checked directly on the store with an injected clock so
it stays deterministic and never sleeps.
"""

from   pathlib                  import Path
import sys

from   flask                    import Flask, jsonify
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import idempotency # noqa: E402
from   idempotency              import IdempotencyStore, idempotent


@pytest.fixture
def app_and_counter(monkeypatch):
    """A minimal app whose one mutating route counts how often it really runs."""
    monkeypatch.setattr(idempotency, "_STORE", IdempotencyStore(ttl_seconds=600))

    app = Flask(__name__)
    calls = {"count": 0}

    @app.route("/mutate", methods=["POST"])
    @idempotent
    def mutate():
        calls["count"] += 1
        return jsonify({"run": calls["count"]}), 201

    return app, calls


def test_passthrough_without_key_runs_every_time(app_and_counter):
    app, calls = app_and_counter
    client = app.test_client()

    first = client.post("/mutate", json={"a": 1})
    second = client.post("/mutate", json={"a": 1})

    assert first.status_code == 201
    assert second.status_code == 201
    # No key means no dedupe: the handler runs on every call.
    assert calls["count"] == 2
    assert idempotency.IDEMPOTENT_REPLAY_HEADER not in second.headers


def test_first_call_with_key_runs_and_caches(app_and_counter):
    app, calls = app_and_counter
    client = app.test_client()

    res = client.post("/mutate", json={"a": 1}, headers={"Idempotency-Key": "k1"})

    assert res.status_code == 201
    assert res.get_json() == {"run": 1}
    assert calls["count"] == 1
    assert idempotency.IDEMPOTENT_REPLAY_HEADER not in res.headers


def test_replay_returns_cached_response_without_rerunning(app_and_counter):
    app, calls = app_and_counter
    client = app.test_client()

    first = client.post("/mutate", json={"a": 1}, headers={"Idempotency-Key": "k1"})
    second = client.post("/mutate", json={"a": 1}, headers={"Idempotency-Key": "k1"})

    assert calls["count"] == 1  # side effect happened exactly once
    assert first.get_json() == second.get_json() == {"run": 1}
    assert second.status_code == 201
    assert second.headers[idempotency.IDEMPOTENT_REPLAY_HEADER] == "true"


def test_same_key_different_payload_conflicts(app_and_counter):
    app, calls = app_and_counter
    client = app.test_client()

    client.post("/mutate", json={"a": 1}, headers={"Idempotency-Key": "k1"})
    conflict = client.post("/mutate", json={"a": 2}, headers={"Idempotency-Key": "k1"})

    assert conflict.status_code == 409
    assert conflict.get_json()["error_detail"]["code"] == "IDEMPOTENCY_CONFLICT"
    # The conflicting request must not have run the handler.
    assert calls["count"] == 1


def test_store_entry_expires_after_ttl():
    # Injected clock ticks: record() at t=0 (expires_at=100), get() before the
    # TTL at t=50, get() after it at t=200.
    clock = iter([0, 50, 200]).__next__
    store = IdempotencyStore(ttl_seconds=100, clock=clock)

    store.record("k", "fp", 201, b"{}", "application/json")

    live = store.get("k")
    assert live is not None and live.status_code == 201

    # A later read past expires_at (0 + 100) evicts the entry.
    assert store.get("k") is None


def test_store_reads_ttl_from_env(monkeypatch):
    monkeypatch.setattr(idempotency, "_STORE", None)
    monkeypatch.setenv(idempotency.IDEMPOTENCY_TTL_ENV_VAR, "42")

    store = idempotency._get_store()
    assert store._ttl_seconds == 42


def test_store_env_falls_back_on_garbage(monkeypatch):
    monkeypatch.setattr(idempotency, "_STORE", None)
    monkeypatch.setenv(idempotency.IDEMPOTENCY_TTL_ENV_VAR, "not-a-number")

    store = idempotency._get_store()
    assert store._ttl_seconds == idempotency._DEFAULT_TTL_SECONDS

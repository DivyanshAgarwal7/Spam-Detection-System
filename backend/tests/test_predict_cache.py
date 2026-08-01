"""Tests for the content-addressed /predict response cache (issue #1008).

Two layers of coverage:

* Unit tests drive :class:`predict_cache.PredictCache` and
  :func:`predict_cache.make_cache_key` directly (no Flask app, no ML deps), with
  an injected clock. They pin hit/miss accounting, TTL expiry, LRU eviction,
  version-namespaced invalidation and deep-copy isolation.
* Endpoint tests exercise the wiring in ``/predict`` -- the ``X-Cache`` header,
  the ``Cache-Control``/``?fresh=1`` bypass, and cache invalidation when a model
  hot-swap bumps the serving version. They skip cleanly if ``api`` can't be
  imported in this environment (e.g. optional ML dependencies missing).
"""

from   itertools                import count
import os
from   pathlib                  import Path
import sys

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

os.environ.setdefault("MODEL_PATH", str(BASE_DIR / "linear_svm_model.pkl"))
os.environ.setdefault("VECTORIZER_PATH", str(BACKEND_DIR / "tfidf_vectorizer.pkl"))
os.environ.setdefault("LABEL_ENCODER_PATH", str(BASE_DIR / "label_encoder.pkl"))
os.environ.setdefault("URL_MODEL_PATH", str(BACKEND_DIR / "url_detector.pkl"))
os.environ.setdefault("URL_VECTORIZER_PATH", str(BACKEND_DIR / "url_vectorizer.pkl"))

sys.path.insert(0, str(BACKEND_DIR))

from   conftest                 import TEST_INTERNAL_SECRET # noqa: E402
import predict_cache # noqa: E402

VALID_SECRET = {"X-Internal-Secret": TEST_INTERNAL_SECRET}


# ---------------------------------------------------------------------------
# Unit tests: PredictCache + make_cache_key (no app import required)
# ---------------------------------------------------------------------------


@pytest.fixture
def clock(monkeypatch):
    """A controllable stand-in for predict_cache._now, starting at t=1000."""
    state = {"t": 1000.0}
    monkeypatch.setattr(predict_cache, "_now", lambda: state["t"])
    return state


def test_miss_then_hit_counts_and_returns_value():
    cache = predict_cache.PredictCache(max_size=8, ttl_seconds=100.0)
    key = predict_cache.make_cache_key("free money", 1, {"type": "message"})

    assert cache.get(key) is None  # miss
    cache.set(key, {"result": "spam"})
    assert cache.get(key) == {"result": "spam"}  # hit

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1
    assert stats["hit_rate"] == 0.5


def test_entry_expires_after_ttl(clock):
    cache = predict_cache.PredictCache(max_size=8, ttl_seconds=100.0)
    key = predict_cache.make_cache_key("hello", 1, {"type": "message"})

    cache.set(key, {"result": "ham"})  # stored at t=1000, expires at 1100
    clock["t"] = 1050.0
    assert cache.get(key) == {"result": "ham"}  # still fresh
    clock["t"] = 1101.0
    assert cache.get(key) is None  # expired -> miss and evicted

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 0


def test_version_bump_invalidates_prior_entry():
    cache = predict_cache.PredictCache(max_size=8, ttl_seconds=100.0)
    options = {"type": "message"}
    key_v1 = predict_cache.make_cache_key("win a prize", 1, options)
    key_v2 = predict_cache.make_cache_key("win a prize", 2, options)

    cache.set(key_v1, {"result": "spam", "version": 1})

    # A hot-swap bumps serving_state.version; the new-version key must miss so a
    # stale model can never serve a cached answer -- but the old entry is still
    # addressable under its own version until it ages out.
    assert key_v1 != key_v2
    assert cache.get(key_v2) is None
    assert cache.get(key_v1) == {"result": "spam", "version": 1}


def test_options_change_produces_distinct_key():
    as_message = predict_cache.make_cache_key("bit.ly/x", 1, {"type": "message"})
    as_url = predict_cache.make_cache_key("bit.ly/x", 1, {"type": "url"})
    assert as_message != as_url


def test_lru_eviction_respects_max_size():
    cache = predict_cache.PredictCache(max_size=2, ttl_seconds=100.0)
    keys = {
        name: predict_cache.make_cache_key(name, 1, {"type": "message"})
        for name in ("a", "b", "c")
    }

    cache.set(keys["a"], {"v": "a"})
    cache.set(keys["b"], {"v": "b"})
    cache.get(keys["a"])  # touch a -> b becomes the LRU victim
    cache.set(keys["c"], {"v": "c"})  # inserts c, evicts b

    stats = cache.stats()
    assert stats["size"] == 2
    assert stats["evictions"] == 1
    assert cache.get(keys["b"]) is None  # b was evicted
    assert cache.get(keys["a"]) == {"v": "a"}


def test_values_are_deep_copied_on_set_and_get():
    cache = predict_cache.PredictCache(max_size=8, ttl_seconds=100.0)
    key = predict_cache.make_cache_key("mutate me", 1, {"type": "message"})

    payload = {"nested": {"score": 10}}
    cache.set(key, payload)
    payload["nested"]["score"] = 999  # mutating the source must not leak in

    fetched = cache.get(key)
    assert fetched["nested"]["score"] == 10
    fetched["nested"]["score"] = -1  # mutating the copy must not poison the cache
    assert cache.get(key)["nested"]["score"] == 10


def test_disabled_cache_is_a_noop():
    cache = predict_cache.PredictCache(max_size=8, ttl_seconds=100.0, enabled=False)
    key = predict_cache.make_cache_key("anything", 1, {"type": "message"})

    cache.set(key, {"result": "spam"})
    assert cache.get(key) is None

    stats = cache.stats()
    assert stats["enabled"] is False
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["size"] == 0


def test_clear_resets_entries_and_counters():
    cache = predict_cache.PredictCache(max_size=8, ttl_seconds=100.0)
    key = predict_cache.make_cache_key("x", 1, {"type": "message"})
    cache.set(key, {"v": 1})
    cache.get(key)

    cache.clear()

    stats = cache.stats()
    assert stats == {
        "enabled": True,
        "hits": 0,
        "misses": 0,
        "size": 0,
        "max_size": 8,
        "ttl_seconds": 100.0,
        "evictions": 0,
        "hit_rate": 0.0,
    }


# ---------------------------------------------------------------------------
# Endpoint tests: /predict wiring (skipped if `api` cannot be imported)
# ---------------------------------------------------------------------------


class _FakeVectorizer:
    def transform(self, texts):
        return list(texts)


class _FakeModel:
    """Returns a version-tagged label so a hot-swap yields a distinct body."""

    def __init__(self, token):
        self.token = token

    def predict(self, _vectorized):
        return [f"spam-{self.token}"]


class _FakeLabelEncoder:
    def inverse_transform(self, prediction):
        return list(prediction)


class _FakeXAI:
    def analyze(self, *_args, **_kwargs):
        return {"reasons": []}

    def get_global_importance(self):
        return []


def _family(token):
    return {
        "model": _FakeModel(token),
        "vectorizer": _FakeVectorizer(),
        "label_encoder": _FakeLabelEncoder(),
        "xai_service": _FakeXAI(),
    }


def _make_loader():
    tokens = count(2)  # initial install is token 1; first reload -> token 2

    def loader():
        return _family(next(tokens))

    return loader


@pytest.fixture
def api_module():
    try:
        import api as _api  # noqa: E402
    except Exception as exc:  # pragma: no cover - env without ML deps/models
        pytest.skip(f"api import unavailable: {exc}")
    return _api


@pytest.fixture
def client(api_module):
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as c:
        yield c


@pytest.fixture
def fake_state(api_module):
    """Point the process-wide serving state at fakes and start with a clean cache."""
    import serving_state

    original = serving_state.STATE
    serving_state.init_state(loader=_make_loader(), **_family(1))
    predict_cache.CACHE.clear()
    yield serving_state.STATE
    serving_state.STATE = original
    predict_cache.CACHE.clear()


def _predict(client, text, **kwargs):
    headers = dict(VALID_SECRET)
    headers.update(kwargs.pop("headers", {}))
    return client.post("/predict", json={"text": text}, headers=headers, **kwargs)


def test_first_call_misses_then_repeat_hits(client, fake_state):
    first = _predict(client, "buy cheap pills now")
    assert first.status_code == 200
    assert first.headers.get("X-Cache") == "MISS"

    second = _predict(client, "buy cheap pills now")
    assert second.status_code == 200
    assert second.headers.get("X-Cache") == "HIT"
    # A hit must serve the identical body the miss computed.
    assert second.get_json() == first.get_json()


def test_no_cache_header_bypasses_lookup(client, fake_state):
    _predict(client, "limited offer")  # populate
    bypass = _predict(client, "limited offer", headers={"Cache-Control": "no-cache"})
    assert bypass.status_code == 200
    assert bypass.headers.get("X-Cache") == "MISS"


def test_fresh_query_param_bypasses_lookup(client, fake_state):
    _predict(client, "limited offer")  # populate
    bypass = client.post(
        "/predict?fresh=1", json={"text": "limited offer"}, headers=VALID_SECRET
    )
    assert bypass.status_code == 200
    assert bypass.headers.get("X-Cache") == "MISS"


def test_version_bump_invalidates_and_recomputes(client, fake_state):
    before = _predict(client, "identical text")
    assert before.headers.get("X-Cache") == "MISS"
    assert before.get_json()["prediction"] == "spam-1"
    assert _predict(client, "identical text").headers.get("X-Cache") == "HIT"

    # Hot-swap the model; the version bump must invalidate the cached answer.
    fake_state.reload()

    after = _predict(client, "identical text")
    assert after.headers.get("X-Cache") == "MISS"
    assert after.get_json()["prediction"] == "spam-2"


def test_cache_stats_endpoint_is_public_and_reports_counters(client, fake_state):
    _predict(client, "count me")
    _predict(client, "count me")  # one miss, one hit

    res = client.get("/cache-stats")  # no internal secret -> public
    assert res.status_code == 200
    body = res.get_json()
    assert body["hits"] >= 1
    assert body["misses"] >= 1
    assert "hit_rate" in body

"""Content-addressed response cache for the /predict hot path (issue #1008).

Repeated /predict calls with the same input re-run the full pipeline (language
detection, optional translation, domain analysis, vectorisation, inference and
explainability) even when the answer is byte-for-byte identical. This module
memoises the prediction payload keyed by the *content* of the request rather
than by any client-supplied identifier.

Two properties make the cache safe to sit in front of a live model:

* **Version namespacing.** The key folds in ``serving_state``'s monotonically
  increasing ``version`` (see :mod:`serving_state`). A ``POST /reload-model``
  hot-swap bumps that version, so every prior entry becomes unreachable and the
  first post-swap request is a miss -- a stale model can never serve a cached
  answer. Old entries age out naturally via TTL/LRU; no explicit purge needed.
* **Content addressing.** The key is ``sha256`` of the *normalised* input text
  (via ``utils.text_normalizer``) combined with the prediction options, so
  homoglyph/whitespace-obfuscated variants that normalise to the same text
  share a cache slot and an attacker cannot trivially blow the cache with
  cosmetic variations.

The cache combines TTL expiry (entries older than ``ttl_seconds`` are treated
as absent) with LRU eviction (the least-recently-used entry is dropped once the
cache is full). It is safe for concurrent use from Flask's threaded server: all
state transitions happen under a single lock, and values are deep-copied on both
``set`` and ``get`` so a caller mutating a returned payload can never poison a
cached entry.

>>> cache = PredictCache(max_size=8, ttl_seconds=100.0)
>>> key = make_cache_key("free money now", version=1, options={"type": "message"})
>>> cache.get(key) is None
True
>>> cache.set(key, {"result": "spam"})
>>> cache.get(key)
{'result': 'spam'}
>>> cache.stats()["hits"], cache.stats()["misses"]
(1, 2)
"""

from __future__ import annotations

from   collections              import OrderedDict
import copy
from   dataclasses              import dataclass
import hashlib
import json
import os
import threading
import time
from   typing                   import Any

__all__ = [
    "PredictCache",
    "CACHE",
    "make_cache_key",
    "get",
    "set",
    "stats",
    "clear",
]

# Sane defaults for a single ML API process. 512 distinct recent inputs at a
# few KB each is a small, bounded footprint; a 5-minute TTL keeps entries fresh
# enough that model/data drift between reloads is not a concern in practice.
DEFAULT_MAX_SIZE = 512
DEFAULT_TTL_SECONDS = 300.0


def _now() -> float:
    """Monotonic clock used for TTL accounting (patched in tests)."""
    return time.monotonic()


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float


class PredictCache:
    """Thread-safe bounded cache combining TTL expiry with LRU eviction.

    ``max_size`` caps the number of live entries; inserting into a full cache
    evicts the least-recently-used one. ``ttl_seconds`` bounds an entry's age --
    a read past the TTL is a miss and drops the entry. ``enabled=False`` turns
    the cache into a transparent no-op (every ``get`` misses, every ``set`` is
    dropped, and no hit/miss is counted) so it can be switched off by config
    without touching call sites.
    """

    def __init__(
        self,
        *,
        max_size: int = DEFAULT_MAX_SIZE,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        enabled: bool = True,
    ) -> None:
        self._max_size = max(0, int(max_size))
        self._ttl_seconds = float(ttl_seconds)
        self._enabled = bool(enabled)
        self._lock = threading.Lock()
        self._entries: "OrderedDict[str, _Entry]" = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        """Return a deep copy of the cached payload, or ``None`` on miss.

        A present-but-expired entry is treated as a miss and evicted so the TTL
        is enforced lazily on read without a background sweeper.
        """
        if not self._enabled:
            return None
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at <= _now():
                del self._entries[key]
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return copy.deepcopy(entry.value)

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` with a fresh TTL, evicting LRU as needed."""
        if not self._enabled or self._max_size == 0:
            return
        with self._lock:
            self._entries[key] = _Entry(
                value=copy.deepcopy(value), expires_at=_now() + self._ttl_seconds
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)
                self._evictions += 1

    def stats(self) -> dict[str, Any]:
        """Snapshot of counters: hits, misses, size, evictions and hit_rate."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "enabled": self._enabled,
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._entries),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl_seconds,
                "evictions": self._evictions,
                "hit_rate": round(self._hits / total, 4) if total else 0.0,
            }

    def clear(self) -> None:
        """Drop all entries and reset the hit/miss/eviction counters."""
        with self._lock:
            self._entries.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0


def make_cache_key(
    normalized_text: str, version: int, options: dict[str, Any] | None = None
) -> str:
    """Build a stable cache key from normalised text, model version and options.

    The text is hashed (``sha256``) rather than embedded so the key length is
    bounded and message content never lives in the key. ``version`` namespaces
    the key by the live serving state, so a model hot-swap transparently
    invalidates every prior entry. ``options`` (e.g. the ``type`` selector that
    routes to the URL vs text classifier) are serialised deterministically so
    two calls differing only in options don't collide.
    """
    text_hash = hashlib.sha256((normalized_text or "").encode("utf-8")).hexdigest()
    options_repr = json.dumps(
        options or {}, sort_keys=True, separators=(",", ":"), default=str
    )
    return f"v{version}:{text_hash}:{options_repr}"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _build_cache_from_env() -> PredictCache:
    return PredictCache(
        max_size=_env_int("PREDICT_CACHE_MAX_SIZE", DEFAULT_MAX_SIZE),
        ttl_seconds=_env_float("PREDICT_CACHE_TTL_SECONDS", DEFAULT_TTL_SECONDS),
        enabled=_env_flag("PREDICT_CACHE_ENABLED", True),
    )


# Process-wide cache the /predict handler reads through. Built once from the
# environment at import; tests construct their own PredictCache instances.
CACHE = _build_cache_from_env()


def get(key: str) -> Any | None:
    return CACHE.get(key)


def set(key: str, value: Any) -> None:  # noqa: A001 - mirrors the cache method name
    CACHE.set(key, value)


def stats() -> dict[str, Any]:
    return CACHE.stats()


def clear() -> None:
    CACHE.clear()

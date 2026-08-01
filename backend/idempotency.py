"""In-process idempotency keys for mutating ML-API endpoints (issue #1022).

Several mutating endpoints are unsafe to retry blindly: ``/feedback`` appends a
row to a CSV on every call, ``/scan-emails`` re-runs an upstream fetch plus a
model scan, and ``/reload-model`` hot-swaps the serving model set. When a client
resends the *same* request -- because the socket dropped before the response
arrived, or a proxy retried on its behalf -- the side effect happens twice. This
module lets a caller tag a mutating request with an ``Idempotency-Key`` header
so a replayed request returns the original response instead of re-executing.

The store is intentionally in-process (a dict guarded by locks): the ML API runs
as a single process per worker and keys only need to outlive a client-side
retry, so a few-minute TTL is enough. A shared backing store (Redis, ...) would
add operational surface out of proportion to the problem.

Semantics for a request that carries an ``Idempotency-Key``:

* first time the key is seen -- run the handler, cache ``(fingerprint, status,
  body)``, return the response.
* same key + same fingerprint -- replay the cached response, skipping the
  handler and all of its side effects.
* same key + different fingerprint -- the caller reused a key for a different
  payload, which is a client bug; return a typed ``IDEMPOTENCY_CONFLICT`` (409).

Requests without the header keep today's behaviour: :func:`idempotent` becomes a
pass-through, so callers that don't opt in are unaffected.

>>> store = IdempotencyStore(ttl_seconds=100, clock=iter([0, 0, 200]).__next__)
>>> store.record("k", "fp", 201, b"{}", "application/json")
>>> store.get("k").status_code            # not yet expired (clock -> 0)
201
>>> store.get("k") is None                # clock -> 200, past the TTL
True
"""

from   dataclasses              import dataclass
from   functools                import wraps
import hashlib
import os
import threading
import time

from   flask                    import Response, g, make_response, request

from   errors                   import ErrorCode, error_response

__all__ = [
    "IDEMPOTENCY_KEY_HEADER",
    "IDEMPOTENCY_TTL_ENV_VAR",
    "IdempotencyStore",
    "idempotent",
]

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
IDEMPOTENCY_TTL_ENV_VAR = "IDEMPOTENCY_TTL_SECONDS"

# Marks replayed responses so callers (and tests) can tell a cache hit from a
# freshly computed response without inspecting the body.
IDEMPOTENT_REPLAY_HEADER = "Idempotent-Replay"

_DEFAULT_TTL_SECONDS = 600


@dataclass(slots=True)
class _Entry:
    """One cached response, tied to the fingerprint that produced it."""

    fingerprint: str
    status_code: int
    body: bytes
    content_type: str
    expires_at: float


class IdempotencyStore:
    """TTL-backed cache of responses keyed by ``Idempotency-Key``.

    ``clock`` is injectable so expiry can be tested deterministically without
    sleeping; it defaults to :func:`time.monotonic` because only elapsed time
    matters and a monotonic source is immune to wall-clock adjustments.

    The per-key lock exposed by :meth:`lock_for` is what makes two simultaneous
    retries safe: the first request through runs the handler while the second
    blocks, then finds the cached entry and replays it.
    """

    def __init__(self, ttl_seconds=_DEFAULT_TTL_SECONDS, *, clock=time.monotonic):
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, _Entry] = {}
        self._key_locks: dict[str, threading.Lock] = {}
        # Guards both dicts; held only for O(1) bookkeeping, never across the
        # wrapped handler, so it does not serialise unrelated keys.
        self._registry_lock = threading.Lock()

    def lock_for(self, key):
        """Return the process-wide lock dedicated to ``key`` (created on demand)."""
        with self._registry_lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
            return lock

    def get(self, key):
        """Return the live entry for ``key``, or ``None`` if absent or expired."""
        with self._registry_lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                del self._entries[key]
                return None
            return entry

    def record(self, key, fingerprint, status_code, body, content_type):
        """Cache a response under ``key`` with a fresh TTL window."""
        entry = _Entry(
            fingerprint=fingerprint,
            status_code=status_code,
            body=body,
            content_type=content_type,
            expires_at=self._clock() + self._ttl_seconds,
        )
        with self._registry_lock:
            self._entries[key] = entry


# Module-level singleton so a key persists across requests within a worker. It
# is created lazily (rather than at import) so IDEMPOTENCY_TTL_SECONDS can be
# set by process configuration before the first request, and so tests can swap
# in a store with an injected clock.
_STORE = None


def _get_store():
    global _STORE
    if _STORE is None:
        _STORE = IdempotencyStore(ttl_seconds=_ttl_seconds_from_env())
    return _STORE


def _ttl_seconds_from_env():
    raw = os.getenv(IDEMPOTENCY_TTL_ENV_VAR)
    if raw is None:
        return _DEFAULT_TTL_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_TTL_SECONDS
    # A non-positive TTL would cache nothing (or forever); fall back to the
    # default rather than silently disabling replay.
    return value if value > 0 else _DEFAULT_TTL_SECONDS


def _fingerprint():
    """Stable hash of the request identity (method + path + body).

    The body is included so the same key against a *different* payload is
    detected as a conflict rather than served a stale, unrelated response.
    """
    digest = hashlib.sha256()
    digest.update(request.method.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(request.path.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(request.get_data(cache=True) or b"")
    return digest.hexdigest()


def _replay(entry):
    response = Response(
        entry.body,
        status=entry.status_code,
        content_type=entry.content_type,
    )
    response.headers[IDEMPOTENT_REPLAY_HEADER] = "true"
    return response


def idempotent(f):
    """Make ``f`` replay-safe when the request carries an ``Idempotency-Key``.

    Without the header this is a transparent pass-through. With it, the first
    request runs the handler and caches its response; a matching replay returns
    that cached response without re-running the handler; and a key reused for a
    different payload yields a typed 409 conflict.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
        if not key:
            return f(*args, **kwargs)

        store = _get_store()
        fingerprint = _fingerprint()

        # Serialise on the key so concurrent retries can't both execute the
        # handler; the loser blocks here, then falls through to the cache hit.
        with store.lock_for(key):
            entry = store.get(key)
            if entry is not None:
                if entry.fingerprint == fingerprint:
                    return _replay(entry)
                return error_response(
                    ErrorCode.IDEMPOTENCY_CONFLICT,
                    "Idempotency-Key was reused with a different request payload.",
                    409,
                    request_id=getattr(g, "request_id", "unknown"),
                )

            response = make_response(f(*args, **kwargs))
            store.record(
                key,
                fingerprint,
                response.status_code,
                response.get_data(),
                response.content_type,
            )
            return response

    return decorated_function

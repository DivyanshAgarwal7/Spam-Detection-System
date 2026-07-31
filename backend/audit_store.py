"""Tamper-evident, append-only audit store for the Flask ML API (issue #1023).

The ``audit_log`` decorator in ``api.py`` historically emitted only free-text
log lines, which are trivially editable after the fact and impossible to query.
This module persists each audited action as a row in a local SQLite database
and links the rows into a SHA-256 hash chain: every record commits to the hash
of its predecessor, so editing or deleting any row invalidates the hash of that
record and of every record that follows it. :func:`verify_chain` recomputes the
chain end to end and reports whether it is intact, giving operators a cheap
integrity check over the whole trail.

The store is deliberately dependency-free (stdlib ``sqlite3`` only) and is meant
to be called fail-soft: a write failure must never break the request being
audited (see ``api.audit_log``). The database location is configurable via
``AUDIT_DB_PATH`` so deployments can point it at durable storage.

>>> import os, tempfile
>>> db = os.path.join(tempfile.mkdtemp(), "audit.db")
>>> _ = append("alice", "predict", "message", "req-1", 200, db_path=db)
>>> _ = append("bob", "reload_model", "model", "req-2", 200, db_path=db)
>>> verify_chain(db_path=db)
True
"""

from   datetime                 import datetime, timezone
import hashlib
import json
import os
from   pathlib                  import Path
import sqlite3

__all__ = [
    "GENESIS_HASH",
    "DB_PATH",
    "get_db_connection",
    "init_db",
    "append",
    "verify_chain",
]

# Default location for the audit database. Overridable so deployments can point
# the store at a durable, backed-up volume rather than the app directory.
DB_PATH = os.getenv(
    "AUDIT_DB_PATH",
    str(Path(__file__).resolve().parent / "audit_log.db"),
)

# prev_hash of the first record. A fixed, all-zero digest anchors the chain so
# the genesis record is verified with the same rule as every later one.
GENESIS_HASH = "0" * 64

# Fields committed to by ``record_hash``, in a fixed order. ``id`` is excluded
# because it is assigned by SQLite on insert and is not part of the signed
# payload; ordering/deletion is instead caught by the prev_hash linkage.
_HASHED_FIELDS = ("actor", "action", "resource", "request_id", "status", "timestamp")


def get_db_connection(db_path=None):
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(db_path=None):
    """Create the audit table if it does not exist. Idempotent."""
    with get_db_connection(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                request_id TEXT NOT NULL,
                status INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL
            )
            """
        )
        conn.commit()


def append(actor, action, resource, request_id, status, timestamp=None, db_path=None):
    """Append one audited action to the chain and return the stored record.

    ``prev_hash`` is taken from the current tail of the chain (or
    :data:`GENESIS_HASH` when the store is empty) and ``record_hash`` is the
    SHA-256 of ``prev_hash`` concatenated with the canonical serialization of
    the signed fields. The returned dict includes the assigned ``id`` and both
    hashes.
    """
    init_db(db_path)
    record = {
        "actor": str(actor),
        "action": str(action),
        "resource": str(resource),
        "request_id": str(request_id),
        "status": int(status),
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }
    with get_db_connection(db_path) as conn:
        tail = conn.execute(
            "SELECT record_hash FROM audit_records ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_hash = tail["record_hash"] if tail else GENESIS_HASH
        record_hash = _compute_hash(prev_hash, record)
        cursor = conn.execute(
            """
            INSERT INTO audit_records
                (actor, action, resource, request_id, status, timestamp, prev_hash, record_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["actor"],
                record["action"],
                record["resource"],
                record["request_id"],
                record["status"],
                record["timestamp"],
                prev_hash,
                record_hash,
            ),
        )
        conn.commit()
        record["id"] = cursor.lastrowid
    record["prev_hash"] = prev_hash
    record["record_hash"] = record_hash
    return record


def verify_chain(db_path=None):
    """Recompute the hash chain and return whether it is intact.

    Walks the records in insertion order, checking that each row's stored
    ``prev_hash`` matches the running hash and that its ``record_hash`` matches
    a fresh recomputation. Any edited field, deleted row or reordering breaks
    one of these checks, so the function returns ``False`` for a trail that has
    been tampered with and ``True`` otherwise (including for an empty store).
    """
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM audit_records ORDER BY id ASC").fetchall()

    running_prev = GENESIS_HASH
    for row in rows:
        if row["prev_hash"] != running_prev:
            return False
        expected = _compute_hash(running_prev, {k: row[k] for k in _HASHED_FIELDS})
        if expected != row["record_hash"]:
            return False
        running_prev = row["record_hash"]
    return True


def _canonical(record):
    """Deterministic serialization of the signed fields.

    ``sort_keys`` plus compact separators make the byte string reproducible
    across processes and Python versions, so a hash computed at append time
    recomputes identically during verification.
    """
    payload = {field: record[field] for field in _HASHED_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hash(prev_hash, record):
    return hashlib.sha256((prev_hash + _canonical(record)).encode("utf-8")).hexdigest()

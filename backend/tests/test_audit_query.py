"""Tests for audit trail querying and retention pruning (issue #1023)."""

from   datetime                 import datetime, timedelta, timezone
from   pathlib                  import Path
import sys

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))

import audit_store

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _ts(days_ago):
    return (NOW - timedelta(days=days_ago)).isoformat()


@pytest.fixture
def store(tmp_path, monkeypatch):
    db_path = tmp_path / "audit_query_test.db"
    monkeypatch.setattr(audit_store, "DB_PATH", str(db_path))
    audit_store.init_db()
    return audit_store


def test_query_returns_newest_first(store):
    store.append("alice", "predict", "message", "req-1", 200)
    store.append("bob", "predict", "message", "req-2", 200)
    store.append("carol", "predict", "message", "req-3", 200)

    records = store.query()

    assert [r["actor"] for r in records] == ["carol", "bob", "alice"]


def test_filter_by_actor_action_and_resource(store):
    store.append("alice", "predict", "message", "req-1", 200)
    store.append("alice", "reload_model", "model", "req-2", 200)
    store.append("bob", "predict", "message", "req-3", 200)

    assert {r["request_id"] for r in store.query(actor="alice")} == {"req-1", "req-2"}
    assert {r["request_id"] for r in store.query(action="predict")} == {
        "req-1",
        "req-3",
    }
    assert {r["request_id"] for r in store.query(resource="model")} == {"req-2"}
    # Filters compose (AND semantics).
    assert {r["request_id"] for r in store.query(actor="alice", action="predict")} == {
        "req-1"
    }


def test_time_window_filters_are_inclusive(store):
    store.append("alice", "predict", "message", "old", 200, timestamp=_ts(10))
    store.append("alice", "predict", "message", "mid", 200, timestamp=_ts(5))
    store.append("alice", "predict", "message", "new", 200, timestamp=_ts(1))

    assert {r["request_id"] for r in store.query(since=_ts(5))} == {"mid", "new"}
    assert {r["request_id"] for r in store.query(until=_ts(5))} == {"old", "mid"}
    assert {r["request_id"] for r in store.query(since=_ts(5), until=_ts(5))} == {"mid"}


def test_pagination_limit_and_offset(store):
    for i in range(5):
        store.append("alice", "predict", "message", f"req-{i}", 200)

    first_page = store.query(limit=2)
    second_page = store.query(limit=2, offset=2)

    assert [r["request_id"] for r in first_page] == ["req-4", "req-3"]
    assert [r["request_id"] for r in second_page] == ["req-2", "req-1"]


def test_limit_is_clamped_to_sane_bounds(store):
    for i in range(3):
        store.append("alice", "predict", "message", f"req-{i}", 200)

    # Oversized limit returns everything without error; a zero limit still
    # yields at least one row rather than an empty/invalid query.
    assert len(store.query(limit=10_000)) == 3
    assert len(store.query(limit=0)) == 1


def test_prune_deletes_records_older_than_window(store):
    store.append("alice", "predict", "message", "ancient", 200, timestamp=_ts(120))
    store.append("alice", "predict", "message", "old", 200, timestamp=_ts(45))
    store.append("alice", "predict", "message", "recent", 200, timestamp=_ts(5))

    deleted = store.prune(retention_days=30, now=NOW)

    assert deleted == 2
    remaining = {r["request_id"] for r in store.query()}
    assert remaining == {"recent"}


def test_prune_reseals_so_chain_still_verifies(store):
    store.append("alice", "predict", "message", "ancient", 200, timestamp=_ts(120))
    store.append("bob", "predict", "message", "old", 200, timestamp=_ts(45))
    store.append("carol", "predict", "message", "recent", 200, timestamp=_ts(5))

    store.prune(retention_days=30, now=NOW)

    assert store.verify_chain() is True


def test_prune_is_a_noop_for_nonpositive_window(store):
    store.append("alice", "predict", "message", "old", 200, timestamp=_ts(400))

    assert store.prune(retention_days=0, now=NOW) == 0
    assert len(store.query()) == 1

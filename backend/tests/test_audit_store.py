"""Tests for the tamper-evident audit store (issue #1023)."""

from   pathlib                  import Path
import sqlite3
import sys

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))

import audit_store


@pytest.fixture
def store(tmp_path, monkeypatch):
    db_path = tmp_path / "audit_test.db"
    monkeypatch.setattr(audit_store, "DB_PATH", str(db_path))
    audit_store.init_db()
    return audit_store


def test_empty_chain_is_intact(store):
    assert store.verify_chain() is True


def test_first_record_links_to_genesis(store):
    record = store.append("alice", "predict", "message", "req-1", 200)

    assert record["prev_hash"] == audit_store.GENESIS_HASH
    assert record["id"] == 1
    assert store.verify_chain() is True


def test_appended_records_chain_and_verify(store):
    first = store.append("alice", "predict", "message", "req-1", 200)
    second = store.append("bob", "reload_model", "model", "req-2", 500)
    third = store.append("carol", "feedback", "label", "req-3", 201)

    # Each record commits to its predecessor's hash.
    assert second["prev_hash"] == first["record_hash"]
    assert third["prev_hash"] == second["record_hash"]
    assert store.verify_chain() is True


def test_edited_row_is_detected(store):
    store.append("alice", "predict", "message", "req-1", 200)
    store.append("bob", "reload_model", "model", "req-2", 200)

    # Rewrite a persisted field directly, simulating a database-level edit that
    # leaves the stored record_hash untouched.
    with sqlite3.connect(store.DB_PATH) as conn:
        conn.execute("UPDATE audit_records SET actor = ? WHERE id = 1", ("mallory",))
        conn.commit()

    assert store.verify_chain() is False


def test_edited_status_is_detected(store):
    store.append("alice", "predict", "message", "req-1", 200)

    with sqlite3.connect(store.DB_PATH) as conn:
        conn.execute("UPDATE audit_records SET status = ? WHERE id = 1", (403,))
        conn.commit()

    assert store.verify_chain() is False


def test_deleted_row_is_detected(store):
    store.append("alice", "predict", "message", "req-1", 200)
    store.append("bob", "reload_model", "model", "req-2", 200)
    store.append("carol", "feedback", "label", "req-3", 200)

    # Removing an interior record orphans the prev_hash linkage of its
    # successor, which verification must catch.
    with sqlite3.connect(store.DB_PATH) as conn:
        conn.execute("DELETE FROM audit_records WHERE id = 2")
        conn.commit()

    assert store.verify_chain() is False

import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "email_connectors"))

import imap_store


@pytest.fixture
def store(tmp_path, monkeypatch):
    db_path = tmp_path / "imap_test.db"
    monkeypatch.setattr(imap_store, "DB_PATH", str(db_path))
    imap_store.init_db()
    return imap_store


def test_save_and_get_connection_round_trips(store):
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass", 30)

    row = store.get_connection("alice")
    assert row["host"] == "imap.example.com"
    assert row["scan_interval_minutes"] == 30
    assert row["last_scan_at"] is None


def test_save_connection_upserts_existing_user(store):
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass", 30)
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass-2", 60)

    row = store.get_connection("alice")
    assert row["scan_interval_minutes"] == 60
    assert row["encrypted_password"] == "enc-pass-2"


def test_update_schedule(store):
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass", 30)
    store.update_schedule("alice", 15)

    assert store.get_connection("alice")["scan_interval_minutes"] == 15


def test_update_last_scan_sets_timestamp(store):
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass", 30)
    store.update_last_scan("alice")

    assert store.get_connection("alice")["last_scan_at"] is not None


def test_delete_connection_removes_row_and_history(store):
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass", 30)
    store.save_scan_results("alice", [{"id": "1", "subject": "Hi", "sender": "a@b.com", "date": "x", "prediction": "ham"}])

    store.delete_connection("alice")

    assert store.get_connection("alice") is None
    assert store.get_scan_history("alice") == []


def test_save_and_get_scan_history_ordered_most_recent_first(store):
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass", 30)
    store.save_scan_results("alice", [
        {"id": "1", "subject": "First", "sender": "a@b.com", "date": "x", "prediction": "ham"},
    ])
    store.save_scan_results("alice", [
        {"id": "2", "subject": "Second", "sender": "a@b.com", "date": "x", "prediction": "spam"},
    ])

    history = store.get_scan_history("alice")
    assert len(history) == 2
    assert history[0]["subject"] == "Second"


def test_get_all_active_connections(store):
    store.save_connection("alice", "imap.example.com", 993, "alice@example.com", "enc-pass", 30)
    store.save_connection("bob", "imap.other.com", 993, "bob@other.com", "enc-pass-2", 15)

    usernames = {row["username"] for row in store.get_all_active_connections()}
    assert usernames == {"alice", "bob"}

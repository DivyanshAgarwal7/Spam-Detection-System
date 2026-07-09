import sys
from pathlib import Path
import pytest
from cryptography.fernet import Fernet
import oauth_store
import imap_store
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "email_connectors"))




@pytest.fixture
def store(tmp_path, monkeypatch):
    db_path = tmp_path / "oauth_test.db"
    monkeypatch.setattr(imap_store, "DB_PATH", str(db_path))
    monkeypatch.setattr(oauth_store, "DB_PATH", str(db_path))
    monkeypatch.setenv("IMAP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    oauth_store.init_db()
    return oauth_store


def test_save_and_get_oauth_tokens(store):
    tokens = {
        "access_token": "test_access",
        "refresh_token": "test_refresh",
        "expires_in": 3600
    }
    store.save_oauth_tokens("user1", "gmail", tokens)

    retrieved = store.get_oauth_tokens("user1", "gmail")
    assert retrieved is not None
    assert retrieved["access_token"] == "test_access"
    assert retrieved["refresh_token"] == "test_refresh"
    assert retrieved["expires_at"] is not None
    assert retrieved["updated_at"] is not None


def test_save_preserves_old_refresh_token(store):
    tokens1 = {
        "access_token": "access_one",
        "refresh_token": "refresh_one",
        "expires_in": 3600
    }
    store.save_oauth_tokens("user1", "gmail", tokens1)

    tokens2 = {
        "access_token": "access_two",
        "expires_in": 1800
    }
    # Save tokens2 which lacks refresh_token, it should preserve the old one
    store.save_oauth_tokens("user1", "gmail", tokens2)

    retrieved = store.get_oauth_tokens("user1", "gmail")
    assert retrieved["access_token"] == "access_two"
    assert retrieved["refresh_token"] == "refresh_one"


def test_delete_oauth_tokens(store):
    tokens = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 3600
    }
    store.save_oauth_tokens("user1", "gmail", tokens)
    store.save_oauth_tokens("user1", "outlook", tokens)

    # Delete only outlook
    store.delete_oauth_tokens("user1", "outlook")
    assert store.get_oauth_tokens("user1", "outlook") is None
    assert store.get_oauth_tokens("user1", "gmail") is not None

    # Delete all for user
    store.delete_oauth_tokens("user1")
    assert store.get_oauth_tokens("user1", "gmail") is None


def test_get_all_oauth_tokens(store):
    tokens = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 3600
    }
    store.save_oauth_tokens("user1", "gmail", tokens)
    store.save_oauth_tokens("user2", "outlook", tokens)

    all_tokens = store.get_all_oauth_tokens()
    assert len(all_tokens) == 2
    users = {t["username"] for t in all_tokens}
    assert users == {"user1", "user2"}


def test_get_expiring_oauth_tokens(store):
    # One token expiring soon (under 10 mins threshold)
    tokens_expiring = {
        "access_token": "access_exp",
        "refresh_token": "refresh_exp",
        "expires_in": 200
    }
    # One token expiring later
    tokens_later = {
        "access_token": "access_lat",
        "refresh_token": "refresh_lat",
        "expires_in": 3600
    }

    store.save_oauth_tokens("expiring_user", "gmail", tokens_expiring)
    store.save_oauth_tokens("stable_user", "outlook", tokens_later)

    expiring = store.get_expiring_oauth_tokens(threshold_minutes=10)
    assert len(expiring) == 1
    assert expiring[0]["username"] == "expiring_user"

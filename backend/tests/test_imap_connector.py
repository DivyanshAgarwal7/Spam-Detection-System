import sys
import imaplib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "email_connectors"))

import imap_connector


def _mock_fetch_response(msg_id, raw_bytes):
    return "OK", [(msg_id, raw_bytes)]


@patch("imaplib.IMAP4_SSL")
def test_test_imap_connection_success(mock_imap_cls):
    mock_conn = MagicMock()
    mock_conn.select.return_value = ("OK", [b"1"])
    mock_imap_cls.return_value = mock_conn

    imap_connector.test_imap_connection("imap.example.com", 993, "user@example.com", "secret")

    mock_conn.login.assert_called_once_with("user@example.com", "secret")
    mock_conn.select.assert_called_once_with("INBOX", readonly=True)
    mock_conn.logout.assert_called_once()


@patch("imaplib.IMAP4_SSL")
def test_test_imap_connection_bad_credentials_raises(mock_imap_cls):
    mock_conn = MagicMock()
    mock_conn.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
    mock_imap_cls.return_value = mock_conn

    with pytest.raises(imap_connector.ImapAuthError):
        imap_connector.test_imap_connection("imap.example.com", 993, "user@example.com", "wrong")

    mock_conn.logout.assert_called_once()


@patch("imaplib.IMAP4_SSL")
def test_fetch_imap_emails_parses_messages(mock_imap_cls):
    raw_email = (
        b"From: spammer@bad.com\r\n"
        b"Subject: Big Deals!\r\n"
        b"Date: Thu, 18 Jun 2026 12:00:00 GMT\r\n"
        b"Content-Type: text/plain\r\n\r\n"
        b"Claim your free prize now!"
    )

    mock_conn = MagicMock()
    mock_conn.select.return_value = ("OK", [b"1"])
    mock_conn.search.return_value = ("OK", [b"1"])
    mock_conn.fetch.return_value = _mock_fetch_response(b"1", raw_email)
    mock_imap_cls.return_value = mock_conn

    emails = imap_connector.fetch_imap_emails("imap.example.com", 993, "user@example.com", "secret", limit=10)

    assert len(emails) == 1
    assert emails[0]["sender"] == "spammer@bad.com"
    assert emails[0]["subject"] == "Big Deals!"
    assert "Claim your free prize now!" in emails[0]["body"]
    assert "From: spammer@bad.com" in emails[0]["raw_headers"]
    mock_conn.logout.assert_called_once()


@patch("imaplib.IMAP4_SSL")
def test_fetch_imap_emails_no_messages_returns_empty_list(mock_imap_cls):
    mock_conn = MagicMock()
    mock_conn.select.return_value = ("OK", [b"0"])
    mock_conn.search.return_value = ("OK", [b""])
    mock_imap_cls.return_value = mock_conn

    emails = imap_connector.fetch_imap_emails("imap.example.com", 993, "user@example.com", "secret")

    assert emails == []

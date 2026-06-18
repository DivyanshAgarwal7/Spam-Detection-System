import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "email_connectors"))

import gmail_connector

def test_get_gmail_auth_url():
    url = gmail_connector.get_gmail_auth_url("http://test/callback")
    assert "https://accounts.google.com/o/oauth2/v2/auth" in url
    assert "client_id=" in url
    assert "redirect_uri=http%3A%2F%2Ftest%2Fcallback" in url
    assert "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly" in url

@patch("requests.post")
def test_get_gmail_tokens(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_in": 3600
    }
    mock_post.return_value = mock_response

    tokens = gmail_connector.get_gmail_tokens("mock_code", "http://test/callback")
    assert tokens["access_token"] == "mock_access_token"
    assert tokens["refresh_token"] == "mock_refresh_token"
    mock_post.assert_called_once()

@patch("requests.post")
def test_refresh_gmail_token(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_mock_access_token",
        "expires_in": 3600
    }
    mock_post.return_value = mock_response

    tokens = gmail_connector.refresh_gmail_token("mock_refresh_token")
    assert tokens["access_token"] == "new_mock_access_token"
    mock_post.assert_called_once()

@patch("requests.get")
def test_fetch_gmail_emails(mock_get):
    # Mock search response
    mock_search_response = MagicMock()
    mock_search_response.json.return_value = {
        "messages": [
            {"id": "msg_123"},
            {"id": "msg_456"}
        ]
    }
    
    # Mock detail response
    mock_detail_response_1 = MagicMock()
    mock_detail_response_1.status_code = 200
    mock_detail_response_1.json.return_value = {
        "id": "msg_123",
        "snippet": "Hello, check this great deal!",
        "payload": {
            "headers": [
                {"name": "From", "value": "spammer@bad.com"},
                {"name": "Subject", "value": "Big Deals!"},
                {"name": "Date", "value": "Thu, 18 Jun 2026 12:00:00 GMT"}
            ]
        }
    }

    mock_detail_response_2 = MagicMock()
    mock_detail_response_2.status_code = 200
    mock_detail_response_2.json.return_value = {
        "id": "msg_456",
        "snippet": "Are we meeting tomorrow?",
        "payload": {
            "headers": [
                {"name": "From", "value": "friend@good.com"},
                {"name": "Subject", "value": "Meeting tomorrow"},
                {"name": "Date", "value": "Thu, 18 Jun 2026 12:10:00 GMT"}
            ]
        }
    }

    mock_get.side_effect = [mock_search_response, mock_detail_response_1, mock_detail_response_2]

    emails = gmail_connector.fetch_gmail_emails("mock_access_token", limit=2)
    assert len(emails) == 2
    
    assert emails[0]["id"] == "msg_123"
    assert emails[0]["sender"] == "spammer@bad.com"
    assert emails[0]["subject"] == "Big Deals!"
    assert emails[0]["body"] == "Hello, check this great deal!"
    assert "From: spammer@bad.com" in emails[0]["raw_headers"]

    assert emails[1]["id"] == "msg_456"
    assert emails[1]["sender"] == "friend@good.com"
    assert emails[1]["subject"] == "Meeting tomorrow"
    assert emails[1]["body"] == "Are we meeting tomorrow?"

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "email_connectors"))

import outlook_connector

def test_get_outlook_auth_url():
    url = outlook_connector.get_outlook_auth_url("http://test/callback")
    assert "https://login.microsoftonline.com/common/oauth2/v2.0/authorize" in url
    assert "client_id=" in url
    assert "redirect_uri=http%3A%2F%2Ftest%2Fcallback" in url
    assert "scope=https%3A%2F%2Fgraph.microsoft.com%2FMail.Read+offline_access" in url

@patch("requests.post")
def test_get_outlook_tokens(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "mock_outlook_access_token",
        "refresh_token": "mock_outlook_refresh_token",
        "expires_in": 3600
    }
    mock_post.return_value = mock_response

    tokens = outlook_connector.get_outlook_tokens("mock_code", "http://test/callback")
    assert tokens["access_token"] == "mock_outlook_access_token"
    assert tokens["refresh_token"] == "mock_outlook_refresh_token"
    mock_post.assert_called_once()

@patch("requests.post")
def test_refresh_outlook_token(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_mock_outlook_access_token",
        "expires_in": 3600
    }
    mock_post.return_value = mock_response

    tokens = outlook_connector.refresh_outlook_token("mock_refresh_token")
    assert tokens["access_token"] == "new_mock_outlook_access_token"
    mock_post.assert_called_once()

@patch("requests.get")
def test_fetch_outlook_emails(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {
                "id": "out_123",
                "subject": "Discount on services",
                "sender": {
                    "emailAddress": {
                        "name": "Sale Agent",
                        "address": "sales@discount.com"
                    }
                },
                "bodyPreview": "Take 50% off your next order.",
                "receivedDateTime": "2026-06-18T10:00:00Z",
                "internetMessageHeaders": [
                    {"name": "From", "value": "sales@discount.com"},
                    {"name": "SPF", "value": "pass"}
                ]
            }
        ]
    }
    mock_get.return_value = mock_response

    emails = outlook_connector.fetch_outlook_emails("mock_access_token", limit=1)
    assert len(emails) == 1
    assert emails[0]["id"] == "out_123"
    assert emails[0]["sender"] == "Sale Agent <sales@discount.com>"
    assert emails[0]["subject"] == "Discount on services"
    assert emails[0]["body"] == "Take 50% off your next order."
    assert emails[0]["date"] == "2026-06-18T10:00:00Z"
    assert "SPF: pass" in emails[0]["raw_headers"]

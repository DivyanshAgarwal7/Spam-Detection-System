import os
import urllib.parse
import requests

MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")

def get_outlook_auth_url(redirect_uri):
    """Generates the Microsoft Graph OAuth 2.0 authorization URL."""
    params = {
        "client_id": MICROSOFT_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://graph.microsoft.com/Mail.Read offline_access",
        "response_mode": "query"
    }
    return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)

def get_outlook_tokens(code, redirect_uri):
    """Exchanges authorization code for Microsoft access and refresh tokens."""
    data = {
        "client_id": MICROSOFT_CLIENT_ID,
        "client_secret": MICROSOFT_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    response = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data)
    response.raise_for_status()
    return response.json()

def refresh_outlook_token(refresh_token):
    """Refreshes the Microsoft access token using the refresh token."""
    data = {
        "client_id": MICROSOFT_CLIENT_ID,
        "client_secret": MICROSOFT_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data)
    response.raise_for_status()
    return response.json()

def fetch_outlook_emails(access_token, limit=50):
    """Fetches latest email fields and headers from Microsoft Graph API."""
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/me/messages?$top={limit}&$select=subject,sender,bodyPreview,receivedDateTime,internetMessageHeaders"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    res = r.json()
    
    emails = []
    messages = res.get("value", [])
    for m in messages:
        subject = m.get("subject") or "No Subject"
        sender_obj = m.get("sender", {}).get("emailAddress", {})
        sender_name = sender_obj.get("name", "")
        sender_email = sender_obj.get("address", "")
        sender = f"{sender_name} <{sender_email}>" if sender_name else sender_email
        
        body_preview = m.get("bodyPreview") or ""
        date = m.get("receivedDateTime") or "Unknown Date"
        
        # Build raw headers block from internetMessageHeaders if present
        raw_headers_list = []
        headers_data = m.get("internetMessageHeaders", []) or []
        for h in headers_data:
            raw_headers_list.append(f"{h.get('name')}: {h.get('value')}")
        raw_headers = "\n".join(raw_headers_list)
        
        emails.append({
            "id": m.get("id"),
            "subject": subject,
            "sender": sender,
            "body": body_preview,
            "date": date,
            "raw_headers": raw_headers
        })
        
    return emails

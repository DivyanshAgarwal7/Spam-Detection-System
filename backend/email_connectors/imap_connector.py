import imaplib
import email
from email.header import decode_header


class ImapAuthError(Exception):
    """Raised when the IMAP server rejects the supplied credentials."""


def _connect(host, port, username, password):
    """Opens a read-only IMAP connection and selects the inbox.

    Raises ImapAuthError on bad credentials so callers can return a 401
    instead of a generic 500.
    """
    conn = imaplib.IMAP4_SSL(host, int(port))
    try:
        conn.login(username, password)
    except imaplib.IMAP4.error as exc:
        conn.logout()
        raise ImapAuthError(str(exc)) from exc

    status, _ = conn.select("INBOX", readonly=True)
    if status != "OK":
        conn.logout()
        raise ImapAuthError("Unable to open INBOX in read-only mode")
    return conn


def test_imap_connection(host, port, username, password):
    """Verifies that the given IMAP credentials can open the inbox read-only."""
    conn = _connect(host, port, username, password)
    conn.logout()


def _decode_value(raw_value):
    if not raw_value:
        return ""
    parts = decode_header(raw_value)
    decoded = ""
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded += text.decode(charset or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def fetch_imap_emails(host, port, username, password, limit=50):
    """Fetches the most recent emails from the inbox over a read-only IMAP session."""
    conn = _connect(host, port, username, password)
    try:
        status, data = conn.search(None, "ALL")
        if status != "OK":
            return []

        message_ids = data[0].split()
        message_ids = message_ids[-limit:] if limit else message_ids

        emails = []
        for msg_id in reversed(message_ids):
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            raw_headers = "\n".join(
                f"{name}: {value}" for name, value in msg.items()
            )

            emails.append({
                "id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                "subject": _decode_value(msg.get("Subject")) or "No Subject",
                "sender": _decode_value(msg.get("From")) or "Unknown Sender",
                "body": _extract_body(msg)[:2000],
                "date": msg.get("Date", "Unknown Date"),
                "raw_headers": raw_headers,
            })

        return emails
    finally:
        conn.logout()

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi_backend.database import (
    insert_email,
    mark_email,
    get_spam_emails,
    get_legitimate_emails,
    count_spam,
    count_legitimate,
)

router = APIRouter(prefix="/api/emails", tags=["emails"])


class EmailIn(BaseModel):
    subject: str
    sender:  str
    is_spam: bool = False


class MarkIn(BaseModel):
    is_spam: bool


# ── INSERT ───────────────────────────────────────────────────────────────────

@router.post("/")
def create_email(body: EmailIn):
    """Insert a new email record."""
    try:
        new_id = insert_email(body.subject, body.sender, body.is_spam)
        return {"success": True, "email_id": new_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── UPDATE ───────────────────────────────────────────────────────────────────

@router.patch("/{email_id}/mark")
def mark_email_status(email_id: int, body: MarkIn):
    """Mark an email as spam or legitimate."""
    try:
        updated = mark_email(email_id, body.is_spam)
        if not updated:
            raise HTTPException(status_code=404, detail="Email not found.")
        return {"success": True, "email_id": email_id, "is_spam": body.is_spam}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── RETRIEVE ─────────────────────────────────────────────────────────────────

@router.get("/spam")
def list_spam():
    """Retrieve all spam emails."""
    try:
        return {"success": True, "emails": get_spam_emails()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/legitimate")
def list_legitimate():
    """Retrieve all legitimate emails."""
    try:
        return {"success": True, "emails": get_legitimate_emails()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── COUNT ────────────────────────────────────────────────────────────────────

@router.get("/count/spam")
def total_spam():
    """Count total spam emails."""
    try:
        return {"success": True, "count": count_spam()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/count/legitimate")
def total_legitimate():
    """Count total legitimate emails."""
    try:
        return {"success": True, "count": count_legitimate()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
import csv
import io
from fpdf import FPDF
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from database import get_connection

router = APIRouter(prefix="/api/emails", tags=["export"])


def get_all_emails() -> list:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM emails ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# ── CSV EXPORT ───────────────────────────────────────────────────────────────

def generate_csv(emails: list) -> io.StringIO:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["email_id", "subject", "sender", "is_spam", "timestamp"],
    )
    writer.writeheader()
    for email in emails:
        writer.writerow({
            "email_id":  email["email_id"],
            "subject":   email["subject"],
            "sender":    email["sender"],
            "is_spam":   "Spam" if email["is_spam"] else "Legitimate",
            "timestamp": str(email["timestamp"]),
        })
    output.seek(0)
    return output


# ── PDF EXPORT ───────────────────────────────────────────────────────────────

def generate_pdf(emails: list) -> io.BytesIO:
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Email Classification Report", ln=True, align="C")
    pdf.ln(4)

    # Summary
    total      = len(emails)
    spam_count = sum(1 for e in emails if e["is_spam"])
    legit_count = total - spam_count

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Total Emails: {total}", ln=True)
    pdf.cell(0, 8, f"Spam: {spam_count}  |  Legitimate: {legit_count}", ln=True)
    pdf.ln(6)

    # Table header
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(12,  8, "ID",         border=1, fill=True)
    pdf.cell(70,  8, "Subject",    border=1, fill=True)
    pdf.cell(55,  8, "Sender",     border=1, fill=True)
    pdf.cell(25,  8, "Status",     border=1, fill=True)
    pdf.cell(35,  8, "Timestamp",  border=1, fill=True, ln=True)

    # Table rows
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    for i, email in enumerate(emails):
        fill = i % 2 == 0
        pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
        status = "SPAM" if email["is_spam"] else "LEGIT"
        pdf.cell(12,  7, str(email["email_id"]),          border=1, fill=fill)
        pdf.cell(70,  7, str(email["subject"])[:40],      border=1, fill=fill)
        pdf.cell(55,  7, str(email["sender"])[:30],       border=1, fill=fill)
        pdf.cell(25,  7, status,                          border=1, fill=fill)
        pdf.cell(35,  7, str(email["timestamp"])[:16],    border=1, fill=fill, ln=True)

    buf = io.BytesIO(pdf.output())
    buf.seek(0)
    return buf


# ── EXPORT ENDPOINT ──────────────────────────────────────────────────────────

@router.get("/export")
def export_emails(format: str = Query(default="csv", pattern="^(csv|pdf)$")):
    """
    Export all email records.
    - GET /api/emails/export?format=csv
    - GET /api/emails/export?format=pdf
    """
    try:
        emails = get_all_emails()
        if not emails:
            raise HTTPException(status_code=404, detail="No email records found.")

        if format == "csv":
            output = generate_csv(emails)
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=email_report.csv"
                },
            )

        if format == "pdf":
            buf = generate_pdf(emails)
            return StreamingResponse(
                buf,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=email_report.pdf"
                },
            )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
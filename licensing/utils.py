"""
Utility functions for the licensing app.
"""
import io
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone


# ─── REFERENCE NUMBERS ────────────────────────────────────────────────────────

def generate_licence_reference() -> str:
    """
    Generate a unique application reference number: LIC-YYYY-NNNNNN
    Checks the database for collisions and increments if needed.
    """
    from .models import Application
    year = timezone.now().year
    prefix = f"LIC-{year}-"
    last = (
        Application.objects.filter(reference_number__startswith=prefix)
        .order_by("reference_number")
        .values_list("reference_number", flat=True)
        .last()
    )
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:06d}"


def generate_licence_number(type_code: str) -> str:
    """
    Generate a unique issued licence number: LIC-{CODE}-YYYY-NNNNNN
    e.g. LIC-ISP-2026-000001
    """
    from .models import Licence
    year = timezone.now().year
    prefix = f"LIC-{type_code}-{year}-"
    last = (
        Licence.objects.filter(licence_number__startswith=prefix)
        .order_by("licence_number")
        .values_list("licence_number", flat=True)
        .last()
    )
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:06d}"


def calculate_expiry_date(issued_date: date, validity_months: int) -> date:
    """Return the expiry date given an issue date and validity period in months."""
    return issued_date + relativedelta(months=validity_months)


# ─── PDF CERTIFICATE ──────────────────────────────────────────────────────────

def generate_certificate_pdf(licence) -> bytes:
    """
    Generate a simple text-based PDF certificate for an issued licence.
    Returns the PDF as bytes.

    Uses only the standard library reportlab if available, otherwise
    falls back to a plain-text PDF so the demo always works.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # ── Header ─────────────────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2, height - 3 * cm, "BOTSWANA COMMUNICATIONS REGULATORY AUTHORITY")
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 4.2 * cm, "LICENCE CERTIFICATE")

        # ── Divider ─────────────────────────────────────────────────────────
        c.line(2 * cm, height - 4.8 * cm, width - 2 * cm, height - 4.8 * cm)

        # ── Body ─────────────────────────────────────────────────────────────
        c.setFont("Helvetica", 12)
        lines = [
            f"Licence Number:   {licence.licence_number}",
            f"Licence Type:     {licence.licence_type.name} ({licence.licence_type.code})",
            f"Holder:           {licence.organisation_name}",
            f"Issued Date:      {licence.issued_date.strftime('%d %B %Y')}",
            f"Expiry Date:      {licence.expiry_date.strftime('%d %B %Y')}",
            f"Status:           {licence.get_status_display()}",
        ]
        y = height - 7 * cm
        for line in lines:
            c.drawString(3 * cm, y, line)
            y -= 1 * cm

        if licence.conditions:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(3 * cm, y - 0.5 * cm, "Conditions:")
            c.setFont("Helvetica", 10)
            y -= 1.5 * cm
            for condition_line in licence.conditions.splitlines():
                c.drawString(3 * cm, y, condition_line[:90])
                y -= 0.7 * cm

        # ── Footer ────────────────────────────────────────────────────────────
        c.line(2 * cm, 3 * cm, width - 2 * cm, 3 * cm)
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(
            width / 2, 2.3 * cm,
            "This certificate is issued under the authority of BOCRA. "
            "Verify at bocra.org.bw/verify"
        )
        c.drawCentredString(
            width / 2, 1.7 * cm,
            f"Generated: {date.today().strftime('%d %B %Y')}"
        )

        c.showPage()
        c.save()
        return buffer.getvalue()

    except ImportError:
        # Fallback: minimal but valid PDF bytes (plain text)
        content = (
            f"%PDF-1.4\n"
            f"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            f"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]\n"
            f"  /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            f"4 0 obj << /Length 200 >>\nstream\n"
            f"BT /F1 12 Tf 50 750 Td "
            f"(BOCRA Licence Certificate) Tj\n"
            f"0 -20 Td (Licence: {licence.licence_number}) Tj\n"
            f"0 -20 Td (Holder: {licence.organisation_name}) Tj\n"
            f"0 -20 Td (Issued: {licence.issued_date}) Tj\n"
            f"0 -20 Td (Expires: {licence.expiry_date}) Tj\n"
            f"ET\nendstream\nendobj\n"
            f"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            f"xref\n0 6\n"
            f"trailer << /Size 6 /Root 1 0 R >>\n"
            f"startxref\n0\n%%EOF"
        )
        return content.encode("latin-1")

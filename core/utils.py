import os
import re
import string
import random
import unicodedata
from datetime import date, datetime, timedelta

from django.utils import timezone


# ─── REFERENCE NUMBERS ────────────────────────────────────────────────────────

def generate_reference_number(prefix: str, length: int = 8) -> str:
    """
    Generate a unique reference number with a prefix.
    Example: generate_reference_number('LIC') → 'LIC-20260001'
    """
    digits = "".join(random.choices(string.digits, k=length))
    return f"{prefix}-{digits}"


# ─── BOTSWANA PHONE NUMBERS ───────────────────────────────────────────────────

_BW_PHONE_RE = re.compile(r"^(\+267|267)?[0-9]{8}$")


def validate_botswana_phone_number(phone: str) -> bool:
    """
    Returns True if the phone number is a valid Botswana format.
    Accepts: +267XXXXXXXX, 267XXXXXXXX, XXXXXXXX (8 digits).
    """
    if not phone:
        return False
    cleaned = re.sub(r"[\s\-()]", "", phone)
    return bool(_BW_PHONE_RE.match(cleaned))


def format_botswana_phone_number(phone: str) -> str:
    """
    Normalise a Botswana phone number to +267XXXXXXXX.
    Raises ValueError if the number is not valid.
    """
    cleaned = re.sub(r"[\s\-()]", "", phone)
    if cleaned.startswith("+267"):
        digits = cleaned[4:]
    elif cleaned.startswith("267"):
        digits = cleaned[3:]
    else:
        digits = cleaned

    if len(digits) != 8 or not digits.isdigit():
        raise ValueError(f"Invalid Botswana phone number: {phone}")
    return f"+267{digits}"


# ─── BOTSWANA ID / PASSPORT ───────────────────────────────────────────────────

_OMANG_RE = re.compile(r"^\d{6}/\d{2}/\d{1}$")       # 123456/01/1
_OMANG_PLAIN_RE = re.compile(r"^\d{9}$")               # 9 digits no separators
_PASSPORT_RE = re.compile(r"^[A-Z]{2}\d{7}$")          # BP1234567


def validate_botswana_id_number(id_number: str) -> bool:
    """
    Returns True if the value looks like a valid Botswana Omang or passport number.
    """
    if not id_number:
        return False
    val = id_number.strip().upper()
    return bool(
        _OMANG_RE.match(val)
        or _OMANG_PLAIN_RE.match(val)
        or _PASSPORT_RE.match(val)
    )


# ─── DATES ────────────────────────────────────────────────────────────────────

def calculate_age(birth_date: date) -> int:
    """Return the age in whole years for a given birth date."""
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def get_date_range(period: str) -> tuple:
    """
    Return (start_date, end_date) for a named period.
    Supported: 'today', 'week', 'month', 'year'.
    """
    now = timezone.now()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = now
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "year":
        start = now.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = now
    else:
        raise ValueError(f"Unsupported period: {period}. Use one of: today, week, month, year")
    return start, end


# ─── FILE UTILITIES ────────────────────────────────────────────────────────────

def get_file_extension(filename: str) -> str:
    """Return the lowercase extension including dot, e.g. '.pdf'."""
    return os.path.splitext(filename)[1].lower()


def format_file_size(size_bytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def sanitize_filename(filename: str) -> str:
    """Remove characters that are unsafe in filenames."""
    name, ext = os.path.splitext(filename)
    # Normalise unicode to ASCII
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    # Keep only alphanumerics, hyphens, underscores, spaces
    name = re.sub(r"[^\w\s\-]", "", name).strip()
    name = re.sub(r"\s+", "_", name)
    return f"{name}{ext}"


def generate_unique_filename(filename: str, existing_files: set) -> str:
    """Append a counter to filename if it already exists in existing_files."""
    if filename not in existing_files:
        return filename
    name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        candidate = f"{name}_{counter}{ext}"
        if candidate not in existing_files:
            return candidate
        counter += 1


# ─── EMAIL ────────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email or ""))


# ─── TEXT ─────────────────────────────────────────────────────────────────────

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max_length characters, appending '...' if needed."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


# ─── API RESPONSE HELPERS ─────────────────────────────────────────────────────

def api_success(data=None, message: str = "Success", status: int = 200) -> dict:
    """
    Build a standardised success response body as per the BOCRA API design spec.

    Usage in a view:
        return Response(api_success(serializer.data, "User retrieved"), status=200)
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "errors": None,
    }


def api_error(message: str = "An error occurred", errors=None, status: int = 400) -> dict:
    """
    Build a standardised error response body as per the BOCRA API design spec.

    Usage in a view:
        return Response(api_error("Validation failed", serializer.errors), status=400)
    """
    return {
        "success": False,
        "message": message,
        "data": None,
        "errors": errors,
    }

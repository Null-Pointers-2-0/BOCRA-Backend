"""
Utility functions for the BOCRA Digital Platform.
"""
import uuid
import re
import string
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError


def generate_reference_number(prefix, length=8):
    """
    Generate a unique reference number with prefix.
    
    Args:
        prefix (str): Prefix for the reference number
        length (int): Length of the random part
        
    Returns:
        str: Unique reference number
        
    Example:
        >>> generate_reference_number('LIC')
        'LIC-12345678'
    """
    # Generate random number
    digits = "".join(random.choices(string.digits, k=length))
    return f"{prefix}-{digits}"


# ─── BOTSWANA PHONE NUMBERS ────────────────────────────────────────────────────

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
        raise ValueError("Invalid Botswana phone number")

    return f"+267{digits}"


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


def validate_botswana_phone_number(phone_number):
    """
    Validate Botswana phone number format.
    
    Args:
        phone_number (str): Phone number to validate
        
    Returns:
        bool: True if valid, False otherwise
        
    Valid formats:
        - +267XXXXXXXX
        - 267XXXXXXXX
        - XXXXXXXX (local format)
    """
    if not phone_number:
        return False
    
    # Remove any non-digit characters
    clean_number = re.sub(r'[^\d]', '', phone_number)
    
    # Check if it's a Botswana number
    if clean_number.startswith('267'):
        # International format: +267XXXXXXXX or 267XXXXXXXX
        return len(clean_number) == 11 and clean_number[3:] != '00000000'
    elif len(clean_number) == 8:
        # Local format: XXXXXXXX
        return clean_number != '00000000'
    
    return False


def format_botswana_phone_number(phone_number):
    """
    Format phone number to Botswana international format.
    
    Args:
        phone_number (str): Phone number to format
        
    Returns:
        str: Formatted phone number (+267XXXXXXXX)
        
    Example:
        >>> format_botswana_phone_number('71234567')
        '+26771234567'
    """
    if not phone_number:
        return ''
    
    # Remove any non-digit characters
    clean_number = re.sub(r'[^\d]', '', phone_number)
    
    # Format to international format
    if clean_number.startswith('267') and len(clean_number) == 11:
        return f"+{clean_number}"
    elif len(clean_number) == 8:
        return f"+267{clean_number}"
    
    return phone_number


def validate_botswana_id_number(id_number):
    """
    Validate Botswana ID number format.
    
    Args:
        id_number (str): ID number to validate
        
    Returns:
        bool: True if valid format, False otherwise
        
    Valid formats:
        - XXXXXX/XX/XX (Omang format)
        - PXXXXXXXX (Passport format)
        - XXXXXXXXX (9-digit format)
    """
    if not id_number:
        return False
    
    # Remove spaces
    clean_id = id_number.replace(' ', '')
    
    # Check Omang format: XXXXXX/XX/XX
    if re.match(r'^\d{6}/\d{2}/\d{2}$', clean_id):
        return True
    
    # Check Passport format: P followed by digits
    if re.match(r'^P\d+$', clean_id):
        return len(clean_id) >= 8  # Passport numbers are at least 8 characters
    
    # Check 9-digit format
    if re.match(r'^\d{9}$', clean_id):
        return True
    
    return False


def calculate_age(birth_date):
    """
    Calculate age from birth date.
    
    Args:
        birth_date (datetime.date): Birth date
        
    Returns:
        int: Age in years
    """
    today = timezone.now().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


def get_file_extension(filename):
    """
    Get file extension from filename.
    
    Args:
        filename (str): Filename
        
    Returns:
        str: File extension (lowercase, without dot)
    """
    if not filename:
        return ''
    
    return filename.lower().split('.')[-1] if '.' in filename else ''


def format_file_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Formatted file size
        
    Example:
        >>> format_file_size(1024)
        '1.0 KB'
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def sanitize_filename(filename):
    """
    Sanitize filename by removing or replacing unsafe characters.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    return sanitized


def generate_unique_filename(filename, existing_files=None):
    """
    Generate a unique filename to avoid conflicts.
    
    Args:
        filename (str): Original filename
        existing_files (list): List of existing filenames to check against
        
    Returns:
        str: Unique filename
    """
    if not existing_files:
        existing_files = []
    
    # If filename doesn't exist, return as-is
    if filename not in existing_files:
        return filename
    
    # Split filename into name and extension
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    
    counter = 1
    while True:
        new_filename = f"{name}_{counter}.{ext}" if ext else f"{name}_{counter}"
        if new_filename not in existing_files:
            return new_filename
        counter += 1


def is_valid_email(email):
    """
    Simple email validation.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def truncate_text(text, max_length=100, suffix='...'):
    """
    Truncate text to specified length.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        suffix (str): Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def get_date_range(period):
    """
    Get date range for a given period.
    
    Args:
        period (str): Period ('today', 'week', 'month', 'year')
        
    Returns:
        tuple: (start_date, end_date)
    """
    today = timezone.now().date()
    
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = today.replace(day=1)
        # Get last day of month
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:
        raise ValueError(f"Invalid period: {period}")
    
    return start_date, end_date


def calculate_business_days(start_date, end_date):
    """
    Calculate business days between two dates.
    
    Args:
        start_date (datetime.date): Start date
        end_date (datetime.date): End date
        
    Returns:
        int: Number of business days
    """
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days

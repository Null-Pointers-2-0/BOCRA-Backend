"""
Utility functions for the complaints app.
"""
from django.utils import timezone


def generate_complaint_reference() -> str:
    """
    Generate a unique complaint reference number: CMP-YYYY-NNNNNN
    Checks the database for collisions and increments.
    """
    from .models import Complaint
    year = timezone.now().year
    prefix = f"CMP-{year}-"
    last = (
        Complaint.objects.filter(reference_number__startswith=prefix)
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

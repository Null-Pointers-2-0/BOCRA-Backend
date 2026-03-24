"""
Utility functions for the domains app.
"""
from django.utils import timezone


def generate_domain_reference() -> str:
    """
    Generate a unique domain application reference number: DOM-YYYY-NNNNNN
    """
    from .models import DomainApplication

    year = timezone.now().year
    prefix = f"DOM-{year}-"
    last = (
        DomainApplication.objects.filter(reference_number__startswith=prefix)
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

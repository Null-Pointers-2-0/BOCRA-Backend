"""
Celery tasks for the complaints app.

Tasks
─────
send_complaint_submitted_email  — confirm receipt to complainant
send_complaint_status_email     — notify complainant on any status change
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _frontend_url() -> str:
    return getattr(settings, "FRONTEND_URL", "http://localhost:3000")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_complaint_submitted_email(self, complaint_id: str):
    """
    Send a confirmation email to the complainant after submission.
    Works for both authenticated and anonymous complaints.
    """
    try:
        from .models import Complaint
        complaint = Complaint.objects.get(id=complaint_id)
    except Exception:
        logger.warning("send_complaint_submitted_email: complaint %s not found.", complaint_id)
        return

    tracking_url = f"{_frontend_url()}/complaints/track?ref={complaint.reference_number}"
    subject = f"Complaint Received — {complaint.reference_number}"
    body = (
        f"Dear {complaint.complainant_name},\n\n"
        f"We have received your complaint and it has been logged for review.\n\n"
        f"Reference Number: {complaint.reference_number}\n"
        f"Subject: {complaint.subject}\n"
        f"Category: {complaint.get_category_display()}\n"
        f"Against: {complaint.against_operator_name}\n"
        f"Priority: {complaint.get_priority_display()}\n"
        f"SLA Deadline: {complaint.sla_deadline.strftime('%d %B %Y') if complaint.sla_deadline else 'N/A'}\n\n"
        f"You can track the status of your complaint at any time using your reference number:\n"
        f"{tracking_url}\n\n"
        f"Our team will review your complaint and keep you updated on progress.\n\n"
        f"Regards,\nBOCRA Complaints Team"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[complaint.complainant_email],
            fail_silently=False,
        )
        logger.info(
            "Complaint submitted email sent to %s for %s.",
            complaint.complainant_email,
            complaint.reference_number,
        )
    except Exception as exc:
        logger.error(
            "Failed to send complaint submitted email for %s: %s",
            complaint.reference_number,
            exc,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_complaint_status_email(self, complaint_id: str, new_status: str):
    """
    Notify the complainant whenever their complaint status changes.
    """
    try:
        from .models import Complaint, ComplaintStatus
        complaint = Complaint.objects.get(id=complaint_id)
    except Exception:
        logger.warning("send_complaint_status_email: complaint %s not found.", complaint_id)
        return

    from .models import ComplaintStatus

    tracking_url = f"{_frontend_url()}/complaints/track?ref={complaint.reference_number}"

    status_messages = {
        ComplaintStatus.ASSIGNED: (
            f"Complaint Update — {complaint.reference_number}",
            f"Your complaint ({complaint.reference_number}) has been assigned to a "
            f"BOCRA case handler and will be investigated shortly.\n\n"
            f"Track progress: {tracking_url}",
        ),
        ComplaintStatus.INVESTIGATING: (
            f"Complaint Under Investigation — {complaint.reference_number}",
            f"Your complaint ({complaint.reference_number}) is now being actively "
            f"investigated by our team.\n\n"
            f"Track progress: {tracking_url}",
        ),
        ComplaintStatus.AWAITING_RESPONSE: (
            f"Complaint Update — {complaint.reference_number}",
            f"Your complaint ({complaint.reference_number}) is awaiting a response "
            f"from the operator. We will update you once we hear back.\n\n"
            f"Track progress: {tracking_url}",
        ),
        ComplaintStatus.RESOLVED: (
            f"Complaint Resolved — {complaint.reference_number}",
            f"Your complaint ({complaint.reference_number}) has been resolved.\n\n"
            f"Resolution:\n{complaint.resolution}\n\n"
            f"If you are not satisfied with the resolution, you may request the case "
            f"be reopened by contacting us.\n\n"
            f"Details: {tracking_url}",
        ),
        ComplaintStatus.CLOSED: (
            f"Complaint Closed — {complaint.reference_number}",
            f"Your complaint ({complaint.reference_number}) has been formally closed.\n\n"
            f"Thank you for bringing this matter to our attention.\n\n"
            f"Details: {tracking_url}",
        ),
        ComplaintStatus.REOPENED: (
            f"Complaint Reopened — {complaint.reference_number}",
            f"Your complaint ({complaint.reference_number}) has been reopened for "
            f"further investigation.\n\n"
            f"Track progress: {tracking_url}",
        ),
    }

    subject, body_extra = status_messages.get(
        new_status,
        (
            f"Complaint Update — {complaint.reference_number}",
            f"Your complaint status has been updated to: {complaint.get_status_display()}.\n\n"
            f"Track progress: {tracking_url}",
        ),
    )

    body = (
        f"Dear {complaint.complainant_name},\n\n"
        f"{body_extra}\n\n"
        f"Regards,\nBOCRA Complaints Team"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[complaint.complainant_email],
            fail_silently=False,
        )
        logger.info(
            "Complaint status email sent to %s for %s (status: %s).",
            complaint.complainant_email,
            complaint.reference_number,
            new_status,
        )
    except Exception as exc:
        logger.error(
            "Failed to send complaint status email for %s: %s",
            complaint.reference_number,
            exc,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

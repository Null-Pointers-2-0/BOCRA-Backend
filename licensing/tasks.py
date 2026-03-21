"""
Celery tasks for the licensing app.

Tasks
─────
send_application_submitted_email  — notify applicant on submission
send_application_status_email     — notify applicant on any status change
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _frontend_url() -> str:
    return getattr(settings, "FRONTEND_URL", "http://localhost:3000")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_application_submitted_email(self, application_id: str):
    """
    Send a confirmation email to the applicant after they submit an application.
    """
    try:
        from .models import Application
        application = Application.objects.select_related(
            "applicant", "licence_type"
        ).get(id=application_id)
    except Exception as exc:
        logger.warning("send_application_submitted_email: application %s not found.", application_id)
        return

    applicant = application.applicant
    tracking_url = (
        f"{_frontend_url()}/licensing/applications/{application.id}"
    )
    subject = f"Application Received — {application.reference_number}"
    body = (
        f"Dear {applicant.first_name or applicant.username},\n\n"
        f"We have received your application for a {application.licence_type.name} licence.\n\n"
        f"Reference Number: {application.reference_number}\n"
        f"Organisation: {application.organisation_name}\n"
        f"Status: {application.get_status_display()}\n\n"
        f"You can track your application at:\n{tracking_url}\n\n"
        f"Our team will review your application and update you on any changes.\n\n"
        f"Regards,\nBOCRA Licensing Team"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[applicant.email],
            fail_silently=False,
        )
        logger.info(
            "Application submitted email sent to %s for %s.",
            applicant.email,
            application.reference_number,
        )
    except Exception as exc:
        logger.error(
            "Failed to send application submitted email for %s: %s",
            application.reference_number,
            exc,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_application_status_email(self, application_id: str, new_status: str):
    """
    Notify the applicant whenever their application status changes.
    Includes tailored messaging per status.
    """
    try:
        from .models import Application, ApplicationStatus
        application = Application.objects.select_related(
            "applicant", "licence_type"
        ).get(id=application_id)
    except Exception:
        logger.warning("send_application_status_email: application %s not found.", application_id)
        return

    from .models import ApplicationStatus

    applicant = application.applicant
    tracking_url = f"{_frontend_url()}/licensing/applications/{application.id}"

    # ── Status-specific subject and body ──────────────────────────────────────
    status_messages = {
        ApplicationStatus.UNDER_REVIEW: (
            f"Application Under Review — {application.reference_number}",
            (
                f"Your application ({application.reference_number}) for a "
                f"{application.licence_type.name} licence is now under review by our team.\n\n"
                f"We will notify you of any updates."
            ),
        ),
        ApplicationStatus.INFO_REQUESTED: (
            f"Additional Information Required — {application.reference_number}",
            (
                f"We require additional information to process your application "
                f"({application.reference_number}).\n\n"
                f"Message from BOCRA:\n{application.info_request_message}\n\n"
                f"Please log in and upload the requested documents:\n{tracking_url}"
            ),
        ),
        ApplicationStatus.APPROVED: (
            f"Licence Application Approved — {application.reference_number}",
            (
                f"Congratulations! Your application ({application.reference_number}) for a "
                f"{application.licence_type.name} licence has been APPROVED.\n\n"
                f"Your licence has been issued. You can download your certificate at:\n{tracking_url}\n\n"
                f"Thank you for registering with BOCRA."
            ),
        ),
        ApplicationStatus.REJECTED: (
            f"Licence Application Rejected — {application.reference_number}",
            (
                f"We regret to inform you that your application ({application.reference_number}) "
                f"for a {application.licence_type.name} licence has been rejected.\n\n"
                f"Reason: {application.decision_reason or 'Not specified.'}\n\n"
                f"If you believe this decision is incorrect, you may contact BOCRA at "
                f"licensing@bocra.org.bw.\n\nRegards,\nBOCRA Licensing Team"
            ),
        ),
        ApplicationStatus.CANCELLED: (
            f"Application Cancelled — {application.reference_number}",
            (
                f"Your application ({application.reference_number}) has been cancelled.\n\n"
                f"If this was not intentional, please submit a new application at:\n"
                f"{_frontend_url()}/licensing"
            ),
        ),
    }

    subject, body = status_messages.get(
        new_status,
        (
            f"Application Status Update — {application.reference_number}",
            (
                f"The status of your application ({application.reference_number}) has been "
                f"updated to: {application.get_status_display()}.\n\n"
                f"Track your application: {tracking_url}"
            ),
        ),
    )

    body += f"\n\nRegards,\nBOCRA Licensing Team\nlicensing@bocra.org.bw"

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[applicant.email],
            fail_silently=False,
        )
        logger.info(
            "Status email (%s) sent to %s for %s.",
            new_status,
            applicant.email,
            application.reference_number,
        )
    except Exception as exc:
        logger.error(
            "Failed to send status email for %s: %s",
            application.reference_number,
            exc,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

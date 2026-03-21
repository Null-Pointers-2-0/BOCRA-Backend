"""
Celery tasks for the accounts app.
All tasks use exponential backoff retry with a max of 3 attempts.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

User = get_user_model()


def _get_frontend_url() -> str:
    return getattr(settings, "FRONTEND_URL", "http://localhost:3000")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_id: str, token: str):
    """
    Send an email verification link to the user.
    Link format: {FRONTEND_URL}/verify-email?token={token}
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning("send_verification_email: user %s not found.", user_id)
        return

    verify_url = f"{_get_frontend_url()}/verify-email?token={token}"
    subject = "Verify your BOCRA account email"

    try:
        html_body = render_to_string(
            "accounts/email/verify_email.html",
            {"user": user, "verify_url": verify_url, "expiry_hours": 24},
        )
    except Exception:
        html_body = (
            f"Hi {user.first_name or user.username},\n\n"
            f"Please verify your email by clicking the link below:\n{verify_url}\n\n"
            f"This link expires in 24 hours."
        )

    try:
        send_mail(
            subject=subject,
            message=f"Verify your email: {verify_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body if "<html" in html_body else None,
            fail_silently=False,
        )
        logger.info("Verification email sent to %s.", user.email)
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", user.email, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id: str, uid: str, token: str):
    """
    Send a password reset link to the user.
    Link format: {FRONTEND_URL}/password-reset/confirm?uid={uid}&token={token}
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning("send_password_reset_email: user %s not found.", user_id)
        return

    reset_url = f"{_get_frontend_url()}/password-reset/confirm?uid={uid}&token={token}"
    subject = "Reset your BOCRA account password"

    try:
        html_body = render_to_string(
            "accounts/email/reset_password.html",
            {"user": user, "reset_url": reset_url},
        )
    except Exception:
        html_body = (
            f"Hi {user.first_name or user.username},\n\n"
            f"Click the link below to reset your password:\n{reset_url}\n\n"
            f"If you did not request this, please ignore this email."
        )

    try:
        send_mail(
            subject=subject,
            message=f"Reset your password: {reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body if "<html" in html_body else None,
            fail_silently=False,
        )
        logger.info("Password reset email sent to %s.", user.email)
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", user.email, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_id: str):
    """
    Send a welcome email after the user verifies their email address.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    if not user.email_verified:
        return

    subject = "Welcome to BOCRA Digital Platform"

    try:
        html_body = render_to_string(
            "accounts/email/welcome.html",
            {"user": user, "login_url": f"{_get_frontend_url()}/login"},
        )
    except Exception:
        html_body = (
            f"Hi {user.first_name or user.username},\n\n"
            f"Your email has been verified. Welcome to the BOCRA Digital Platform.\n\n"
            f"Log in at: {_get_frontend_url()}/login"
        )

    try:
        send_mail(
            subject=subject,
            message=f"Welcome to BOCRA! Log in at: {_get_frontend_url()}/login",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body if "<html" in html_body else None,
            fail_silently=False,
        )
        logger.info("Welcome email sent to %s.", user.email)
    except Exception as exc:
        logger.error("Failed to send welcome email to %s: %s", user.email, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_account_locked_email(self, user_id: str):
    """
    Notify a user that their account has been locked due to failed login attempts.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    subject = "BOCRA account temporarily locked"
    unlock_time = user.locked_until.strftime("%Y-%m-%d %H:%M UTC") if user.locked_until else "24 hours"

    try:
        html_body = render_to_string(
            "accounts/email/account_locked.html",
            {"user": user, "unlock_time": unlock_time},
        )
    except Exception:
        html_body = (
            f"Hi {user.first_name or user.username},\n\n"
            f"Your account has been temporarily locked due to too many failed login attempts.\n"
            f"Access will be restored at: {unlock_time}.\n\n"
            f"If this wasn't you, please contact BOCRA support immediately."
        )

    try:
        send_mail(
            subject=subject,
            message=f"Your account is locked until {unlock_time}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body if "<html" in html_body else None,
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

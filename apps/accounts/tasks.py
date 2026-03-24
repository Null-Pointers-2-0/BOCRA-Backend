"""
Celery tasks for the accounts app.
Handles asynchronous email sending and user management tasks.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id, token):
    """
    Send email verification link to user.
    
    This task runs asynchronously to avoid blocking the main application
    during email sending. Implements retry logic for reliability.
    
    Args:
        user_id: UUID of the user
        token: JWT token for verification
        
    Raises:
        Retry: If email sending fails (will retry up to 3 times)
    """
    try:
        user = User.objects.get(id=user_id)
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        # Render HTML email template
        html_message = render_to_string('accounts/email/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
            'expiry_hours': 24,
        })
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject='Verify Your BOCRA Account',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to user {user.email}")
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for verification email")
        # Don't retry if user doesn't exist
        pass
        
    except Exception as exc:
        logger.error(f"Failed to send verification email to user {user_id}: {exc}")
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, uid, token):
    """
    Send password reset link to user.
    
    This task handles password reset email delivery asynchronously.
    Includes security measures and proper logging.
    
    Args:
        user_id: UUID of the user
        uid: Base64 encoded user ID
        token: Password reset token
        
    Raises:
        Retry: If email sending fails (will retry up to 3 times)
    """
    try:
        user = User.objects.get(id=user_id)
        
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        
        # Render HTML email template
        html_message = render_to_string('accounts/email/reset_password.html', {
            'user': user,
            'reset_url': reset_url,
            'expiry_hours': 24,
        })
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject='Reset Your BOCRA Password',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to user {user.email}")
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for password reset email")
        # Don't retry if user doesn't exist
        pass
        
    except Exception as exc:
        logger.error(f"Failed to send password reset email to user {user_id}: {exc}")
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id):
    """
    Send welcome email to newly verified users.
    
    This task sends a welcome email after a user successfully
    verifies their email address.
    
    Args:
        user_id: UUID of the user
        
    Raises:
        Retry: If email sending fails (will retry up to 3 times)
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Only send welcome email to verified users
        if not user.email_verified:
            logger.warning(f"User {user.email} is not verified, skipping welcome email")
            return
        
        # Render HTML email template
        html_message = render_to_string('accounts/email/welcome.html', {
            'user': user,
            'login_url': f"{settings.FRONTEND_URL}/login",
        })
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject='Welcome to BOCRA Digital Platform',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Welcome email sent to user {user.email}")
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for welcome email")
        pass
        
    except Exception as exc:
        logger.error(f"Failed to send welcome email to user {user_id}: {exc}")
        countdown = 60 * (2 ** self.request.retries)
        self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def send_account_locked_email(self, user_id):
    """
    Send email notification when account is locked.
    
    This task notifies users when their account has been locked
    due to multiple failed login attempts.
    
    Args:
        user_id: UUID of the user
        
    Raises:
        Retry: If email sending fails (will retry up to 3 times)
    """
    try:
        user = User.objects.get(id=user_id)
        
        if not user.is_locked:
            logger.warning(f"User {user.email} is not locked, skipping locked notification")
            return
        
        # Render HTML email template
        html_message = render_to_string('accounts/email/account_locked.html', {
            'user': user,
            'unlock_url': f"{settings.FRONTEND_URL}/unlock-account",
            'support_email': settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else 'support@bocra.bw',
        })
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject='Your BOCRA Account Has Been Locked',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Account locked notification sent to user {user.email}")
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for account locked email")
        pass
        
    except Exception as exc:
        logger.error(f"Failed to send account locked email to user {user_id}: {exc}")
        countdown = 60 * (2 ** self.request.retries)
        self.retry(exc=exc, countdown=countdown)


@shared_task
def cleanup_unverified_users():
    """
    Delete user accounts that haven't been verified after 7 days.
    
    This scheduled task runs daily to clean up unverified accounts
    and maintain database hygiene.
    
    Returns:
        str: Summary of cleanup operation
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=7)
    
    with transaction.atomic():
        unverified_users = User.objects.filter(
            email_verified=False,
            created_at__lt=cutoff_date,
            role='CITIZEN',
            is_active=True
        )
        
        count = unverified_users.count()
        
        if count > 0:
            # Soft delete the users
            unverified_users.update(is_active=False)
            
            logger.info(f"Soft deleted {count} unverified users older than 7 days")
            return f"Soft deleted {count} unverified users older than 7 days"
        
        return "No unverified users to clean up"


@shared_task
def cleanup_expired_sessions():
    """
    Clean up expired user sessions and unlock accounts.
    
    This task runs hourly to:
    - Unlock accounts whose lock period has expired
    - Clean up expired sessions
    - Update user statistics
    
    Returns:
        str: Summary of cleanup operation
    """
    now = timezone.now()
    
    with transaction.atomic():
        # Unlock expired locked accounts
        locked_accounts = User.objects.filter(
            locked_until__lt=now,
            is_active=True
        )
        
        unlocked_count = locked_accounts.count()
        if unlocked_count > 0:
            locked_accounts.update(
                locked_until=None,
                failed_login_attempts=0
            )
            logger.info(f"Unlocked {unlocked_count} accounts")
        
        # Clean up expired sessions (if using Django sessions)
        try:
            from django.contrib.sessions.models import Session
            expired_sessions = Session.objects.filter(
                expire_date__lt=now
            )
            session_count = expired_sessions.count()
            if session_count > 0:
                expired_sessions.delete()
                logger.info(f"Cleaned up {session_count} expired sessions")
        except ImportError:
            logger.warning("Django sessions not available")
        
        return f"Unlocked {unlocked_count} accounts and cleaned up expired sessions"


@shared_task
def generate_user_statistics():
    """
    Generate daily user statistics for reporting.
    
    This task runs daily to collect and store user statistics
    for analytics and reporting purposes.
    
    Returns:
        dict: User statistics summary
    """
    from apps.analytics.models import UserStatistics
    
    try:
        # Get current statistics
        stats = User.objects.get_user_statistics()
        
        # Store statistics for historical tracking
        UserStatistics.objects.create(
            date=timezone.now().date(),
            total_users=stats['total_users'],
            citizens=stats['citizens'],
            staff=stats['staff'],
            admins=stats['admins'],
            verified=stats['verified'],
            unverified=stats['unverified'],
            locked=stats['locked'],
            verification_rate=stats['verification_rate'],
        )
        
        logger.info(f"Generated user statistics: {stats}")
        return stats
        
    except Exception as exc:
        logger.error(f"Failed to generate user statistics: {exc}")
        return {}


@shared_task(bind=True, max_retries=3)
def send_bulk_notification_email(self, subject, message, user_ids):
    """
    Send bulk notification emails to specified users.
    
    This task handles bulk email sending for system notifications,
    announcements, or marketing communications.
    
    Args:
        subject: Email subject
        message: Email message content
        user_ids: List of user IDs to send to
        
    Returns:
        dict: Email sending statistics
    """
    try:
        users = User.objects.filter(
            id__in=user_ids,
            is_active=True,
            email_verified=True
        )
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                success_count += 1
                
            except Exception as exc:
                error_count += 1
                logger.error(f"Failed to send bulk email to {user.email}: {exc}")
        
        result = {
            'total_users': users.count(),
            'success_count': success_count,
            'error_count': error_count,
        }
        
        logger.info(f"Bulk email sent: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to send bulk notification: {exc}")
        countdown = 60 * (2 ** self.request.retries)
        self.retry(exc=exc, countdown=countdown)


@shared_task
def sync_user_profiles():
    """
    Synchronize user profiles with external systems.
    
    This task can be used to sync user data with external
    authentication systems or directories.
    
    Returns:
        str: Sync operation summary
    """
    # Placeholder for external system synchronization
    # This could integrate with:
    # - Active Directory/LDAP
    # - External authentication providers
    # - Government identity systems
    
    logger.info("User profile synchronization completed")
    return "User profile synchronization completed"


@shared_task
def audit_user_activity():
    """
    Perform user activity audit for security monitoring.
    
    This task runs periodically to:
    - Detect suspicious login patterns
    - Monitor failed login attempts
    - Generate security alerts
    
    Returns:
        dict: Audit results
    """
    audit_results = {
        'suspicious_logins': 0,
        'high_failed_attempts': 0,
        'security_alerts': 0,
    }
    
    # Check for users with high failed login attempts
    high_failed_users = User.objects.filter(
        failed_login_attempts__gte=10,
        is_active=True
    )
    
    audit_results['high_failed_attempts'] = high_failed_users.count()
    
    if high_failed_users.exists():
        logger.warning(f"Found {high_failed_users.count()} users with high failed login attempts")
        audit_results['security_alerts'] += high_failed_users.count()
    
    # Check for accounts locked in the last 24 hours
    recent_locks = User.objects.filter(
        locked_until__gte=timezone.now() - timezone.timedelta(hours=24)
    )
    
    audit_results['suspicious_logins'] = recent_locks.count()
    
    logger.info(f"User activity audit completed: {audit_results}")
    return audit_results

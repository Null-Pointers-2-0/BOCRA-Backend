"""
Alerts app models.

Entities
--------
AlertCategory       -- Categories of alerts citizens can subscribe to.
AlertSubscription   -- A subscriber's subscription to alert categories.
AlertLog            -- Audit trail of sent alerts.
"""
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


# -- ENUMS ---------------------------------------------------------------------

class AlertStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT    = "SENT",    "Sent"
    FAILED  = "FAILED",  "Failed"


# -- ALERT CATEGORY ------------------------------------------------------------

class AlertCategory(BaseModel):
    """
    Categories of alerts citizens can subscribe to.
    E.g. NEW_REGULATION, NEW_TENDER, LICENCE_EXPIRY, etc.
    """

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Icon identifier for frontend (e.g. 'bell', 'shield').",
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Visible to anonymous subscribers.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this category accepts new subscriptions.",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display ordering (lower = first).",
    )

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Alert Category"
        verbose_name_plural = "Alert Categories"

    def __str__(self):
        return f"{self.name} ({self.code})"


# -- ALERT SUBSCRIPTION --------------------------------------------------------

def _generate_token():
    """Generate a secure random 64-character hex token."""
    return secrets.token_hex(32)


class AlertSubscription(BaseModel):
    """
    A subscriber's subscription to one or more alert categories.
    One record per email address. Categories linked via M2M.
    Requires double opt-in (email confirmation) before alerts are sent.
    """

    email = models.EmailField(db_index=True, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_subscriptions",
        help_text="Linked user account (if registered).",
    )
    categories = models.ManyToManyField(
        AlertCategory,
        related_name="subscriptions",
        blank=True,
    )
    is_confirmed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Email confirmed via double opt-in.",
    )
    confirm_token = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_token,
        help_text="Token for email confirmation link.",
    )
    unsubscribe_token = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_token,
        help_text="Token for one-click unsubscribe link.",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    operator_filter = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Optional operator code filter (e.g. MASCOM, ORANGE, BTCL).",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Master on/off switch for this subscription.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alert Subscription"
        verbose_name_plural = "Alert Subscriptions"

    def __str__(self):
        status = "confirmed" if self.is_confirmed else "unconfirmed"
        return f"{self.email} ({status})"

    @property
    def is_token_expired(self):
        """Confirmation tokens expire after 72 hours."""
        if self.is_confirmed:
            return False
        expiry = self.created_at + timezone.timedelta(hours=72)
        return timezone.now() > expiry


# -- ALERT LOG -----------------------------------------------------------------

class AlertLog(BaseModel):
    """
    Audit trail of sent alerts. Every email dispatched is logged here.
    """

    subscription = models.ForeignKey(
        AlertSubscription,
        on_delete=models.CASCADE,
        related_name="alert_logs",
    )
    category = models.ForeignKey(
        AlertCategory,
        on_delete=models.CASCADE,
        related_name="alert_logs",
    )
    subject = models.CharField(max_length=300)
    body_preview = models.TextField(
        max_length=500,
        blank=True,
        default="",
        help_text="First 500 characters of the email body.",
    )
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Type of triggering object (e.g. 'publication', 'tender').",
    )
    related_object_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of the triggering object.",
    )
    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.PENDING,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error details if delivery failed.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alert Log"
        verbose_name_plural = "Alert Logs"
        indexes = [
            models.Index(fields=["category", "-created_at"]),
            models.Index(fields=["subscription", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.subject} -> {self.subscription.email} ({self.status})"

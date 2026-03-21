"""
Notifications app models.

Entities
────────
Notification   — An in-app notification delivered to a user.
"""
import uuid

from django.conf import settings
from django.db import models


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class NotificationType(models.TextChoices):
    IN_APP = "IN_APP", "In-App"
    EMAIL  = "EMAIL",  "Email"
    SMS    = "SMS",    "SMS"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT    = "SENT",    "Sent"
    READ    = "READ",    "Read"
    FAILED  = "FAILED",  "Failed"


# ─── NOTIFICATION ─────────────────────────────────────────────────────────────

class Notification(models.Model):
    """An in-app notification sent to a specific user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        default=NotificationType.IN_APP,
        db_index=True,
    )
    title = models.CharField(max_length=300)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=NotificationStatus.choices,
        default=NotificationStatus.SENT,
        db_index=True,
    )
    # Generic relation to any object in the system
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of related object (e.g. 'complaint', 'licence', 'publication').",
    )
    related_object_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of the related object.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} → {self.recipient}"

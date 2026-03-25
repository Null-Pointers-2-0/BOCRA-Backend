"""
QoE Reporter app models.

Entities
--------
QoEReport   -- A citizen network experience report (crowdsourced QoE data).
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import BaseModel


# -- ENUMS ---------------------------------------------------------------------

class ServiceType(models.TextChoices):
    DATA  = "DATA",  "Mobile Data / Internet"
    VOICE = "VOICE", "Voice Calls"
    SMS   = "SMS",   "Text Messaging"
    FIXED = "FIXED", "Fixed Broadband"


class ConnectionType(models.TextChoices):
    TWO_G   = "2G", "2G"
    THREE_G = "3G", "3G"
    FOUR_G  = "4G", "4G"
    FIVE_G  = "5G", "5G"


# -- QOE REPORT ----------------------------------------------------------------

class QoEReport(BaseModel):
    """
    A single citizen network experience report.

    Submitted anonymously or by a logged-in user. Contains a star rating,
    optional speed test results, and location data.
    """

    operator = models.ForeignKey(
        "analytics.NetworkOperator",
        on_delete=models.CASCADE,
        related_name="qoe_reports",
    )
    service_type = models.CharField(
        max_length=10,
        choices=ServiceType.choices,
        default=ServiceType.DATA,
        db_index=True,
    )
    connection_type = models.CharField(
        max_length=5,
        choices=ConnectionType.choices,
        db_index=True,
        help_text="Network technology the user is connected to (3G, 4G, 5G).",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 = Very Poor, 5 = Excellent",
    )

    # Speed test results (optional -- filled when user runs in-browser speed test)
    download_speed = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Download speed in Mbps.",
    )
    upload_speed = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Upload speed in Mbps.",
    )
    latency_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Latency in milliseconds.",
    )

    # Location (coordinates rounded to 3dp for privacy)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    district = models.ForeignKey(
        "coverages.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qoe_reports",
        help_text="Resolved from coordinates or selected manually.",
    )

    # Free-text description
    description = models.TextField(
        blank=True,
        default="",
        max_length=1000,
        help_text="Optional description of the network experience.",
    )

    # Submitter info
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qoe_reports",
        help_text="Set automatically if user is authenticated.",
    )
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Spam / rate limiting
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="SHA-256 hash of submitter IP for rate limiting.",
    )

    # Staff moderation
    is_verified = models.BooleanField(
        default=False,
        help_text="Verified by BOCRA staff.",
    )
    is_flagged = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flagged as suspicious (auto or manual).",
    )

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "QoE Report"
        verbose_name_plural = "QoE Reports"
        indexes = [
            models.Index(fields=["operator", "submitted_at"]),
            models.Index(fields=["district", "submitted_at"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return (
            f"QoE #{str(self.id)[:8]} -- {self.get_connection_type_display()} "
            f"{self.operator_id} -- {self.rating}/5"
        )

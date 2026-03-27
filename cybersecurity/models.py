"""
Cybersecurity app models.

Entities
────────
AuditRequest  — A cybersecurity audit request (anonymous or authenticated).
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel
from core.utils import generate_reference_number


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class AuditType(models.TextChoices):
    VULNERABILITY_ASSESSMENT = "VULNERABILITY_ASSESSMENT", "Vulnerability Assessment"
    PENETRATION_TEST         = "PENETRATION_TEST",         "Penetration Test"
    COMPLIANCE_AUDIT         = "COMPLIANCE_AUDIT",         "Compliance Audit"
    INCIDENT_RESPONSE        = "INCIDENT_RESPONSE",        "Incident Response"
    GENERAL                  = "GENERAL",                  "General Inquiry"


class AuditRequestStatus(models.TextChoices):
    SUBMITTED    = "SUBMITTED",    "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    SCHEDULED    = "SCHEDULED",    "Scheduled"
    IN_PROGRESS  = "IN_PROGRESS",  "In Progress"
    COMPLETED    = "COMPLETED",    "Completed"
    REJECTED     = "REJECTED",     "Rejected"


# ─── AUDIT REQUEST ────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    """
    A cybersecurity audit request — may be submitted anonymously or by
    an authenticated user. Similar pattern to complaints.
    """

    # ── identifiers ──────────────────────────────────────────────────────────
    reference_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
    )

    # ── requester (nullable for anonymous) ────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_requests",
        help_text="Null for anonymous requests.",
    )
    requester_name = models.CharField(max_length=200)
    requester_email = models.EmailField()
    requester_phone = models.CharField(max_length=20, blank=True, default="")
    organization = models.CharField(max_length=255)

    # ── audit details ─────────────────────────────────────────────────────────
    audit_type = models.CharField(
        max_length=30,
        choices=AuditType.choices,
        db_index=True,
    )
    description = models.TextField(
        help_text="Description of the system/service to be audited and specific concerns.",
    )
    preferred_date = models.DateField(
        null=True,
        blank=True,
        help_text="Preferred start date for the audit.",
    )

    # ── status / workflow ─────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=AuditRequestStatus.choices,
        default=AuditRequestStatus.SUBMITTED,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_audits",
    )

    # ── resolution ────────────────────────────────────────────────────────────
    staff_notes = models.TextField(
        blank=True,
        default="",
        help_text="Internal notes from staff processing the request.",
    )
    resolution = models.TextField(
        blank=True,
        default="",
        help_text="Formal resolution or outcome.",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Request"
        verbose_name_plural = "Audit Requests"

    def __str__(self):
        return f"{self.reference_number} — {self.organization} ({self.get_audit_type_display()})"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = generate_reference_number("CYB")
        super().save(*args, **kwargs)

    # ── state machine ─────────────────────────────────────────────────────────

    VALID_TRANSITIONS = {
        AuditRequestStatus.SUBMITTED:    [AuditRequestStatus.UNDER_REVIEW, AuditRequestStatus.REJECTED],
        AuditRequestStatus.UNDER_REVIEW: [AuditRequestStatus.SCHEDULED, AuditRequestStatus.REJECTED],
        AuditRequestStatus.SCHEDULED:    [AuditRequestStatus.IN_PROGRESS, AuditRequestStatus.REJECTED],
        AuditRequestStatus.IN_PROGRESS:  [AuditRequestStatus.COMPLETED],
        AuditRequestStatus.COMPLETED:    [],
        AuditRequestStatus.REJECTED:     [],
    }

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_status(self, new_status: str):
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from {self.status} to {new_status}."
            )
        self.status = new_status
        if new_status == AuditRequestStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

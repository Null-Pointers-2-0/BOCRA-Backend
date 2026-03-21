"""
Complaints app models.

Entities
────────
Complaint            — A regulatory complaint (anonymous or authenticated).
ComplaintDocument     — Evidence files attached to a complaint.
CaseNote             — Internal staff notes on a complaint case.
ComplaintStatusLog    — Immutable audit trail of every status change.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class ComplaintCategory(models.TextChoices):
    SERVICE_QUALITY = "SERVICE_QUALITY", "Service Quality"
    BILLING         = "BILLING",         "Billing Dispute"
    COVERAGE        = "COVERAGE",        "Network Coverage"
    CONDUCT         = "CONDUCT",         "Operator Conduct"
    INTERNET        = "INTERNET",        "Internet Services"
    BROADCASTING    = "BROADCASTING",    "Broadcasting"
    POSTAL          = "POSTAL",          "Postal Services"
    OTHER           = "OTHER",           "Other"


class ComplaintStatus(models.TextChoices):
    SUBMITTED          = "SUBMITTED",          "Submitted"
    ASSIGNED           = "ASSIGNED",           "Assigned"
    INVESTIGATING      = "INVESTIGATING",      "Under Investigation"
    AWAITING_RESPONSE  = "AWAITING_RESPONSE",  "Awaiting Response"
    RESOLVED           = "RESOLVED",           "Resolved"
    CLOSED             = "CLOSED",             "Closed"
    REOPENED           = "REOPENED",           "Reopened"


class ComplaintPriority(models.TextChoices):
    LOW    = "LOW",    "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH   = "HIGH",   "High"
    URGENT = "URGENT", "Urgent"


# ─── SLA DEFAULTS ─────────────────────────────────────────────────────────────

SLA_DAYS_BY_PRIORITY = {
    ComplaintPriority.LOW:    30,
    ComplaintPriority.MEDIUM: 14,
    ComplaintPriority.HIGH:   7,
    ComplaintPriority.URGENT: 3,
}


# ─── COMPLAINT ────────────────────────────────────────────────────────────────

class Complaint(BaseModel):
    """
    A regulatory complaint — may be submitted anonymously (no login) or by
    an authenticated user. Follows a state machine similar to licensing
    applications.

    State machine:
        SUBMITTED → ASSIGNED → INVESTIGATING ↔ AWAITING_RESPONSE
                                              ↓
                                           RESOLVED → CLOSED
                                              ↑
                                           REOPENED ──→ INVESTIGATING
    """

    # ── identifiers ──────────────────────────────────────────────────────────
    reference_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
    )

    # ── complainant (nullable for anonymous) ──────────────────────────────────
    complainant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
        help_text="Null for anonymous complaints.",
    )
    complainant_name = models.CharField(
        max_length=200,
        help_text="Required for anonymous complaints.",
    )
    complainant_email = models.EmailField(
        help_text="Required — used for status notifications.",
    )
    complainant_phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    # ── target ────────────────────────────────────────────────────────────────
    against_licensee = models.ForeignKey(
        "licensing.Licence",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints_against",
        help_text="Link to an active licence, if identifiable.",
    )
    against_operator_name = models.CharField(
        max_length=255,
        help_text="Free-text operator name (always filled, even if licence linked).",
    )

    # ── complaint details ─────────────────────────────────────────────────────
    category = models.CharField(
        max_length=20,
        choices=ComplaintCategory.choices,
        db_index=True,
    )
    subject = models.CharField(max_length=300)
    description = models.TextField()

    # ── status / workflow ─────────────────────────────────────────────────────
    status = models.CharField(
        max_length=25,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.SUBMITTED,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=ComplaintPriority.choices,
        default=ComplaintPriority.MEDIUM,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )

    # ── resolution ────────────────────────────────────────────────────────────
    resolution = models.TextField(
        blank=True,
        default="",
        help_text="Formal resolution text — filled when case is resolved.",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    # ── SLA ───────────────────────────────────────────────────────────────────
    sla_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Auto-calculated from priority on submission.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Complaint"
        verbose_name_plural = "Complaints"

    def __str__(self):
        return f"{self.reference_number} — {self.subject[:50]} ({self.status})"

    # ── SLA helper ────────────────────────────────────────────────────────────

    @property
    def is_overdue(self) -> bool:
        if self.sla_deadline and self.status not in (
            ComplaintStatus.RESOLVED,
            ComplaintStatus.CLOSED,
        ):
            return timezone.now() > self.sla_deadline
        return False

    @property
    def days_until_sla(self):
        if self.sla_deadline:
            delta = self.sla_deadline - timezone.now()
            return delta.days
        return None

    # ── state machine ─────────────────────────────────────────────────────────

    VALID_TRANSITIONS = {
        ComplaintStatus.SUBMITTED:         [ComplaintStatus.ASSIGNED],
        ComplaintStatus.ASSIGNED:          [ComplaintStatus.INVESTIGATING],
        ComplaintStatus.INVESTIGATING:     [ComplaintStatus.AWAITING_RESPONSE, ComplaintStatus.RESOLVED],
        ComplaintStatus.AWAITING_RESPONSE: [ComplaintStatus.INVESTIGATING, ComplaintStatus.RESOLVED],
        ComplaintStatus.RESOLVED:          [ComplaintStatus.CLOSED, ComplaintStatus.REOPENED],
        ComplaintStatus.CLOSED:            [ComplaintStatus.REOPENED],
        ComplaintStatus.REOPENED:          [ComplaintStatus.INVESTIGATING],
    }

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_status(self, new_status: str, changed_by, reason: str = "") -> "ComplaintStatusLog":
        """
        Perform a validated status transition and record it in the audit log.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from {self.status} to {new_status}."
            )
        old_status = self.status
        self.status = new_status

        if new_status == ComplaintStatus.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()

        if new_status == ComplaintStatus.REOPENED:
            self.resolved_at = None

        self.save(update_fields=["status", "resolved_at", "updated_at"])

        log = ComplaintStatusLog.objects.create(
            complaint=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            reason=reason,
        )
        return log


# ─── COMPLAINT DOCUMENT ───────────────────────────────────────────────────────

class ComplaintDocument(BaseModel):
    """Evidence files attached to a complaint."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(max_length=255, help_text="Descriptive label for the evidence.")
    file = models.FileField(upload_to="complaints/documents/%Y/%m/")
    file_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0, help_text="Size in bytes.")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_complaint_docs",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Complaint Document"
        verbose_name_plural = "Complaint Documents"

    def __str__(self):
        return f"{self.name} — {self.complaint.reference_number}"


# ─── CASE NOTE ─────────────────────────────────────────────────────────────────

class CaseNote(BaseModel):
    """
    Internal notes on a complaint case.
    is_internal=True means only staff can see it.
    """

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="complaint_notes",
    )
    content = models.TextField()
    is_internal = models.BooleanField(
        default=True,
        help_text="Internal notes are visible to BOCRA staff only.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Case Note"
        verbose_name_plural = "Case Notes"

    def __str__(self):
        return f"Note on {self.complaint.reference_number} by {self.author}"


# ─── COMPLAINT STATUS LOG ─────────────────────────────────────────────────────

class ComplaintStatusLog(models.Model):
    """
    Immutable audit trail — every status change on a Complaint.
    Inherits from plain Model (not BaseModel) so it is never soft-deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    from_status = models.CharField(max_length=25, choices=ComplaintStatus.choices)
    to_status = models.CharField(max_length=25, choices=ComplaintStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="complaint_status_changes",
    )
    reason = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]
        verbose_name = "Complaint Status Log"
        verbose_name_plural = "Complaint Status Logs"

    def __str__(self):
        return f"{self.complaint.reference_number}: {self.from_status} → {self.to_status}"

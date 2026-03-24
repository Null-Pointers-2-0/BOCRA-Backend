"""
Licensing app models.

Entities
────────
LicenceSector        — Regulatory sector grouping (ICT, Postal, Broadcasting, etc.)
LicenceType          — The catalogue of licence types BOCRA offers.
Application          — A submitted (or drafted) licence application.
ApplicationDocument  — Files attached to an application.
ApplicationStatusLog — Immutable audit trail of every status change.
Licence              — The actual issued licence, created on approval.
"""
import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import AuditableModel, BaseModel


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class ApplicationStatus(models.TextChoices):
    DRAFT          = "DRAFT",           "Draft"
    SUBMITTED      = "SUBMITTED",       "Submitted"
    UNDER_REVIEW   = "UNDER_REVIEW",    "Under Review"
    INFO_REQUESTED = "INFO_REQUESTED",  "Additional Information Requested"
    APPROVED       = "APPROVED",        "Approved"
    REJECTED       = "REJECTED",        "Rejected"
    CANCELLED      = "CANCELLED",       "Cancelled"


class LicenceStatus(models.TextChoices):
    ACTIVE    = "ACTIVE",    "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    EXPIRED   = "EXPIRED",   "Expired"
    REVOKED   = "REVOKED",   "Revoked"


# ─── LICENCE SECTOR ───────────────────────────────────────────────────────────

class LicenceSector(AuditableModel):
    """
    Regulatory sector grouping for licence types.
    Examples: ICT, Postal, Broadcasting, General.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.TextField(
        help_text="Public-facing description of this regulatory sector.",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Optional icon identifier for the frontend.",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display ordering (lower = first).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active sectors appear on the public portal.",
        db_index=True,
    )

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Licence Sector"
        verbose_name_plural = "Licence Sectors"

    def __str__(self):
        return f"{self.name} ({self.code})"


# ─── LICENCE TYPE ─────────────────────────────────────────────────────────────

class LicenceType(AuditableModel):
    """
    The public catalogue of licence types BOCRA issues.

    Examples: Services & Applications Provider (SAP), Network Facilities
    Provider (NFP), Radio Dealer's Licence, VANS, etc.
    """

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    sector = models.ForeignKey(
        LicenceSector,
        on_delete=models.PROTECT,
        related_name="licence_types",
        null=True,
        blank=True,
        help_text="Regulatory sector this licence type belongs to.",
    )
    description = models.TextField(help_text="Shown to applicants on the public portal.")
    requirements = models.TextField(
        help_text="Documents and information the applicant must provide.",
        blank=True,
        default="",
    )
    eligibility_criteria = models.TextField(
        help_text="Who is eligible to apply for this licence type.",
        blank=True,
        default="",
    )
    required_documents = models.JSONField(
        default=list,
        blank=True,
        help_text='Structured list of required docs, e.g. [{"name": "Certificate of Incorporation", "required": true}].',
    )
    fee_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Initial application / licensing fee in BWP.",
    )
    annual_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Recurring annual fee in BWP.",
    )
    renewal_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Renewal fee in BWP (may differ from initial fee).",
    )
    fee_currency = models.CharField(max_length=3, default="BWP")
    validity_period_months = models.PositiveIntegerField(
        default=12,
        help_text="How long the issued licence is valid for (months).",
    )
    is_domain_applicable = models.BooleanField(
        default=False,
        help_text="If true, this licence is relevant when applying for .bw domains.",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display ordering within its sector (lower = first).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active types appear on the public portal.",
        db_index=True,
    )

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Licence Type"
        verbose_name_plural = "Licence Types"

    def __str__(self):
        return f"{self.name} ({self.code})"


# ─── APPLICATION ──────────────────────────────────────────────────────────────

class Application(BaseModel):
    """
    A licence application — may start as a DRAFT and progress through the
    status state machine until APPROVED or REJECTED.

    State machine:
        DRAFT → SUBMITTED → UNDER_REVIEW ↔ INFO_REQUESTED
                                         ↓
                                    APPROVED / REJECTED
        Any state → CANCELLED (by applicant, before UNDER_REVIEW)
    """

    # ── identifiers ──────────────────────────────────────────────────────────
    reference_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,  # auto-populated on pre_save
    )

    # ── relationships ─────────────────────────────────────────────────────────
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="licence_applications",
    )
    licence_type = models.ForeignKey(
        LicenceType,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    # Set if this is a renewal of an existing licence.
    renewal_of = models.ForeignKey(
        "Licence",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="renewal_applications",
    )

    # ── status ────────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    # ── applicant / organisation details ──────────────────────────────────────
    organisation_name = models.CharField(max_length=255)
    organisation_registration = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Company registration number (from CIPA).",
    )
    contact_person = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    description = models.TextField(
        help_text="Brief description of the business / purpose of application.",
    )

    # ── staff review ──────────────────────────────────────────────────────────
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_applications",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Internal staff notes — not visible to applicant.",
    )
    decision_date = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(
        blank=True,
        default="",
        help_text="Required when rejecting an application.",
    )

    # ── extra info request ───────────────────────────────────────────────────
    info_request_message = models.TextField(
        blank=True,
        default="",
        help_text="Message sent to applicant when requesting more information.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Application"
        verbose_name_plural = "Applications"

    def __str__(self):
        return f"{self.reference_number} — {self.licence_type.code} ({self.status})"

    # ── valid transitions ──────────────────────────────────────────────────────

    VALID_TRANSITIONS = {
        ApplicationStatus.DRAFT:          [ApplicationStatus.SUBMITTED, ApplicationStatus.CANCELLED],
        ApplicationStatus.SUBMITTED:      [ApplicationStatus.UNDER_REVIEW, ApplicationStatus.CANCELLED],
        ApplicationStatus.UNDER_REVIEW:   [ApplicationStatus.INFO_REQUESTED, ApplicationStatus.APPROVED, ApplicationStatus.REJECTED],
        ApplicationStatus.INFO_REQUESTED: [ApplicationStatus.UNDER_REVIEW, ApplicationStatus.CANCELLED],
        ApplicationStatus.APPROVED:       [],   # terminal
        ApplicationStatus.REJECTED:       [],   # terminal
        ApplicationStatus.CANCELLED:      [],   # terminal
    }

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_status(self, new_status: str, changed_by, reason: str = "") -> "ApplicationStatusLog":
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

        if new_status == ApplicationStatus.SUBMITTED and not self.submitted_at:
            self.submitted_at = timezone.now()
        if new_status in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED):
            self.decision_date = timezone.now()
            self.reviewed_by = changed_by

        self.save(update_fields=[
            "status", "submitted_at", "decision_date", "reviewed_by", "updated_at"
        ])

        log = ApplicationStatusLog.objects.create(
            application=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            reason=reason,
        )
        return log


# ─── APPLICATION DOCUMENT ─────────────────────────────────────────────────────

class ApplicationDocument(BaseModel):
    """Supporting documents attached to a licence application."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(max_length=255, help_text="Descriptive label for the document.")
    file = models.FileField(upload_to="licensing/documents/%Y/%m/")
    file_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0, help_text="Size in bytes.")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_application_docs",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Application Document"
        verbose_name_plural = "Application Documents"

    def __str__(self):
        return f"{self.name} — {self.application.reference_number}"


# ─── APPLICATION STATUS LOG ───────────────────────────────────────────────────

class ApplicationStatusLog(models.Model):
    """
    Immutable audit trail — every status change on an Application.
    Inherits from plain Model (not BaseModel) so it is never soft-deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    from_status = models.CharField(max_length=20, choices=ApplicationStatus.choices)
    to_status   = models.CharField(max_length=20, choices=ApplicationStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="application_status_changes",
    )
    reason = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]
        verbose_name = "Application Status Log"
        verbose_name_plural = "Application Status Logs"

    def __str__(self):
        return f"{self.application.reference_number}: {self.from_status} → {self.to_status}"


# ─── LICENCE ──────────────────────────────────────────────────────────────────

class Licence(BaseModel):
    """
    The actual issued licence — created automatically when an Application
    is transitioned to APPROVED.
    """

    licence_number = models.CharField(max_length=50, unique=True, db_index=True, blank=True)
    application = models.OneToOneField(
        Application,
        on_delete=models.PROTECT,
        related_name="licence",
    )
    licence_type = models.ForeignKey(
        LicenceType,
        on_delete=models.PROTECT,
        related_name="licences",
    )
    holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="licences",
    )
    organisation_name = models.CharField(max_length=255)
    issued_date = models.DateField(default=date.today)
    expiry_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=LicenceStatus.choices,
        default=LicenceStatus.ACTIVE,
        db_index=True,
    )
    certificate_file = models.FileField(
        upload_to="licensing/certificates/%Y/",
        null=True,
        blank=True,
    )
    conditions = models.TextField(
        blank=True,
        default="",
        help_text="Any specific conditions attached to this licence.",
    )

    class Meta:
        ordering = ["-issued_date"]
        verbose_name = "Licence"
        verbose_name_plural = "Licences"

    def __str__(self):
        return f"{self.licence_number} — {self.organisation_name} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> int:
        return (self.expiry_date - date.today()).days

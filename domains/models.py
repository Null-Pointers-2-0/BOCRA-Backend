"""
Domains app models.

Entities
────────
DomainZone                    — Catalogue of available .bw zones.
DomainApplication             — Request to register, renew, or transfer a domain.
DomainApplicationDocument     — Files attached to an application.
DomainApplicationStatusLog    — Immutable audit trail of status changes.
Domain                        — The registered domain record.
DomainEvent                   — Audit log for changes to active domains.
"""
import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import AuditableModel, BaseModel


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class DomainApplicationStatus(models.TextChoices):
    DRAFT          = "DRAFT",           "Draft"
    SUBMITTED      = "SUBMITTED",       "Submitted"
    UNDER_REVIEW   = "UNDER_REVIEW",    "Under Review"
    INFO_REQUESTED = "INFO_REQUESTED",  "Additional Information Requested"
    APPROVED       = "APPROVED",        "Approved"
    REJECTED       = "REJECTED",        "Rejected"
    CANCELLED      = "CANCELLED",       "Cancelled"


class DomainApplicationType(models.TextChoices):
    REGISTRATION = "REGISTRATION", "Registration"
    RENEWAL      = "RENEWAL",      "Renewal"
    TRANSFER     = "TRANSFER",     "Transfer"


class DomainStatus(models.TextChoices):
    ACTIVE         = "ACTIVE",         "Active"
    EXPIRED        = "EXPIRED",        "Expired"
    SUSPENDED      = "SUSPENDED",      "Suspended"
    PENDING_DELETE = "PENDING_DELETE",  "Pending Delete"
    DELETED        = "DELETED",        "Deleted"


class DomainEventType(models.TextChoices):
    REGISTERED     = "REGISTERED",      "Registered"
    RENEWED        = "RENEWED",         "Renewed"
    TRANSFERRED    = "TRANSFERRED",     "Transferred"
    NS_UPDATED     = "NS_UPDATED",      "Nameservers Updated"
    CONTACT_UPDATED = "CONTACT_UPDATED", "Contact Updated"
    SUSPENDED      = "SUSPENDED",       "Suspended"
    UNSUSPENDED    = "UNSUSPENDED",     "Unsuspended"
    EXPIRED        = "EXPIRED",         "Expired"
    DELETED        = "DELETED",         "Deleted"


# ─── DOMAIN ZONE ──────────────────────────────────────────────────────────────

class DomainZone(AuditableModel):
    """
    Catalogue of available .bw zones. Managed by staff.
    Examples: .co.bw, .org.bw, .ac.bw, .gov.bw, .net.bw, .bw
    """

    name = models.CharField(max_length=50, help_text="Zone name (e.g., .co.bw)")
    code = models.CharField(max_length=20, unique=True, db_index=True, help_text="Unique short code (e.g., CO_BW)")
    description = models.TextField(help_text="Shown to applicants — who this zone is for.")
    registration_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Registration fee in BWP.",
    )
    renewal_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Annual renewal fee in BWP.",
    )
    fee_currency = models.CharField(max_length=3, default="BWP")
    min_registration_years = models.PositiveIntegerField(default=1)
    max_registration_years = models.PositiveIntegerField(default=10)
    is_restricted = models.BooleanField(
        default=False,
        help_text="Requires special eligibility (e.g., .gov.bw).",
    )
    eligibility_criteria = models.TextField(
        blank=True,
        default="",
        help_text="Requirements for restricted zones.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Domain Zone"
        verbose_name_plural = "Domain Zones"

    def __str__(self):
        return f"{self.name} ({self.code})"


# ─── DOMAIN APPLICATION ───────────────────────────────────────────────────────

class DomainApplication(BaseModel):
    """
    A request to register, renew, or transfer a .bw domain.
    Follows the same state machine as licensing applications.

    State machine:
        DRAFT → SUBMITTED → UNDER_REVIEW ↔ INFO_REQUESTED
                                         ↓
                                    APPROVED / REJECTED
        Any state → CANCELLED (by applicant, before UNDER_REVIEW)
    """

    # ── identifiers ──────────────────────────────────────────────────────────
    reference_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        blank=True,
    )
    application_type = models.CharField(
        max_length=20,
        choices=DomainApplicationType.choices,
        default=DomainApplicationType.REGISTRATION,
    )

    # ── relationships ────────────────────────────────────────────────────────
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="domain_applications",
    )
    domain_name = models.CharField(
        max_length=253,
        help_text="Requested FQDN (e.g., mycompany.co.bw)",
    )
    zone = models.ForeignKey(
        DomainZone,
        on_delete=models.PROTECT,
        related_name="applications",
    )

    # ── status ───────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=DomainApplicationStatus.choices,
        default=DomainApplicationStatus.DRAFT,
        db_index=True,
    )
    registration_period_years = models.PositiveIntegerField(default=1)

    # ── organisation details ─────────────────────────────────────────────────
    organisation_name = models.CharField(max_length=300)
    organisation_registration_number = models.CharField(max_length=100, blank=True, default="")
    registrant_name = models.CharField(max_length=200)
    registrant_email = models.EmailField()
    registrant_phone = models.CharField(max_length=30, blank=True, default="")
    registrant_address = models.TextField(blank=True, default="")

    # ── technical details ────────────────────────────────────────────────────
    nameserver_1 = models.CharField(max_length=253, blank=True, default="")
    nameserver_2 = models.CharField(max_length=253, blank=True, default="")
    nameserver_3 = models.CharField(max_length=253, blank=True, default="")
    nameserver_4 = models.CharField(max_length=253, blank=True, default="")
    tech_contact_name = models.CharField(max_length=200, blank=True, default="")
    tech_contact_email = models.EmailField(blank=True, default="")

    # ── transfer-specific (nullable) ─────────────────────────────────────────
    transfer_from_registrant = models.CharField(max_length=200, blank=True, default="")
    transfer_auth_code = models.CharField(max_length=100, blank=True, default="")

    # ── review ───────────────────────────────────────────────────────────────
    justification = models.TextField(blank=True, default="", help_text="Why the applicant wants this domain.")
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_domain_applications",
    )
    decision_date = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True, default="")
    info_request_message = models.TextField(blank=True, default="")

    # ── audit ────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domain_applications_created",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domain_applications_modified",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Domain Application"
        verbose_name_plural = "Domain Applications"

    def __str__(self):
        return f"{self.reference_number} — {self.domain_name} ({self.status})"

    # ── valid transitions ────────────────────────────────────────────────────

    VALID_TRANSITIONS = {
        DomainApplicationStatus.DRAFT:          [DomainApplicationStatus.SUBMITTED, DomainApplicationStatus.CANCELLED],
        DomainApplicationStatus.SUBMITTED:      [DomainApplicationStatus.UNDER_REVIEW, DomainApplicationStatus.CANCELLED],
        DomainApplicationStatus.UNDER_REVIEW:   [DomainApplicationStatus.INFO_REQUESTED, DomainApplicationStatus.APPROVED, DomainApplicationStatus.REJECTED],
        DomainApplicationStatus.INFO_REQUESTED: [DomainApplicationStatus.UNDER_REVIEW, DomainApplicationStatus.CANCELLED],
        DomainApplicationStatus.APPROVED:       [],
        DomainApplicationStatus.REJECTED:       [],
        DomainApplicationStatus.CANCELLED:      [],
    }

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_status(self, new_status: str, changed_by, reason: str = "") -> "DomainApplicationStatusLog":
        """
        Perform a validated status transition and record it in the audit log.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}.")

        old_status = self.status
        self.status = new_status

        if new_status == DomainApplicationStatus.SUBMITTED and not self.submitted_at:
            self.submitted_at = timezone.now()
        if new_status in (DomainApplicationStatus.APPROVED, DomainApplicationStatus.REJECTED):
            self.decision_date = timezone.now()
            self.reviewed_by = changed_by

        self.save(update_fields=[
            "status", "submitted_at", "decision_date", "reviewed_by", "updated_at",
        ])

        return DomainApplicationStatusLog.objects.create(
            application=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            reason=reason,
        )


# ─── DOMAIN APPLICATION DOCUMENT ──────────────────────────────────────────────

class DomainApplicationDocument(BaseModel):
    """Supporting documents attached to a domain application."""

    application = models.ForeignKey(
        DomainApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(max_length=200, help_text="Document label.")
    file = models.FileField(upload_to="domains/documents/%Y/%m/")
    file_type = models.CharField(max_length=50, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0, help_text="Size in bytes.")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_domain_docs",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Domain Application Document"
        verbose_name_plural = "Domain Application Documents"

    def __str__(self):
        return f"{self.name} — {self.application.reference_number}"


# ─── DOMAIN APPLICATION STATUS LOG ────────────────────────────────────────────

class DomainApplicationStatusLog(models.Model):
    """
    Immutable audit trail — every status change on a domain application.
    Plain Model (not BaseModel) so it is never soft-deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        DomainApplication,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    from_status = models.CharField(max_length=20, choices=DomainApplicationStatus.choices)
    to_status = models.CharField(max_length=20, choices=DomainApplicationStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="domain_application_status_changes",
    )
    reason = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]
        verbose_name = "Domain Application Status Log"
        verbose_name_plural = "Domain Application Status Logs"

    def __str__(self):
        return f"{self.application.reference_number}: {self.from_status} → {self.to_status}"


# ─── DOMAIN ───────────────────────────────────────────────────────────────────

class Domain(BaseModel):
    """
    The actual registered domain. Created automatically when a DomainApplication
    is approved, or seeded from registry data.
    """

    domain_name = models.CharField(max_length=253, unique=True, db_index=True)
    zone = models.ForeignKey(
        DomainZone,
        on_delete=models.PROTECT,
        related_name="domains",
    )
    status = models.CharField(
        max_length=20,
        choices=DomainStatus.choices,
        default=DomainStatus.ACTIVE,
        db_index=True,
    )

    # ── registrant (owner) ───────────────────────────────────────────────────
    registrant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_domains",
        help_text="Current owner (null for seeded externals).",
    )
    registrant_name = models.CharField(max_length=200)
    registrant_email = models.EmailField()
    registrant_phone = models.CharField(max_length=30, blank=True, default="")
    registrant_address = models.TextField(blank=True, default="")
    organisation_name = models.CharField(max_length=300, blank=True, default="")

    # ── technical ────────────────────────────────────────────────────────────
    nameserver_1 = models.CharField(max_length=253, blank=True, default="")
    nameserver_2 = models.CharField(max_length=253, blank=True, default="")
    nameserver_3 = models.CharField(max_length=253, blank=True, default="")
    nameserver_4 = models.CharField(max_length=253, blank=True, default="")
    tech_contact_name = models.CharField(max_length=200, blank=True, default="")
    tech_contact_email = models.EmailField(blank=True, default="")

    # ── dates ────────────────────────────────────────────────────────────────
    registered_at = models.DateTimeField(help_text="Original registration date.")
    expires_at = models.DateTimeField(help_text="When the registration expires.")
    last_renewed_at = models.DateTimeField(null=True, blank=True)

    # ── provenance ───────────────────────────────────────────────────────────
    created_from_application = models.OneToOneField(
        DomainApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domain",
    )
    is_seeded = models.BooleanField(default=False, help_text="Imported/seeded data, not from a real application.")

    # ── audit ────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domains_created",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domains_modified",
    )

    class Meta:
        ordering = ["domain_name"]
        verbose_name = "Domain"
        verbose_name_plural = "Domains"

    def __str__(self):
        return f"{self.domain_name} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return self.expires_at < timezone.now()

    @property
    def days_until_expiry(self) -> int:
        return (self.expires_at - timezone.now()).days


# ─── DOMAIN EVENT ─────────────────────────────────────────────────────────────

class DomainEvent(models.Model):
    """
    Audit log for changes to active domains.
    Separate from application status logs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=20, choices=DomainEventType.choices)
    description = models.TextField(help_text="Human-readable change description.")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="domain_events",
    )
    metadata = models.JSONField(default=dict, blank=True, help_text="Structured before/after data.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Domain Event"
        verbose_name_plural = "Domain Events"

    def __str__(self):
        return f"{self.domain.domain_name}: {self.event_type} at {self.created_at}"

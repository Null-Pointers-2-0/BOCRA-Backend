"""
Tenders app models.

Entities
────────
Tender             — A procurement tender notice published by BOCRA.
TenderDocument     — Downloadable documents (RFP, ToR, etc.) attached to a tender.
TenderAddendum     — Clarifications or amendments published after the initial tender.
TenderAward        — Announcement of the tender award.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.models import AuditableModel, BaseModel


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class TenderCategory(models.TextChoices):
    IT_SERVICES    = "IT_SERVICES",    "IT Services"
    CONSULTING     = "CONSULTING",     "Consulting"
    CONSTRUCTION   = "CONSTRUCTION",   "Construction"
    EQUIPMENT      = "EQUIPMENT",      "Equipment"
    PROFESSIONAL   = "PROFESSIONAL",   "Professional Services"
    MAINTENANCE    = "MAINTENANCE",    "Maintenance"
    OTHER          = "OTHER",          "Other"


class TenderStatus(models.TextChoices):
    DRAFT        = "DRAFT",        "Draft"
    OPEN         = "OPEN",         "Open"
    CLOSING_SOON = "CLOSING_SOON", "Closing Soon"
    CLOSED       = "CLOSED",       "Closed"
    AWARDED      = "AWARDED",      "Awarded"
    CANCELLED    = "CANCELLED",    "Cancelled"


# ─── TENDER ───────────────────────────────────────────────────────────────────

class Tender(AuditableModel):
    """A procurement tender notice published by BOCRA."""

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True, blank=True)
    reference_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique tender reference number (e.g. BOCRA/TENDER/2026/001).",
    )
    description = models.TextField(
        help_text="Full tender description / scope of work.",
    )
    category = models.CharField(
        max_length=30,
        choices=TenderCategory.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=TenderStatus.choices,
        default=TenderStatus.DRAFT,
        db_index=True,
    )
    opening_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the tender opens for submissions.",
    )
    closing_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Deadline for tender submissions.",
    )
    budget_range = models.CharField(
        max_length=100,
        blank=True,
        help_text="Indicative budget range (e.g. 'BWP 500,000 – 1,000,000').",
    )
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["-closing_date", "-created_at"]

    def __str__(self):
        return f"{self.reference_number} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:300]
            slug = base
            n = 1
            while Tender.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """True if the closing date has passed and the tender isn't closed/awarded."""
        if self.closing_date and self.status in (TenderStatus.OPEN, TenderStatus.CLOSING_SOON):
            return timezone.now() > self.closing_date
        return False

    @property
    def days_until_closing(self):
        """Days remaining until closing. None if no closing_date or already closed."""
        if self.closing_date and self.status in (TenderStatus.OPEN, TenderStatus.CLOSING_SOON):
            delta = self.closing_date - timezone.now()
            return max(0, delta.days)
        return None


# ─── TENDER DOCUMENT ──────────────────────────────────────────────────────────

def tender_document_path(instance, filename):
    return f"tenders/documents/{instance.tender.reference_number}/{filename}"


class TenderDocument(BaseModel):
    """Downloadable file attached to a tender (RFP, Terms of Reference, etc.)."""

    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=tender_document_path)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.title} — {self.tender.reference_number}"


# ─── TENDER ADDENDUM ──────────────────────────────────────────────────────────

class TenderAddendum(BaseModel):
    """Clarification or amendment published after the initial tender."""

    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name="addenda",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "tender addenda"

    def __str__(self):
        return f"Addendum: {self.title} — {self.tender.reference_number}"


# ─── TENDER AWARD ─────────────────────────────────────────────────────────────

class TenderAward(BaseModel):
    """Announcement of the tender award decision."""

    tender = models.OneToOneField(
        Tender,
        on_delete=models.CASCADE,
        related_name="award",
    )
    awardee_name = models.CharField(max_length=300)
    award_date = models.DateField()
    award_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    summary = models.TextField(
        blank=True,
        help_text="Brief summary of the award decision.",
    )
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-award_date"]

    def __str__(self):
        return f"Awarded to {self.awardee_name} — {self.tender.reference_number}"


# ─── TENDER APPLICATION STATUS ────────────────────────────────────────────────

class TenderApplicationStatus(models.TextChoices):
    SUBMITTED  = "SUBMITTED",  "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    SHORTLISTED = "SHORTLISTED", "Shortlisted"
    REJECTED   = "REJECTED",   "Rejected"
    WITHDRAWN  = "WITHDRAWN",  "Withdrawn"


# ─── TENDER APPLICATION ───────────────────────────────────────────────────────

class TenderApplication(BaseModel):
    """An application / bid submitted by a user for a specific tender."""

    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tender_applications",
    )
    reference_number = models.CharField(max_length=50, unique=True, editable=False)
    company_name = models.CharField(max_length=300)
    company_registration = models.CharField(max_length=100, blank=True)
    contact_person = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30, blank=True)
    proposal_summary = models.TextField(
        help_text="Brief summary of your proposal / bid.",
    )
    status = models.CharField(
        max_length=20,
        choices=TenderApplicationStatus.choices,
        default=TenderApplicationStatus.SUBMITTED,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("tender", "applicant")]

    def __str__(self):
        return f"{self.reference_number} — {self.company_name}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            import uuid as _uuid
            short = _uuid.uuid4().hex[:8].upper()
            self.reference_number = f"TA-{short}"
        super().save(*args, **kwargs)

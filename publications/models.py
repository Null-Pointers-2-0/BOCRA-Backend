"""
Publications app models.

Entities
────────
Publication            — A regulatory document, policy paper, or report.
PublicationAttachment   — Additional files attached to a publication.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.models import AuditableModel, BaseModel


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class PublicationCategory(models.TextChoices):
    REGULATION       = "REGULATION",       "Regulation"
    POLICY           = "POLICY",           "Policy"
    REPORT           = "REPORT",           "Report"
    GUIDELINE        = "GUIDELINE",        "Guideline"
    CONSULTATION     = "CONSULTATION",     "Consultation Paper"
    ANNUAL_REPORT    = "ANNUAL_REPORT",    "Annual Report"
    STRATEGY         = "STRATEGY",         "Strategy Document"
    OTHER            = "OTHER",            "Other"


class PublicationStatus(models.TextChoices):
    DRAFT     = "DRAFT",     "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED  = "ARCHIVED",  "Archived"


# ─── PUBLICATION ──────────────────────────────────────────────────────────────

def publication_file_path(instance, filename):
    return f"publications/files/{instance.created_at.year if instance.created_at else 'new'}/{filename}"


class Publication(AuditableModel):
    """A regulatory document, policy paper, or report published by BOCRA."""

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True, blank=True)
    summary = models.TextField(
        blank=True,
        help_text="Brief description shown in listing views.",
    )
    category = models.CharField(
        max_length=30,
        choices=PublicationCategory.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
        db_index=True,
    )
    file = models.FileField(
        upload_to=publication_file_path,
        blank=True,
        help_text="Primary document file (PDF, DOCX, XLSX).",
    )
    published_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date shown to the public. Auto-set on first publish.",
    )
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Publication year for filtering. Auto-set from published_date.",
    )
    version = models.CharField(
        max_length=20,
        default="1.0",
        help_text="Document version string.",
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Pin this document to the homepage.",
    )
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-published_date", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:300]
            slug = base
            n = 1
            while Publication.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        if self.published_date and not self.year:
            self.year = self.published_date.year
        super().save(*args, **kwargs)


# ─── PUBLICATION ATTACHMENT ───────────────────────────────────────────────────

def attachment_file_path(instance, filename):
    return f"publications/attachments/{filename}"


class PublicationAttachment(BaseModel):
    """Additional file attached to a publication (annexure, addendum, etc.)."""

    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=attachment_file_path)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.title} — {self.publication.title}"

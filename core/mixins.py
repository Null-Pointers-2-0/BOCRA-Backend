import os

from django.db import models
from django.utils import timezone


class StatusMixin(models.Model):
    """
    Adds a lifecycle status field and helper methods.
    Attach to models that move through workflow states
    (applications, complaints, tenders, licences).
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        ARCHIVED = "ARCHIVED", "Archived"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )

    class Meta:
        abstract = True

    def is_draft(self):
        return self.status == self.Status.DRAFT

    def is_pending(self):
        return self.status == self.Status.PENDING

    def is_in_progress(self):
        return self.status == self.Status.IN_PROGRESS

    def is_completed(self):
        return self.status == self.Status.COMPLETED

    def is_rejected(self):
        return self.status == self.Status.REJECTED

    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    def is_archived(self):
        return self.status == self.Status.ARCHIVED

    def can_edit(self):
        """Records in DRAFT or PENDING can still be edited."""
        return self.status in (self.Status.DRAFT, self.Status.PENDING)

    def can_delete(self):
        """Only DRAFT or CANCELLED records may be deleted."""
        return self.status in (self.Status.DRAFT, self.Status.CANCELLED)


class FileUploadMixin(models.Model):
    """
    Adds a file field with validation and auto-populated metadata.
    Limits: 50 MB max, allowed extensions: pdf, doc, docx, jpg, jpeg, png.
    """

    ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    file = models.FileField(upload_to="uploads/%Y/%m/", null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    file_type = models.CharField(max_length=100, blank=True, default="")
    uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.file:
            ext = os.path.splitext(self.file.name)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                raise ValidationError(
                    f"File type not allowed. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
                )
            if self.file.size > self.MAX_FILE_SIZE_BYTES:
                raise ValidationError("File size must not exceed 50 MB.")

    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = os.path.basename(self.file.name)
            self.file_size = self.file.size
            self.file_type = os.path.splitext(self.file.name)[1].lower().lstrip(".")
            if not self.uploaded_at:
                self.uploaded_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        return os.path.splitext(self.file_name)[1].lower() if self.file_name else ""

    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else None

    @property
    def is_pdf(self):
        return self.file_extension == ".pdf"

    @property
    def is_image(self):
        return self.file_extension in {".jpg", ".jpeg", ".png"}


class NotesMixin(models.Model):
    """
    Adds public notes and internal-only notes fields.
    Notes are appended with timestamps — never overwritten.
    """

    notes = models.TextField(blank=True, default="")
    internal_notes = models.TextField(blank=True, default="")

    class Meta:
        abstract = True

    def add_note(self, note: str, internal: bool = False):
        """Append a timestamped note."""
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        entry = f"[{timestamp}] {note}"
        if internal:
            self.internal_notes = f"{self.internal_notes}\n{entry}".strip()
        else:
            self.notes = f"{self.notes}\n{entry}".strip()
        self.save(update_fields=["internal_notes" if internal else "notes", "updated_at"])

    def clear_notes(self, internal: bool = False):
        if internal:
            self.internal_notes = ""
            self.save(update_fields=["internal_notes", "updated_at"])
        else:
            self.notes = ""
            self.save(update_fields=["notes", "updated_at"])

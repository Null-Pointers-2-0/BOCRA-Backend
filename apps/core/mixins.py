"""
Utility mixins for common functionality across models and views.
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class StatusMixin(models.Model):
    """
    Mixin that adds status field with common status choices.
    
    Useful for models that need status tracking like applications,
    complaints, tenders, etc.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'
        ARCHIVED = 'ARCHIVED', 'Archived'
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Current status of this record"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['status']),
        ]

    def is_draft(self):
        """Check if status is draft."""
        return self.status == self.Status.DRAFT

    def is_pending(self):
        """Check if status is pending."""
        return self.status == self.Status.PENDING

    def is_in_progress(self):
        """Check if status is in progress."""
        return self.status == self.Status.IN_PROGRESS

    def is_completed(self):
        """Check if status is completed."""
        return self.status == self.Status.COMPLETED

    def is_rejected(self):
        """Check if status is rejected."""
        return self.status == self.Status.REJECTED

    def is_cancelled(self):
        """Check if status is cancelled."""
        return self.status == self.Status.CANCELLED

    def is_archived(self):
        """Check if status is archived."""
        return self.status == self.Status.ARCHIVED

    def can_edit(self):
        """
        Check if the record can be edited based on status.
        
        Returns:
            bool: True if record can be edited, False otherwise
        """
        return self.status in [self.Status.DRAFT, self.Status.PENDING]

    def can_delete(self):
        """
        Check if the record can be deleted based on status.
        
        Returns:
            bool: True if record can be deleted, False otherwise
        """
        return self.status in [self.Status.DRAFT, self.Status.CANCELLED]


class FileUploadMixin(models.Model):
    """
    Mixin for models that handle file uploads.
    
    Provides common file handling functionality with
    proper validation and organization.
    """
    file = models.FileField(
        upload_to='uploads/%Y/%m/',
        blank=True,
        null=True,
        help_text="Uploaded file"
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Original file name"
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    file_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="File MIME type"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the file was uploaded"
    )

    class Meta:
        abstract = True

    def clean(self):
        """
        Validate file upload.
        
        Raises:
            ValidationError: If file is invalid
        """
        if self.file:
            # Check file size (max 50MB)
            max_size = 50 * 1024 * 1024  # 50MB in bytes
            if self.file.size > max_size:
                raise ValidationError(
                    f'File size cannot exceed 50MB. Current size: {self.file.size / (1024*1024):.2f}MB'
                )
            
            # Check file extension (allowed types)
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = self.file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(
                    f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
                )

    def save(self, *args, **kwargs):
        """
        Override save to update file metadata.
        """
        if self.file and not self.file_name:
            self.file_name = self.file.name
            self.file_size = self.file.size
            self.file_type = self.file.content_type or 'application/octet-stream'
        
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        """Get file extension."""
        if self.file_name:
            return self.file_name.lower().split('.')[-1]
        return None

    @property
    def file_size_mb(self):
        """Get file size in megabytes."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

    @property
    def is_pdf(self):
        """Check if file is a PDF."""
        return self.file_extension == 'pdf'

    @property
    def is_image(self):
        """Check if file is an image."""
        return self.file_extension in ['jpg', 'jpeg', 'png']


class NotesMixin(models.Model):
    """
    Mixin for models that need notes/comments functionality.
    
    Provides a standardized way to add notes to various models.
    """
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or comments"
    )
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes not visible to public/users"
    )

    class Meta:
        abstract = True

    def add_note(self, note, internal=False):
        """
        Add a note to the existing notes.
        
        Args:
            note (str): Note to add
            internal (bool): Whether this is an internal note
        """
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if internal:
            self.internal_notes = f"{self.internal_notes}\n\n[{timestamp}] {note}".strip()
        else:
            self.notes = f"{self.notes}\n\n[{timestamp}] {note}".strip()
        
        self.save(update_fields=['notes', 'internal_notes'])

    def clear_notes(self, internal=False):
        """
        Clear notes.
        
        Args:
            internal (bool): Whether to clear internal notes
        """
        if internal:
            self.internal_notes = ''
        else:
            self.notes = ''
        
        self.save(update_fields=['notes', 'internal_notes'])

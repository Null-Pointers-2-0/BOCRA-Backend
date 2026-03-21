import uuid

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base for all BOCRA models.
    Provides UUID PK, timestamps, and soft-delete support.
    Every app model should inherit from this unless there is a specific reason not to.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark record as deleted without removing from the database."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self):
        """Undo a soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def hard_delete(self):
        """Permanently remove from database. Use with caution."""
        super().delete()


class TimeStampedModel(models.Model):
    """
    Lightweight abstract base — timestamps only, sequential PK.
    Use for append-only or log-style models that don't need soft-delete.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditableModel(BaseModel):
    """
    Extends BaseModel with created_by / modified_by tracking.
    Use for any model where BOCRA staff actions need an audit trail
    (licence types, applications, publications, tenders, etc.).

    Set instance._current_user before save() to auto-populate these fields.
    """

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    modified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_modified",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        current_user = getattr(self, "_current_user", None)
        if current_user:
            if not self.pk:
                self.created_by = current_user
            self.modified_by = current_user
        super().save(*args, **kwargs)

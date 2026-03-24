"""
Core base models for the BOCRA Digital Platform.
All models inherit from BaseModel for consistent behavior.
"""
import uuid
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.
    
    Provides:
    - UUID primary key (better for distributed systems)
    - Created timestamp (auto-set on creation)
    - Updated timestamp (auto-updated on save)
    - Soft delete capability (is_active flag)
    
    Using UUIDs instead of sequential integers provides:
    - Better security (no ID enumeration attacks)
    - Better performance in distributed systems
    - No collisions when merging data from different sources
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Soft delete flag - False means deleted"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['is_active']),
        ]

    def soft_delete(self):
        """
        Mark the record as deleted without removing from database.
        
        Soft deletion preserves data for audit trails and allows
        for data recovery if needed. This is especially important
        for regulatory compliance in a government system.
        """
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def restore(self):
        """
        Restore a soft-deleted record.
        
        Allows recovery of accidentally deleted records.
        Should be logged for audit purposes in production.
        """
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

    @property
    def is_deleted(self):
        """Check if the record has been soft-deleted."""
        return not self.is_active

    def hard_delete(self):
        """
        Permanently delete the record from database.
        
        Use with caution - this action is irreversible and
        should be restricted to admin users only.
        """
        super().delete()


class TimeStampedModel(models.Model):
    """
    Simplified base model with only timestamps.
    Use when you need sequential IDs instead of UUIDs.
    
    This model is useful for:
    - Models that need human-readable sequential IDs
    - Models that reference external systems with integer IDs
    - Performance-critical models where UUID overhead is not desired
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]


class AuditableModel(BaseModel):
    """
    Base model with audit trail capabilities.
    
    Tracks who created and last modified each record.
    Essential for government systems requiring audit trails.
    """
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        help_text="User who created this record"
    )
    modified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_modified',
        help_text="User who last modified this record"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['modified_by']),
        ]

    def save(self, *args, **kwargs):
        """
        Override save to track the modifying user.
        
        The modifying user should be set on the model instance
        before calling save() in views or services.
        """
        from django.utils import timezone
        
        # Set modified_by if not already set
        if hasattr(self, '_current_user') and not self.modified_by:
            self.modified_by = self._current_user
            
        # Set created_by on new records
        if not self.pk and hasattr(self, '_current_user') and not self.created_by:
            self.created_by = self._current_user
            
        super().save(*args, **kwargs)

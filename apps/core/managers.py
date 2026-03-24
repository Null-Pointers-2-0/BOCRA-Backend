"""
Custom model managers for filtering soft-deleted records.
"""
from django.db import models


class ActiveManager(models.Manager):
    """
    Manager that excludes soft-deleted records by default.
    
    This is the default manager for models that inherit from BaseModel.
    It ensures that soft-deleted records don't appear in normal queries.
    
    Example:
        # Only returns active records
        MyModel.objects.all()
        
        # Returns all records including deleted
        MyModel.all_objects.all()
    """
    def get_queryset(self):
        """
        Filter out soft-deleted records.
        
        Returns:
            QuerySet: QuerySet with only active (not soft-deleted) records
        """
        return super().get_queryset().filter(is_active=True)

    def deleted(self):
        """
        Get only soft-deleted records.
        
        Returns:
            QuerySet: QuerySet with only soft-deleted records
        """
        return super().get_queryset().filter(is_active=False)


class AllObjectsManager(models.Manager):
    """
    Manager that includes all records, including soft-deleted.
    
    Use this when you need to access deleted records for:
    - Audit trails
    - Data recovery
    - Administrative functions
    
    This manager should be accessed via the 'all_objects' attribute
    on models that inherit from BaseModel.
    """
    def get_queryset(self):
        """
        Return all records without filtering.
        
        Returns:
            QuerySet: QuerySet with all records (active and deleted)
        """
        return super().get_queryset().all()

    def active(self):
        """
        Get only active records.
        
        Returns:
            QuerySet: QuerySet with only active records
        """
        return self.get_queryset().filter(is_active=True)

    def deleted(self):
        """
        Get only soft-deleted records.
        
        Returns:
            QuerySet: QuerySet with only soft-deleted records
        """
        return self.get_queryset().filter(is_active=False)


class AuditableManager(ActiveManager):
    """
    Manager for auditable models with user tracking.
    
    Provides additional query methods for audit-related operations.
    """
    def created_by_user(self, user):
        """
        Get records created by a specific user.
        
        Args:
            user: User instance or user ID
            
        Returns:
            QuerySet: Records created by the specified user
        """
        if hasattr(user, 'pk'):
            user_id = user.pk
        else:
            user_id = user
            
        return self.get_queryset().filter(created_by_id=user_id)

    def modified_by_user(self, user):
        """
        Get records last modified by a specific user.
        
        Args:
            user: User instance or user ID
            
        Returns:
            QuerySet: Records last modified by the specified user
        """
        if hasattr(user, 'pk'):
            user_id = user.pk
        else:
            user_id = user
            
        return self.get_queryset().filter(modified_by_id=user_id)

    def created_between(self, start_date, end_date):
        """
        Get records created within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            QuerySet: Records created within the specified date range
        """
        return self.get_queryset().filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

    def modified_between(self, start_date, end_date):
        """
        Get records modified within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            QuerySet: Records modified within the specified date range
        """
        return self.get_queryset().filter(
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date
        )

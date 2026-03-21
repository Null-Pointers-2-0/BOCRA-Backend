from django.db import models


class ActiveManager(models.Manager):
    """
    Default manager for soft-delete models.
    Automatically excludes is_deleted=True records from all querysets.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def deleted(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(is_deleted=True)


class AllObjectsManager(models.Manager):
    """
    Unfiltered manager — returns all records including soft-deleted.
    Attach as `all_objects` alongside the default ActiveManager.
    """

    def active(self):
        return self.get_queryset().filter(is_deleted=False)

    def deleted(self):
        return self.get_queryset().filter(is_deleted=True)


class AuditableManager(ActiveManager):
    """
    Extends ActiveManager with audit-trail query helpers.
    Use on models that inherit from AuditableModel.
    """

    def created_by_user(self, user):
        return self.get_queryset().filter(created_by=user)

    def modified_by_user(self, user):
        return self.get_queryset().filter(modified_by=user)

    def created_between(self, start, end):
        return self.get_queryset().filter(created_at__range=(start, end))

    def modified_between(self, start, end):
        return self.get_queryset().filter(updated_at__range=(start, end))

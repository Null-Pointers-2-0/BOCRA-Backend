"""
Post-registration signal: link anonymous complaints to new user accounts.

When a user's email is verified, find any anonymous complaints submitted
with that email address and associate them with the user.
"""
import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import User

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=User)
def link_anonymous_complaints(sender, instance, **kwargs):
    """
    When email_verified transitions from False → True, find any anonymous
    complaints with a matching email and link them to this user.
    """
    if not instance.pk:
        return  # new user, not yet saved

    try:
        old = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    # Only fire when email_verified changes from False to True
    if old.email_verified or not instance.email_verified:
        return

    from complaints.models import Complaint

    updated = Complaint.objects.filter(
        complainant_email__iexact=instance.email,
        complainant__isnull=True,
        is_deleted=False,
    ).update(complainant=instance)

    if updated:
        logger.info(
            "Linked %d anonymous complaint(s) to user %s (%s)",
            updated,
            instance.pk,
            instance.email,
        )

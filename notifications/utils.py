"""
Notification utility — centralised helper for creating notifications.

Other apps call ``notify_user()`` to create in-app notifications.
In future this function can also dispatch email / SMS via Celery.
"""

from .models import Notification, NotificationType


def notify_user(
    recipient,
    title: str,
    message: str,
    related_object_type: str = "",
    related_object_id=None,
    notification_type: str = NotificationType.IN_APP,
) -> Notification:
    """
    Create and return an in-app notification for *recipient*.

    Parameters
    ----------
    recipient : User
        The user who will receive the notification.
    title : str
        Short notification title (max 300 chars).
    message : str
        Full notification body.
    related_object_type : str, optional
        E.g. "complaint", "licence", "publication".
    related_object_id : UUID, optional
        PK of the related object.
    notification_type : str, optional
        Default ``IN_APP``. Future: ``EMAIL``, ``SMS``.

    Returns
    -------
    Notification
    """
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
    )

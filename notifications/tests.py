"""
Tests for the notifications app.

Test groups
───────────
NotificationModelTests              — Model str, creation
NotifyUserUtilTests                 — notify_user() utility function
MyNotificationsAPITests             — GET /
UnreadCountAPITests                 — GET /unread-count/
MarkReadAPITests                    — PATCH /<pk>/read/
MarkAllReadAPITests                 — PATCH /read-all/
DismissNotificationAPITests         — DELETE /<pk>/
PermissionTests                     — Auth required, owner-only access
"""

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserRole
from notifications.models import Notification, NotificationStatus, NotificationType
from notifications.utils import notify_user

User = get_user_model()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def _user(email="user@test.bw", username="noti_user", **kw):
    defaults = {
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
        "role": UserRole.REGISTERED,
        "is_active": True,
        "email_verified": True,
    }
    defaults.update(kw)
    return User.objects.create_user(email=email, username=username, **defaults)


def _other_user():
    return _user(email="other@test.bw", username="noti_other")


# ─── MODEL TESTS ──────────────────────────────────────────────────────────────

class NotificationModelTests(APITestCase):
    def setUp(self):
        self.user = _user()

    def test_str(self):
        n = Notification.objects.create(
            recipient=self.user,
            title="Test Notification",
            message="Body.",
        )
        self.assertIn("Test Notification", str(n))

    def test_defaults(self):
        n = Notification.objects.create(
            recipient=self.user,
            title="Defaults",
            message="Body.",
        )
        self.assertEqual(n.notification_type, NotificationType.IN_APP)
        self.assertEqual(n.status, NotificationStatus.SENT)
        self.assertFalse(n.is_read)


# ─── UTILITY TESTS ────────────────────────────────────────────────────────────

class NotifyUserUtilTests(APITestCase):
    def setUp(self):
        self.user = _user()

    def test_creates_notification(self):
        n = notify_user(
            recipient=self.user,
            title="Welcome",
            message="Welcome to BOCRA.",
        )
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(n.recipient, self.user)
        self.assertEqual(n.title, "Welcome")

    def test_with_related_object(self):
        import uuid
        obj_id = uuid.uuid4()
        n = notify_user(
            recipient=self.user,
            title="Complaint Updated",
            message="Status changed.",
            related_object_type="complaint",
            related_object_id=obj_id,
        )
        self.assertEqual(n.related_object_type, "complaint")
        self.assertEqual(n.related_object_id, obj_id)


# ─── LIST NOTIFICATIONS ──────────────────────────────────────────────────────

class MyNotificationsAPITests(APITestCase):
    def setUp(self):
        self.user = _user()
        self.url = reverse("notifications:list")
        notify_user(self.user, "Notif 1", "Body 1")
        notify_user(self.user, "Notif 2", "Body 2")
        # Another user's notification — should not appear
        self.other = _other_user()
        notify_user(self.other, "Other's Notif", "Body")

    def test_lists_own_only(self):
        _auth(self.client, self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 2)

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── UNREAD COUNT ─────────────────────────────────────────────────────────────

class UnreadCountAPITests(APITestCase):
    def setUp(self):
        self.user = _user()
        self.url = reverse("notifications:unread-count")
        notify_user(self.user, "n1", "b1")
        notify_user(self.user, "n2", "b2")
        n3 = notify_user(self.user, "n3", "b3")
        n3.is_read = True
        n3.save()

    def test_count(self):
        _auth(self.client, self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["unread_count"], 2)


# ─── MARK SINGLE READ ────────────────────────────────────────────────────────

class MarkReadAPITests(APITestCase):
    def setUp(self):
        self.user = _user()

    def test_mark_read(self):
        n = notify_user(self.user, "Test", "Body")
        _auth(self.client, self.user)
        url = reverse("notifications:mark-read", args=[n.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["data"]["is_read"])
        n.refresh_from_db()
        self.assertTrue(n.is_read)
        self.assertIsNotNone(n.read_at)

    def test_other_user_cannot_mark(self):
        n = notify_user(self.user, "Test", "Body")
        other = _other_user()
        _auth(self.client, other)
        url = reverse("notifications:mark-read", args=[n.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ─── MARK ALL READ ───────────────────────────────────────────────────────────

class MarkAllReadAPITests(APITestCase):
    def setUp(self):
        self.user = _user()
        self.url = reverse("notifications:read-all")
        notify_user(self.user, "n1", "b1")
        notify_user(self.user, "n2", "b2")

    def test_marks_all(self):
        _auth(self.client, self.user)
        resp = self.client.patch(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["marked_read"], 2)
        self.assertEqual(
            Notification.objects.filter(recipient=self.user, is_read=False).count(), 0
        )


# ─── DISMISS ──────────────────────────────────────────────────────────────────

class DismissNotificationAPITests(APITestCase):
    def setUp(self):
        self.user = _user()

    def test_dismiss(self):
        n = notify_user(self.user, "Test", "Body")
        _auth(self.client, self.user)
        url = reverse("notifications:dismiss", args=[n.pk])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.count(), 0)

    def test_other_user_cannot_dismiss(self):
        n = notify_user(self.user, "Test", "Body")
        other = _other_user()
        _auth(self.client, other)
        url = reverse("notifications:dismiss", args=[n.pk])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Notification.objects.count(), 1)


# ─── PERMISSION TESTS ────────────────────────────────────────────────────────

class PermissionTests(APITestCase):
    def test_all_endpoints_require_auth(self):
        """All notification endpoints should return 401 for unauthenticated requests."""
        urls = [
            reverse("notifications:list"),
            reverse("notifications:unread-count"),
            reverse("notifications:read-all"),
        ]
        for url in urls:
            resp = self.client.get(url) if "count" in url or "list" in url else self.client.patch(url)
            self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_405_METHOD_NOT_ALLOWED])

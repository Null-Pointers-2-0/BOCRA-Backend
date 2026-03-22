"""
Tests for the publications app.

Test groups
───────────
PublicationModelTests               — Model str, slug generation, soft delete
PublicationCategoriesAPITests       — GET /categories/
PublicPublicationListAPITests       — GET / (public list, search, filter)
PublicPublicationDetailAPITests     — GET /<pk>/ (public detail)
PublicationDownloadAPITests         — GET /<pk>/download/
StaffPublicationCreateAPITests      — POST /staff/
StaffPublicationListAPITests        — GET /staff/list/
StaffPublicationDetailAPITests      — GET /staff/<pk>/
StaffPublicationUpdateAPITests      — PATCH /staff/<pk>/edit/
PublishPublicationAPITests          — PATCH /staff/<pk>/publish/
ArchivePublicationAPITests          — PATCH /staff/<pk>/archive/
DeletePublicationAPITests           — DELETE /staff/<pk>/delete/
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserRole
from publications.models import (
    Publication,
    PublicationAttachment,
    PublicationCategory,
    PublicationStatus,
)

User = get_user_model()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def _staff_user(**kw):
    defaults = {
        "email": "staff@bocra.org.bw",
        "username": "pub_staff",
        "password": "StaffPass123!",
        "first_name": "Staff",
        "last_name": "User",
        "role": UserRole.STAFF,
        "is_active": True,
        "email_verified": True,
    }
    defaults.update(kw)
    return User.objects.create_user(**defaults)


def _citizen_user(**kw):
    defaults = {
        "email": "citizen@test.bw",
        "username": "pub_citizen",
        "password": "CitizenPass123!",
        "first_name": "Citizen",
        "last_name": "User",
        "role": UserRole.CITIZEN,
        "is_active": True,
        "email_verified": True,
    }
    defaults.update(kw)
    return User.objects.create_user(**defaults)


def _dummy_file(name="doc.pdf", content=b"%PDF-1.4 test", content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def _create_publication(staff, **kw):
    defaults = {
        "title": "Regulation on QoS",
        "summary": "Quality of Service regulation for telecoms operators.",
        "category": PublicationCategory.REGULATION,
        "status": PublicationStatus.DRAFT,
        "file": _dummy_file(),
        "created_by": staff,
    }
    defaults.update(kw)
    return Publication.objects.create(**defaults)


# ─── MODEL TESTS ──────────────────────────────────────────────────────────────

class PublicationModelTests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_str(self):
        pub = _create_publication(self.staff)
        self.assertEqual(str(pub), "Regulation on QoS")

    def test_slug_auto_generated(self):
        pub = _create_publication(self.staff)
        self.assertTrue(pub.slug)
        self.assertIn("regulation-on-qos", pub.slug)

    def test_slug_unique_on_collision(self):
        pub1 = _create_publication(self.staff, title="Test Doc")
        pub2 = _create_publication(self.staff, title="Test Doc")
        self.assertNotEqual(pub1.slug, pub2.slug)

    def test_soft_delete(self):
        pub = _create_publication(self.staff)
        pub.soft_delete()
        self.assertTrue(pub.is_deleted)
        self.assertIsNotNone(pub.deleted_at)

    def test_year_auto_set_from_published_date(self):
        pub = _create_publication(
            self.staff,
            published_date=timezone.now().date(),
        )
        self.assertEqual(pub.year, timezone.now().year)


# ─── PUBLICATION CATEGORIES ───────────────────────────────────────────────────

class PublicationCategoriesAPITests(APITestCase):
    def test_list_categories(self):
        url = reverse("publications:categories")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["success"])
        values = [c["value"] for c in resp.data["data"]]
        self.assertIn("REGULATION", values)
        self.assertIn("POLICY", values)


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

class PublicPublicationListAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.pub1 = _create_publication(
            self.staff,
            title="Published Reg",
            status=PublicationStatus.PUBLISHED,
            published_date=timezone.now().date(),
        )
        self.pub2 = _create_publication(
            self.staff,
            title="Draft Doc",
            status=PublicationStatus.DRAFT,
        )
        self.pub3 = _create_publication(
            self.staff,
            title="Published Policy",
            category=PublicationCategory.POLICY,
            status=PublicationStatus.PUBLISHED,
            published_date=timezone.now().date(),
        )

    def test_public_sees_only_published(self):
        url = reverse("publications:list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [p["title"] for p in resp.data["data"]]
        self.assertIn("Published Reg", titles)
        self.assertIn("Published Policy", titles)
        self.assertNotIn("Draft Doc", titles)

    def test_filter_by_category(self):
        url = reverse("publications:list")
        resp = self.client.get(url, {"category": "POLICY"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["title"], "Published Policy")

    def test_search(self):
        url = reverse("publications:list")
        resp = self.client.get(url, {"search": "Policy"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

class PublicPublicationDetailAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.pub = _create_publication(
            self.staff,
            status=PublicationStatus.PUBLISHED,
            published_date=timezone.now().date(),
        )

    def test_retrieve_published(self):
        url = reverse("publications:detail", kwargs={"pk": self.pub.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], self.pub.title)

    def test_draft_not_visible(self):
        draft = _create_publication(self.staff, title="Secret Draft")
        url = reverse("publications:detail", kwargs={"pk": draft.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────

class PublicationDownloadAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.pub = _create_publication(
            self.staff,
            status=PublicationStatus.PUBLISHED,
            published_date=timezone.now().date(),
        )

    def test_download_increments_count(self):
        old_count = self.pub.download_count
        url = reverse("publications:download", kwargs={"pk": self.pub.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.pub.refresh_from_db()
        self.assertEqual(self.pub.download_count, old_count + 1)

    def test_download_draft_fails(self):
        draft = _create_publication(self.staff, title="Draft File")
        url = reverse("publications:download", kwargs={"pk": draft.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ─── STAFF CREATE ─────────────────────────────────────────────────────────────

class StaffPublicationCreateAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)

    def test_create_publication(self):
        url = reverse("publications:staff-create")
        data = {
            "title": "New Regulation",
            "summary": "New reg summary",
            "category": "REGULATION",
            "file": _dummy_file(),
        }
        resp = self.client.post(url, data, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["data"]["status"], "DRAFT")

    def test_citizen_cannot_create(self):
        citizen = _citizen_user()
        client = APIClient()
        _auth(client, citizen)
        url = reverse("publications:staff-create")
        data = {
            "title": "Hack",
            "summary": "X",
            "category": "REGULATION",
            "file": _dummy_file(),
        }
        resp = client.post(url, data, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

class StaffPublicationListAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.pub = _create_publication(self.staff)
        self.draft = _create_publication(self.staff, title="Draft 2")

    def test_staff_sees_all(self):
        url = reverse("publications:staff-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 2)

    def test_citizen_denied(self):
        citizen = _citizen_user()
        client = APIClient()
        _auth(client, citizen)
        url = reverse("publications:staff-list")
        resp = client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

class StaffPublicationDetailAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.pub = _create_publication(self.staff)

    def test_staff_retrieves_full_detail(self):
        url = reverse("publications:staff-detail", kwargs={"pk": self.pub.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("status", resp.data["data"])
        self.assertIn("created_by_name", resp.data["data"])


# ─── STAFF UPDATE ─────────────────────────────────────────────────────────────

class StaffPublicationUpdateAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.pub = _create_publication(self.staff)

    def test_update_title(self):
        url = reverse("publications:staff-update", kwargs={"pk": self.pub.pk})
        resp = self.client.patch(url, {"title": "Updated Title"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.pub.refresh_from_db()
        self.assertEqual(self.pub.title, "Updated Title")

    def test_update_category(self):
        url = reverse("publications:staff-update", kwargs={"pk": self.pub.pk})
        resp = self.client.patch(url, {"category": "POLICY"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.pub.refresh_from_db()
        self.assertEqual(self.pub.category, "POLICY")


# ─── PUBLISH ──────────────────────────────────────────────────────────────────

class PublishPublicationAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.pub = _create_publication(self.staff)

    def test_publish_draft(self):
        url = reverse("publications:staff-publish", kwargs={"pk": self.pub.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.pub.refresh_from_db()
        self.assertEqual(self.pub.status, PublicationStatus.PUBLISHED)
        self.assertIsNotNone(self.pub.published_date)

    def test_publish_already_published(self):
        self.pub.status = PublicationStatus.PUBLISHED
        self.pub.save()
        url = reverse("publications:staff-publish", kwargs={"pk": self.pub.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publish_archived_fails(self):
        self.pub.status = PublicationStatus.ARCHIVED
        self.pub.save()
        url = reverse("publications:staff-publish", kwargs={"pk": self.pub.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_citizen_cannot_publish(self):
        citizen = _citizen_user()
        client = APIClient()
        _auth(client, citizen)
        url = reverse("publications:staff-publish", kwargs={"pk": self.pub.pk})
        resp = client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── ARCHIVE ──────────────────────────────────────────────────────────────────

class ArchivePublicationAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.pub = _create_publication(
            self.staff,
            status=PublicationStatus.PUBLISHED,
            published_date=timezone.now().date(),
        )

    def test_archive_published(self):
        url = reverse("publications:staff-archive", kwargs={"pk": self.pub.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.pub.refresh_from_db()
        self.assertEqual(self.pub.status, PublicationStatus.ARCHIVED)

    def test_archive_already_archived(self):
        self.pub.status = PublicationStatus.ARCHIVED
        self.pub.save()
        url = reverse("publications:staff-archive", kwargs={"pk": self.pub.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── DELETE ───────────────────────────────────────────────────────────────────

class DeletePublicationAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.pub = _create_publication(self.staff)

    def test_soft_delete(self):
        url = reverse("publications:staff-delete", kwargs={"pk": self.pub.pk})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.pub.refresh_from_db()
        self.assertTrue(self.pub.is_deleted)

    def test_deleted_not_in_public_list(self):
        self.pub.status = PublicationStatus.PUBLISHED
        self.pub.published_date = timezone.now().date()
        self.pub.save()
        self.pub.soft_delete()
        url = reverse("publications:list")
        resp = self.client.get(url)
        ids = [p["id"] for p in resp.data["data"]]
        self.assertNotIn(str(self.pub.pk), ids)

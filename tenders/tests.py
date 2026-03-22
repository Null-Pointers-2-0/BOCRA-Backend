"""
Tests for the tenders app.

Test groups
───────────
TenderModelTests                   — Model str, slug, properties
TenderCategoriesAPITests           — GET /categories/
PublicTenderListAPITests           — GET / (public list, search, filter)
PublicTenderDetailAPITests         — GET /<pk>/ (public detail)
TenderDocumentDownloadAPITests     — GET /<pk>/documents/<doc_pk>/download/
StaffTenderCreateAPITests          — POST /staff/
StaffTenderListAPITests            — GET /staff/list/
StaffTenderDetailAPITests          — GET /staff/<pk>/
StaffTenderUpdateAPITests          — PATCH /staff/<pk>/edit/
PublishTenderAPITests              — PATCH /staff/<pk>/publish/
CloseTenderAPITests                — PATCH /staff/<pk>/close/
UploadTenderDocumentAPITests       — POST /staff/<pk>/documents/
AddTenderAddendumAPITests          — POST /staff/<pk>/addenda/
AwardTenderAPITests                — POST /staff/<pk>/award/
DeleteTenderAPITests               — DELETE /staff/<pk>/delete/
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserRole
from tenders.models import (
    Tender,
    TenderAddendum,
    TenderAward,
    TenderCategory,
    TenderDocument,
    TenderStatus,
)

User = get_user_model()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def _staff_user(**kw):
    defaults = {
        "email": "staff@bocra.org.bw",
        "username": "tnd_staff",
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
        "username": "tnd_citizen",
        "password": "CitizenPass123!",
        "first_name": "Citizen",
        "last_name": "User",
        "role": UserRole.CITIZEN,
        "is_active": True,
        "email_verified": True,
    }
    defaults.update(kw)
    return User.objects.create_user(**defaults)


def _dummy_file(name="rfp.pdf", content=b"%PDF-1.4 test", content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


_ref_counter = 0

def _next_ref():
    global _ref_counter
    _ref_counter += 1
    return f"BOCRA/TENDER/2026/{_ref_counter:03d}"


def _create_tender(staff, **kw):
    defaults = {
        "title": "IT Infrastructure Upgrade",
        "reference_number": _next_ref(),
        "description": "Full scope of IT infrastructure upgrade.",
        "category": TenderCategory.IT_SERVICES,
        "status": TenderStatus.DRAFT,
        "closing_date": timezone.now() + timedelta(days=30),
        "created_by": staff,
    }
    defaults.update(kw)
    return Tender.objects.create(**defaults)


# ─── MODEL TESTS ──────────────────────────────────────────────────────────────

class TenderModelTests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_str(self):
        tender = _create_tender(self.staff, reference_number="BOCRA/T/001")
        self.assertIn("BOCRA/T/001", str(tender))

    def test_slug_auto_generated(self):
        tender = _create_tender(self.staff)
        self.assertTrue(tender.slug)

    def test_days_until_closing(self):
        tender = _create_tender(
            self.staff,
            status=TenderStatus.OPEN,
            closing_date=timezone.now() + timedelta(days=10),
        )
        self.assertIsNotNone(tender.days_until_closing)
        self.assertGreaterEqual(tender.days_until_closing, 9)

    def test_days_until_closing_closed(self):
        tender = _create_tender(self.staff, status=TenderStatus.CLOSED)
        self.assertIsNone(tender.days_until_closing)

    def test_is_overdue(self):
        tender = _create_tender(
            self.staff,
            status=TenderStatus.OPEN,
            closing_date=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(tender.is_overdue)

    def test_soft_delete(self):
        tender = _create_tender(self.staff)
        tender.soft_delete()
        self.assertTrue(tender.is_deleted)


# ─── TENDER CATEGORIES ────────────────────────────────────────────────────────

class TenderCategoriesAPITests(APITestCase):
    def test_list_categories(self):
        url = reverse("tenders:categories")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        values = [c["value"] for c in resp.data["data"]]
        self.assertIn("IT_SERVICES", values)
        self.assertIn("CONSULTING", values)


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

class PublicTenderListAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.open = _create_tender(
            self.staff,
            title="Open Tender",
            status=TenderStatus.OPEN,
        )
        self.draft = _create_tender(
            self.staff,
            title="Draft Tender",
            status=TenderStatus.DRAFT,
        )
        self.awarded = _create_tender(
            self.staff,
            title="Awarded Tender",
            status=TenderStatus.AWARDED,
        )

    def test_public_sees_non_draft(self):
        url = reverse("tenders:list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [t["title"] for t in resp.data["data"]]
        self.assertIn("Open Tender", titles)
        self.assertIn("Awarded Tender", titles)
        self.assertNotIn("Draft Tender", titles)

    def test_filter_by_status(self):
        url = reverse("tenders:list")
        resp = self.client.get(url, {"status": "OPEN"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["title"], "Open Tender")

    def test_search(self):
        url = reverse("tenders:list")
        resp = self.client.get(url, {"search": "Awarded"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

class PublicTenderDetailAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.tender = _create_tender(
            self.staff,
            status=TenderStatus.OPEN,
        )

    def test_retrieve_open_tender(self):
        url = reverse("tenders:detail", kwargs={"pk": self.tender.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], self.tender.title)
        self.assertIn("documents", resp.data["data"])
        self.assertIn("addenda", resp.data["data"])

    def test_draft_not_visible(self):
        draft = _create_tender(self.staff, title="Secret", status=TenderStatus.DRAFT)
        url = reverse("tenders:detail", kwargs={"pk": draft.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ─── DOCUMENT DOWNLOAD ───────────────────────────────────────────────────────

class TenderDocumentDownloadAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.tender = _create_tender(self.staff, status=TenderStatus.OPEN)
        self.doc = TenderDocument.objects.create(
            tender=self.tender,
            title="RFP",
            file=_dummy_file("rfp.pdf"),
            uploaded_by=self.staff,
        )

    def test_download(self):
        url = reverse(
            "tenders:doc-download",
            kwargs={"pk": self.tender.pk, "doc_pk": self.doc.pk},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ─── STAFF CREATE ─────────────────────────────────────────────────────────────

class StaffTenderCreateAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)

    def test_create_tender(self):
        url = reverse("tenders:staff-create")
        data = {
            "title": "New Tender",
            "reference_number": "BOCRA/NEW/001",
            "description": "A new tender.",
            "category": "IT_SERVICES",
            "closing_date": (timezone.now() + timedelta(days=60)).isoformat(),
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["data"]["status"], "DRAFT")

    def test_citizen_cannot_create(self):
        citizen = _citizen_user()
        client = APIClient()
        _auth(client, citizen)
        url = reverse("tenders:staff-create")
        data = {
            "title": "Hack",
            "reference_number": "BOCRA/HACK/001",
            "description": "Nope",
            "category": "IT_SERVICES",
            "closing_date": (timezone.now() + timedelta(days=60)).isoformat(),
        }
        resp = client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

class StaffTenderListAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.t1 = _create_tender(self.staff)
        self.t2 = _create_tender(self.staff, title="Another Tender")

    def test_staff_sees_all(self):
        url = reverse("tenders:staff-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 2)

    def test_citizen_denied(self):
        citizen = _citizen_user()
        client = APIClient()
        _auth(client, citizen)
        url = reverse("tenders:staff-list")
        resp = client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

class StaffTenderDetailAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff)

    def test_staff_retrieves_detail(self):
        url = reverse("tenders:staff-detail", kwargs={"pk": self.tender.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("status", resp.data["data"])
        self.assertIn("created_by_name", resp.data["data"])


# ─── STAFF UPDATE ─────────────────────────────────────────────────────────────

class StaffTenderUpdateAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff)

    def test_update_title(self):
        url = reverse("tenders:staff-update", kwargs={"pk": self.tender.pk})
        resp = self.client.patch(url, {"title": "Updated Title"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tender.refresh_from_db()
        self.assertEqual(self.tender.title, "Updated Title")


# ─── PUBLISH ──────────────────────────────────────────────────────────────────

class PublishTenderAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff)

    def test_publish_draft(self):
        url = reverse("tenders:staff-publish", kwargs={"pk": self.tender.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tender.refresh_from_db()
        self.assertEqual(self.tender.status, TenderStatus.OPEN)
        self.assertIsNotNone(self.tender.opening_date)

    def test_publish_non_draft_fails(self):
        self.tender.status = TenderStatus.OPEN
        self.tender.save()
        url = reverse("tenders:staff-publish", kwargs={"pk": self.tender.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publish_without_closing_date_fails(self):
        self.tender.closing_date = None
        self.tender.save()
        url = reverse("tenders:staff-publish", kwargs={"pk": self.tender.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── CLOSE ────────────────────────────────────────────────────────────────────

class CloseTenderAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff, status=TenderStatus.OPEN)

    def test_close_open_tender(self):
        url = reverse("tenders:staff-close", kwargs={"pk": self.tender.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tender.refresh_from_db()
        self.assertEqual(self.tender.status, TenderStatus.CLOSED)

    def test_close_draft_fails(self):
        self.tender.status = TenderStatus.DRAFT
        self.tender.save()
        url = reverse("tenders:staff-close", kwargs={"pk": self.tender.pk})
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── UPLOAD DOCUMENT ──────────────────────────────────────────────────────────

class UploadTenderDocumentAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff)

    def test_upload_document(self):
        url = reverse("tenders:staff-upload-doc", kwargs={"pk": self.tender.pk})
        data = {"title": "ToR", "file": _dummy_file("tor.pdf")}
        resp = self.client.post(url, data, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TenderDocument.objects.filter(tender=self.tender).count(), 1)


# ─── ADD ADDENDUM ─────────────────────────────────────────────────────────────

class AddTenderAddendumAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff, status=TenderStatus.OPEN)

    def test_add_addendum(self):
        url = reverse("tenders:staff-addendum", kwargs={"pk": self.tender.pk})
        data = {"title": "Clarification 1", "content": "The budget is flexible."}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TenderAddendum.objects.filter(tender=self.tender).count(), 1)

    def test_addendum_on_closed_fails(self):
        self.tender.status = TenderStatus.CLOSED
        self.tender.save()
        url = reverse("tenders:staff-addendum", kwargs={"pk": self.tender.pk})
        data = {"title": "Late Clarification", "content": "Too late."}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── AWARD ────────────────────────────────────────────────────────────────────

class AwardTenderAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff, status=TenderStatus.CLOSED)

    def test_award_closed_tender(self):
        url = reverse("tenders:staff-award", kwargs={"pk": self.tender.pk})
        data = {
            "awardee_name": "TechCo Botswana",
            "award_date": timezone.now().date().isoformat(),
            "award_amount": "750000.00",
            "summary": "Best technical proposal.",
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tender.refresh_from_db()
        self.assertEqual(self.tender.status, TenderStatus.AWARDED)
        self.assertTrue(TenderAward.objects.filter(tender=self.tender).exists())

    def test_award_open_fails(self):
        self.tender.status = TenderStatus.OPEN
        self.tender.save()
        url = reverse("tenders:staff-award", kwargs={"pk": self.tender.pk})
        data = {
            "awardee_name": "Nope",
            "award_date": timezone.now().date().isoformat(),
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_double_award_fails(self):
        TenderAward.objects.create(
            tender=self.tender,
            awardee_name="First Awardee",
            award_date=timezone.now().date(),
            awarded_by=self.staff,
        )
        url = reverse("tenders:staff-award", kwargs={"pk": self.tender.pk})
        data = {
            "awardee_name": "Second",
            "award_date": timezone.now().date().isoformat(),
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── DELETE ───────────────────────────────────────────────────────────────────

class DeleteTenderAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.client = APIClient()
        _auth(self.client, self.staff)
        self.tender = _create_tender(self.staff)

    def test_soft_delete(self):
        url = reverse("tenders:staff-delete", kwargs={"pk": self.tender.pk})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tender.refresh_from_db()
        self.assertTrue(self.tender.is_deleted)

    def test_deleted_not_in_public_list(self):
        self.tender.status = TenderStatus.OPEN
        self.tender.save()
        self.tender.soft_delete()
        url = reverse("tenders:list")
        resp = self.client.get(url)
        ids = [t["id"] for t in resp.data["data"]]
        self.assertNotIn(str(self.tender.pk), ids)

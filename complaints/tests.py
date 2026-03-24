"""
Tests for the complaints app.

Test groups
───────────
ComplaintModelTests          — Model str, SLA properties, state machine transitions
ComplaintStatusLogTests      — Audit log creation on every transition
ComplaintUtilsTests          — Reference number generation
SubmitComplaintAPITests      — POST /submit/ (anonymous + authenticated)
TrackComplaintAPITests       — GET /track/?ref=
ComplaintCategoriesAPITests  — GET /categories/
MyComplaintsAPITests         — GET / (authenticated list)
ComplaintDetailAPITests      — GET /<pk>/ (owner vs staff views)
UploadEvidenceAPITests       — POST /<pk>/documents/
AssignComplaintAPITests      — PATCH /<pk>/assign/
UpdateStatusAPITests         — PATCH /<pk>/status/
AddCaseNoteAPITests          — POST /<pk>/notes/
ResolveComplaintAPITests     — POST /<pk>/resolve/
StaffComplaintListAPITests   — GET /staff/
StaffComplaintDetailAPITests — GET /staff/<pk>/
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserRole
from complaints.models import (
    CaseNote,
    Complaint,
    ComplaintCategory,
    ComplaintDocument,
    ComplaintPriority,
    ComplaintStatus,
    ComplaintStatusLog,
    SLA_DAYS_BY_PRIORITY,
)
from complaints.utils import generate_complaint_reference

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def create_user(
    email="citizen@example.com",
    username="citizen",
    role=UserRole.REGISTERED,
    **kwargs,
):
    user = User.objects.create_user(
        email=email,
        username=username,
        first_name="Mpho",
        last_name="Kgosi",
        password="TestPass123!",
        role=role,
        **kwargs,
    )
    user.verify_email()
    return user


def create_staff(email="staff@bocra.bw", username="staffmember"):
    return create_user(email=email, username=username, role=UserRole.STAFF)


def auth_client(user) -> APIClient:
    """Return an APIClient pre-authenticated with user's JWT."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def create_complaint(complainant=None, **kwargs):
    """Create a complaint with sensible defaults."""
    defaults = dict(
        reference_number=generate_complaint_reference(),
        complainant=complainant,
        complainant_name="Mpho Kgosi",
        complainant_email="mpho@example.com",
        against_operator_name="Mascom Wireless",
        category=ComplaintCategory.SERVICE_QUALITY,
        subject="Frequent call drops in Gaborone CBD",
        description="Experiencing frequent call drops for the past two weeks.",
        priority=ComplaintPriority.MEDIUM,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=timezone.now() + timedelta(days=14),
    )
    defaults.update(kwargs)
    return Complaint.objects.create(**defaults)


def dummy_pdf():
    return SimpleUploadedFile(
        "evidence.pdf",
        b"%PDF-1.4 test content",
        content_type="application/pdf",
    )


SUBMIT_URL = reverse("complaints:submit")
TRACK_URL = reverse("complaints:track")
CATEGORIES_URL = reverse("complaints:categories")
MY_COMPLAINTS_URL = reverse("complaints:my-complaints")
STAFF_LIST_URL = reverse("complaints:staff-list")


# ─── MODEL TESTS ──────────────────────────────────────────────────────────────

class ComplaintModelTests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        self.complaint = create_complaint()

    def test_str(self):
        s = str(self.complaint)
        self.assertIn(self.complaint.reference_number, s)
        self.assertIn("SUBMITTED", s)

    def test_is_overdue_false_when_sla_in_future(self):
        self.complaint.sla_deadline = timezone.now() + timedelta(days=5)
        self.complaint.save()
        self.assertFalse(self.complaint.is_overdue)

    def test_is_overdue_true_when_sla_past(self):
        self.complaint.sla_deadline = timezone.now() - timedelta(days=1)
        self.complaint.save()
        self.assertTrue(self.complaint.is_overdue)

    def test_is_overdue_false_when_resolved(self):
        self.complaint.status = ComplaintStatus.RESOLVED
        self.complaint.sla_deadline = timezone.now() - timedelta(days=1)
        self.complaint.save()
        self.assertFalse(self.complaint.is_overdue)

    def test_days_until_sla(self):
        self.complaint.sla_deadline = timezone.now() + timedelta(days=10)
        self.complaint.save()
        self.assertAlmostEqual(self.complaint.days_until_sla, 10, delta=1)

    def test_days_until_sla_none_when_no_deadline(self):
        self.complaint.sla_deadline = None
        self.complaint.save()
        self.assertIsNone(self.complaint.days_until_sla)

    # ── State machine ────────────────────────────────────────────────────────

    def test_valid_transition_submitted_to_assigned(self):
        self.assertTrue(self.complaint.can_transition_to(ComplaintStatus.ASSIGNED))

    def test_invalid_transition_submitted_to_resolved(self):
        self.assertFalse(self.complaint.can_transition_to(ComplaintStatus.RESOLVED))

    def test_transition_status_happy_path(self):
        log = self.complaint.transition_status(
            ComplaintStatus.ASSIGNED, changed_by=self.staff, reason="Assigned."
        )
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, ComplaintStatus.ASSIGNED)
        self.assertIsInstance(log, ComplaintStatusLog)
        self.assertEqual(log.to_status, ComplaintStatus.ASSIGNED)

    def test_transition_status_raises_on_invalid(self):
        with self.assertRaises(ValueError):
            self.complaint.transition_status(
                ComplaintStatus.CLOSED, changed_by=self.staff
            )

    def test_resolve_sets_resolved_at(self):
        self.complaint.status = ComplaintStatus.INVESTIGATING
        self.complaint.save()
        self.complaint.transition_status(
            ComplaintStatus.RESOLVED, changed_by=self.staff
        )
        self.complaint.refresh_from_db()
        self.assertIsNotNone(self.complaint.resolved_at)

    def test_reopen_clears_resolved_at(self):
        self.complaint.status = ComplaintStatus.RESOLVED
        self.complaint.resolved_at = timezone.now()
        self.complaint.save()
        self.complaint.transition_status(
            ComplaintStatus.REOPENED, changed_by=self.staff
        )
        self.complaint.refresh_from_db()
        self.assertIsNone(self.complaint.resolved_at)

    def test_full_happy_path(self):
        """Walk the complaint through the full happy path."""
        c = self.complaint
        c.transition_status(ComplaintStatus.ASSIGNED, self.staff)
        c.transition_status(ComplaintStatus.INVESTIGATING, self.staff)
        c.transition_status(ComplaintStatus.RESOLVED, self.staff)
        c.transition_status(ComplaintStatus.CLOSED, self.staff)
        c.refresh_from_db()
        self.assertEqual(c.status, ComplaintStatus.CLOSED)
        self.assertEqual(ComplaintStatusLog.objects.filter(complaint=c).count(), 4)


class ComplaintStatusLogTests(APITestCase):

    def test_log_created_on_transition(self):
        staff = create_staff()
        complaint = create_complaint()
        complaint.transition_status(ComplaintStatus.ASSIGNED, staff, reason="Test")
        log = ComplaintStatusLog.objects.get(complaint=complaint)
        self.assertEqual(log.from_status, ComplaintStatus.SUBMITTED)
        self.assertEqual(log.to_status, ComplaintStatus.ASSIGNED)
        self.assertEqual(log.changed_by, staff)
        self.assertEqual(log.reason, "Test")


class ComplaintUtilsTests(APITestCase):

    def test_reference_format(self):
        ref = generate_complaint_reference()
        self.assertTrue(ref.startswith("CMP-"))
        parts = ref.split("-")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[2]), 6)

    def test_sequential_references(self):
        ref1 = generate_complaint_reference()
        create_complaint(reference_number=ref1)
        ref2 = generate_complaint_reference()
        self.assertNotEqual(ref1, ref2)
        seq1 = int(ref1.split("-")[-1])
        seq2 = int(ref2.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)


# ─── SUBMIT TESTS ─────────────────────────────────────────────────────────────

class SubmitComplaintAPITests(APITestCase):

    def _valid_payload(self, **overrides):
        data = {
            "complainant_name": "Mpho Kgosi",
            "complainant_email": "mpho@example.com",
            "against_operator_name": "Mascom Wireless",
            "category": "SERVICE_QUALITY",
            "subject": "Call drops in CBD",
            "description": "Frequent call drops for two weeks.",
        }
        data.update(overrides)
        return data

    @patch("complaints.views.send_complaint_submitted_email.delay")
    def test_anonymous_submit_success(self, mock_email):
        resp = self.client.post(SUBMIT_URL, self._valid_payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["success"])
        self.assertIn("reference_number", resp.data["data"])
        self.assertEqual(resp.data["data"]["status"], "SUBMITTED")
        mock_email.assert_called_once()

    @patch("complaints.views.send_complaint_submitted_email.delay")
    def test_authenticated_submit_auto_fills_name(self, mock_email):
        user = create_user()
        client = auth_client(user)
        payload = self._valid_payload()
        del payload["complainant_name"]
        del payload["complainant_email"]
        resp = client.post(SUBMIT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        complaint = Complaint.objects.get(id=resp.data["data"]["id"])
        self.assertEqual(complaint.complainant, user)
        self.assertIn(user.first_name, complaint.complainant_name)

    @patch("complaints.views.send_complaint_submitted_email.delay")
    def test_sla_auto_calculated(self, mock_email):
        resp = self.client.post(
            SUBMIT_URL,
            self._valid_payload(priority="URGENT"),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(resp.data["data"]["sla_deadline"])
        complaint = Complaint.objects.get(id=resp.data["data"]["id"])
        expected_sla_days = SLA_DAYS_BY_PRIORITY[ComplaintPriority.URGENT]
        delta = complaint.sla_deadline - complaint.created_at
        self.assertAlmostEqual(delta.days, expected_sla_days, delta=1)

    def test_submit_requires_category(self):
        payload = self._valid_payload()
        del payload["category"]
        resp = self.client.post(SUBMIT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_requires_subject(self):
        payload = self._valid_payload()
        del payload["subject"]
        resp = self.client.post(SUBMIT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── TRACK TESTS ──────────────────────────────────────────────────────────────

class TrackComplaintAPITests(APITestCase):

    def setUp(self):
        self.complaint = create_complaint()

    def test_track_by_reference(self):
        resp = self.client.get(TRACK_URL, {"ref": self.complaint.reference_number})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp.data["data"]["reference_number"],
            self.complaint.reference_number,
        )

    def test_track_missing_ref_param(self):
        resp = self.client.get(TRACK_URL)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_track_not_found(self):
        resp = self.client.get(TRACK_URL, {"ref": "CMP-0000-999999"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_track_case_insensitive(self):
        ref = self.complaint.reference_number.lower()
        resp = self.client.get(TRACK_URL, {"ref": ref})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ─── CATEGORIES TESTS ─────────────────────────────────────────────────────────

class ComplaintCategoriesAPITests(APITestCase):

    def test_returns_all_categories(self):
        resp = self.client.get(CATEGORIES_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        values = [c["value"] for c in resp.data["data"]]
        self.assertIn("SERVICE_QUALITY", values)
        self.assertIn("BILLING", values)
        self.assertEqual(len(resp.data["data"]), len(ComplaintCategory.choices))


# ─── MY COMPLAINTS TESTS ──────────────────────────────────────────────────────

class MyComplaintsAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.client = auth_client(self.user)
        self.complaint = create_complaint(complainant=self.user)
        # Another user's complaint — should not appear
        other = create_user(email="other@example.com", username="other")
        create_complaint(complainant=other)

    def test_returns_only_own_complaints(self):
        resp = self.client.get(MY_COMPLAINTS_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(
            resp.data["data"][0]["reference_number"],
            self.complaint.reference_number,
        )

    def test_unauthenticated_rejected(self):
        client = APIClient()
        resp = client.get(MY_COMPLAINTS_URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── COMPLAINT DETAIL TESTS ───────────────────────────────────────────────────

class ComplaintDetailAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.staff = create_staff()
        self.complaint = create_complaint(complainant=self.user)
        # Add an internal note and a public note
        CaseNote.objects.create(
            complaint=self.complaint, author=self.staff,
            content="Internal investigation note.", is_internal=True,
        )
        CaseNote.objects.create(
            complaint=self.complaint, author=self.staff,
            content="Public update for complainant.", is_internal=False,
        )

    def _detail_url(self, pk=None):
        return reverse("complaints:detail", kwargs={"pk": pk or self.complaint.pk})

    def test_owner_sees_complaint(self):
        client = auth_client(self.user)
        resp = client.get(self._detail_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["reference_number"], self.complaint.reference_number)

    def test_owner_only_sees_non_internal_notes(self):
        client = auth_client(self.user)
        resp = client.get(self._detail_url())
        notes = resp.data["data"]["case_notes"]
        self.assertEqual(len(notes), 1)
        self.assertFalse(notes[0]["is_internal"])

    def test_staff_sees_all_notes(self):
        client = auth_client(self.staff)
        resp = client.get(self._detail_url())
        notes = resp.data["data"]["case_notes"]
        self.assertEqual(len(notes), 2)

    def test_other_user_denied(self):
        other = create_user(email="other2@example.com", username="other2")
        client = auth_client(other)
        resp = client.get(self._detail_url())
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ─── UPLOAD EVIDENCE TESTS ────────────────────────────────────────────────────

class UploadEvidenceAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.staff = create_staff()
        self.complaint = create_complaint(complainant=self.user)

    def _upload_url(self, pk=None):
        return reverse("complaints:upload-evidence", kwargs={"pk": pk or self.complaint.pk})

    def test_owner_uploads_evidence(self):
        client = auth_client(self.user)
        resp = client.post(
            self._upload_url(),
            {"name": "Screenshot", "file": dummy_pdf()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ComplaintDocument.objects.filter(complaint=self.complaint).count(), 1)

    def test_staff_uploads_evidence(self):
        client = auth_client(self.staff)
        resp = client.post(
            self._upload_url(),
            {"name": "Investigation doc", "file": dummy_pdf()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_upload_to_closed_complaint_rejected(self):
        self.complaint.status = ComplaintStatus.CLOSED
        self.complaint.save()
        client = auth_client(self.user)
        resp = client.post(
            self._upload_url(),
            {"name": "Late evidence", "file": dummy_pdf()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_rejected(self):
        resp = self.client.post(
            self._upload_url(),
            {"name": "Test", "file": dummy_pdf()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── ASSIGN COMPLAINT TESTS ───────────────────────────────────────────────────

class AssignComplaintAPITests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        self.complaint = create_complaint()

    def _assign_url(self, pk=None):
        return reverse("complaints:assign", kwargs={"pk": pk or self.complaint.pk})

    @patch("complaints.views.send_complaint_status_email.delay")
    def test_assign_to_staff(self, mock_email):
        client = auth_client(self.staff)
        resp = client.patch(
            self._assign_url(),
            {"assigned_to": str(self.staff.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.assigned_to, self.staff)
        self.assertEqual(self.complaint.status, ComplaintStatus.ASSIGNED)
        mock_email.assert_called_once()

    def test_assign_non_staff_fails(self):
        citizen = create_user(email="c2@example.com", username="c2")
        client = auth_client(self.staff)
        resp = client.patch(
            self._assign_url(),
            {"assigned_to": str(citizen.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_citizen_cannot_assign(self):
        citizen = create_user(email="c3@example.com", username="c3")
        client = auth_client(citizen)
        resp = client.patch(
            self._assign_url(),
            {"assigned_to": str(self.staff.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @patch("complaints.views.send_complaint_status_email.delay")
    def test_assign_already_assigned_updates_handler(self, mock_email):
        """Re-assigning changes the handler but doesn't re-transition."""
        self.complaint.transition_status(ComplaintStatus.ASSIGNED, self.staff)
        staff2 = create_staff(email="staff2@bocra.bw", username="staff2")
        client = auth_client(self.staff)
        resp = client.patch(
            self._assign_url(),
            {"assigned_to": str(staff2.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.assigned_to, staff2)


# ─── UPDATE STATUS TESTS ──────────────────────────────────────────────────────

class UpdateStatusAPITests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        self.complaint = create_complaint()
        # Move to ASSIGNED so we can test transitions
        self.complaint.transition_status(ComplaintStatus.ASSIGNED, self.staff)

    def _status_url(self, pk=None):
        return reverse("complaints:update-status", kwargs={"pk": pk or self.complaint.pk})

    @patch("complaints.views.send_complaint_status_email.delay")
    def test_valid_transition(self, mock_email):
        client = auth_client(self.staff)
        resp = client.patch(
            self._status_url(),
            {"status": "INVESTIGATING", "reason": "Starting investigation."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, ComplaintStatus.INVESTIGATING)
        mock_email.assert_called_once()

    def test_invalid_transition_rejected(self):
        client = auth_client(self.staff)
        resp = client.patch(
            self._status_url(),
            {"status": "CLOSED"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_citizen_cannot_update_status(self):
        citizen = create_user(email="c4@example.com", username="c4")
        client = auth_client(citizen)
        resp = client.patch(
            self._status_url(),
            {"status": "INVESTIGATING"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── ADD CASE NOTE TESTS ──────────────────────────────────────────────────────

class AddCaseNoteAPITests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        self.complaint = create_complaint()

    def _notes_url(self, pk=None):
        return reverse("complaints:add-note", kwargs={"pk": pk or self.complaint.pk})

    def test_staff_adds_internal_note(self):
        client = auth_client(self.staff)
        resp = client.post(
            self._notes_url(),
            {"content": "Contacted operator.", "is_internal": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["data"]["is_internal"])
        self.assertEqual(CaseNote.objects.filter(complaint=self.complaint).count(), 1)

    def test_staff_adds_public_note(self):
        client = auth_client(self.staff)
        resp = client.post(
            self._notes_url(),
            {"content": "Update for complainant.", "is_internal": False},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(resp.data["data"]["is_internal"])

    def test_citizen_cannot_add_note(self):
        citizen = create_user(email="c5@example.com", username="c5")
        client = auth_client(citizen)
        resp = client.post(
            self._notes_url(),
            {"content": "Not allowed."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── RESOLVE COMPLAINT TESTS ──────────────────────────────────────────────────

class ResolveComplaintAPITests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        self.complaint = create_complaint()
        # Move through to INVESTIGATING so we can resolve
        self.complaint.transition_status(ComplaintStatus.ASSIGNED, self.staff)
        self.complaint.transition_status(ComplaintStatus.INVESTIGATING, self.staff)

    def _resolve_url(self, pk=None):
        return reverse("complaints:resolve", kwargs={"pk": pk or self.complaint.pk})

    @patch("complaints.views.send_complaint_status_email.delay")
    def test_resolve_success(self, mock_email):
        client = auth_client(self.staff)
        resp = client.post(
            self._resolve_url(),
            {"resolution": "Issue resolved after contacting operator."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, ComplaintStatus.RESOLVED)
        self.assertIsNotNone(self.complaint.resolved_at)
        self.assertIn("resolved", self.complaint.resolution.lower())
        mock_email.assert_called_once()

    def test_resolve_wrong_status_rejected(self):
        # Reset to SUBMITTED — can't resolve from here
        self.complaint.status = ComplaintStatus.SUBMITTED
        self.complaint.save()
        client = auth_client(self.staff)
        resp = client.post(
            self._resolve_url(),
            {"resolution": "Trying to resolve prematurely."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resolve_requires_resolution_text(self):
        client = auth_client(self.staff)
        resp = client.post(self._resolve_url(), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── STAFF COMPLAINT LIST TESTS ───────────────────────────────────────────────

class StaffComplaintListAPITests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        create_complaint()
        create_complaint(
            complainant_email="another@example.com",
            subject="Billing issue",
            category=ComplaintCategory.BILLING,
        )

    def test_staff_sees_all(self):
        client = auth_client(self.staff)
        resp = client.get(STAFF_LIST_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 2)

    def test_citizen_denied(self):
        citizen = create_user(email="c6@example.com", username="c6")
        client = auth_client(citizen)
        resp = client.get(STAFF_LIST_URL)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_category(self):
        client = auth_client(self.staff)
        resp = client.get(STAFF_LIST_URL, {"category": "BILLING"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["category"], "BILLING")


# ─── STAFF COMPLAINT DETAIL TESTS ─────────────────────────────────────────────

class StaffComplaintDetailAPITests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        self.complaint = create_complaint()
        CaseNote.objects.create(
            complaint=self.complaint, author=self.staff,
            content="Internal note.", is_internal=True,
        )
        CaseNote.objects.create(
            complaint=self.complaint, author=self.staff,
            content="Public note.", is_internal=False,
        )

    def _staff_detail_url(self, pk=None):
        return reverse("complaints:staff-detail", kwargs={"pk": pk or self.complaint.pk})

    def test_staff_sees_full_detail(self):
        client = auth_client(self.staff)
        resp = client.get(self._staff_detail_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["reference_number"], self.complaint.reference_number)

    def test_staff_sees_all_notes_including_internal(self):
        client = auth_client(self.staff)
        resp = client.get(self._staff_detail_url())
        notes = resp.data["data"]["case_notes"]
        self.assertEqual(len(notes), 2)

    def test_citizen_denied(self):
        citizen = create_user(email="c7@example.com", username="c7")
        client = auth_client(citizen)
        resp = client.get(self._staff_detail_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

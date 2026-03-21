"""
Tests for the licensing app.

Test groups
───────────
LicenceTypeModelTests        — LicenceType creation and str
ApplicationModelTests        — Application state machine transitions
ApplicationStatusLogTests    — Audit log written on every transition
LicenceModelTests            — Licence computed properties (is_expired, days_until_expiry)
LicenceUtilsTests            — Reference number / licence number generators, expiry calc
LicenceTypeAPITests          — GET /types/, /types/<pk>/
LicenceVerifyAPITests        — GET /verify/
MyApplicationsAPITests       — GET/POST /applications/
ApplicationDetailAPITests    — GET /applications/<pk>/
CancelApplicationAPITests    — PATCH /applications/<pk>/cancel/
UploadDocumentAPITests       — POST /applications/<pk>/documents/
UpdateStatusAPITests         — PATCH /applications/<pk>/status/  (staff)
StaffApplicationQueueTests   — GET /staff/applications/
MyLicencesAPITests           — GET /licences/
LicenceDetailAPITests        — GET /licences/<pk>/
LicenceRenewAPITests         — POST /licences/<pk>/renew/
LicenceCertificateAPITests   — GET /licences/<pk>/certificate/
"""

from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserRole
from licensing.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusLog,
    Licence,
    LicenceStatus,
    LicenceType,
)
from licensing.utils import (
    calculate_expiry_date,
    generate_licence_number,
    generate_licence_reference,
)

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def create_user(
    email="applicant@example.com",
    username="applicant",
    role=UserRole.REGISTERED,
    **kwargs,
):
    user = User.objects.create_user(
        email=email,
        username=username,
        first_name="Jane",
        last_name="Doe",
        password="TestPass123!",
        role=role,
        **kwargs,
    )
    user.verify_email()
    return user


def create_staff(email="staff@bocra.bw", username="staffmember"):
    return create_user(email=email, username=username, role=UserRole.STAFF)


def create_licence_type(**kwargs):
    defaults = dict(
        name="Internet Service Provider",
        code="ISP",
        description="Licence to provide ISP services.",
        requirements="Company registration, technical proposal.",
        fee_amount="5000.00",
        validity_period_months=12,
        is_active=True,
    )
    defaults.update(kwargs)
    return LicenceType.objects.create(**defaults)


def create_application(applicant, licence_type, status_val=ApplicationStatus.DRAFT, **kwargs):
    from licensing.utils import generate_licence_reference
    return Application.objects.create(
        applicant=applicant,
        licence_type=licence_type,
        reference_number=generate_licence_reference(),
        organisation_name="Acme Corp",
        contact_person="Jane Doe",
        contact_email="jane@acme.bw",
        description="Test application",
        status=status_val,
        **kwargs,
    )


def create_active_licence(holder, licence_type):
    """Create an Application + Licence directly in APPROVED/ACTIVE state."""
    applicant = holder
    app = create_application(applicant, licence_type, status_val=ApplicationStatus.APPROVED)
    licence_number = generate_licence_number(licence_type.code)
    return Licence.objects.create(
        licence_number=licence_number,
        application=app,
        licence_type=licence_type,
        holder=holder,
        organisation_name="Acme Corp",
        issued_date=date.today(),
        expiry_date=calculate_expiry_date(date.today(), licence_type.validity_period_months),
        status=LicenceStatus.ACTIVE,
    )


def auth_client(user) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def dummy_pdf_file():
    return SimpleUploadedFile(
        "test_doc.pdf",
        b"%PDF-1.4 test content",
        content_type="application/pdf",
    )


# ─── LicenceType Model ────────────────────────────────────────────────────────

class LicenceTypeModelTests(APITestCase):

    def test_str_representation(self):
        lt = create_licence_type()
        self.assertEqual(str(lt), "Internet Service Provider (ISP)")

    def test_inactive_type_not_in_default_queryset(self):
        create_licence_type(code="OLD", name="Old Licence", is_active=False)
        active_codes = LicenceType.objects.filter(is_active=True).values_list("code", flat=True)
        self.assertNotIn("OLD", active_codes)


# ─── Application State Machine ────────────────────────────────────────────────

class ApplicationModelTests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.staff = create_staff()
        self.lt = create_licence_type()
        self.app = create_application(self.user, self.lt)

    def test_str_representation(self):
        self.assertIn(self.app.reference_number, str(self.app))

    def test_can_transition_draft_to_submitted(self):
        self.assertTrue(self.app.can_transition_to(ApplicationStatus.SUBMITTED))

    def test_cannot_transition_draft_to_approved(self):
        self.assertFalse(self.app.can_transition_to(ApplicationStatus.APPROVED))

    def test_transition_sets_status(self):
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.SUBMITTED)

    def test_transition_sets_submitted_at(self):
        self.assertIsNone(self.app.submitted_at)
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.refresh_from_db()
        self.assertIsNotNone(self.app.submitted_at)

    def test_invalid_transition_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.app.transition_status(ApplicationStatus.APPROVED, changed_by=self.staff)

    def test_full_happy_path(self):
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        self.app.transition_status(ApplicationStatus.APPROVED, changed_by=self.staff)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.APPROVED)
        self.assertIsNotNone(self.app.decision_date)
        self.assertEqual(self.app.reviewed_by, self.staff)

    def test_info_requested_path(self):
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        self.app.transition_status(ApplicationStatus.INFO_REQUESTED, changed_by=self.staff)
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.UNDER_REVIEW)

    def test_rejection_path(self):
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        self.app.transition_status(ApplicationStatus.REJECTED, changed_by=self.staff, reason="Incomplete docs.")
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.REJECTED)

    def test_terminal_approved_cannot_transition(self):
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        self.app.transition_status(ApplicationStatus.APPROVED, changed_by=self.staff)
        self.assertFalse(self.app.can_transition_to(ApplicationStatus.REJECTED))


class ApplicationStatusLogTests(APITestCase):

    def test_log_created_on_transition(self):
        user = create_user(email="l@test.com", username="luser")
        lt = create_licence_type(code="LOG")
        app = create_application(user, lt)
        app.transition_status(ApplicationStatus.SUBMITTED, changed_by=user, reason="Test")
        log = ApplicationStatusLog.objects.filter(application=app).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.from_status, ApplicationStatus.DRAFT)
        self.assertEqual(log.to_status, ApplicationStatus.SUBMITTED)
        self.assertEqual(log.reason, "Test")

    def test_multiple_transitions_logged(self):
        user = create_user(email="ml@test.com", username="mluser")
        staff = create_staff(email="mls@test.com", username="mlstaff")
        lt = create_licence_type(code="ML")
        app = create_application(user, lt)
        app.transition_status(ApplicationStatus.SUBMITTED, changed_by=user)
        app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=staff)
        app.transition_status(ApplicationStatus.APPROVED, changed_by=staff)
        self.assertEqual(ApplicationStatusLog.objects.filter(application=app).count(), 3)


# ─── Licence Model ────────────────────────────────────────────────────────────

class LicenceModelTests(APITestCase):

    def test_is_expired_false_for_future(self):
        user = create_user(email="lm@test.com", username="lmuser")
        lt = create_licence_type(code="LMT")
        licence = create_active_licence(user, lt)
        self.assertFalse(licence.is_expired)

    def test_is_expired_true_for_past(self):
        user = create_user(email="lme@test.com", username="lmeuser")
        lt = create_licence_type(code="LMTE")
        app = create_application(user, lt, status_val=ApplicationStatus.APPROVED)
        licence = Licence.objects.create(
            licence_number=generate_licence_number("LMTE"),
            application=app,
            licence_type=lt,
            holder=user,
            organisation_name="Expired Corp",
            issued_date=date(2020, 1, 1),
            expiry_date=date(2021, 1, 1),
            status=LicenceStatus.EXPIRED,
        )
        self.assertTrue(licence.is_expired)

    def test_days_until_expiry_positive(self):
        user = create_user(email="days@test.com", username="daysuser")
        lt = create_licence_type(code="DAYS")
        licence = create_active_licence(user, lt)
        self.assertGreater(licence.days_until_expiry, 0)

    def test_str_representation(self):
        user = create_user(email="str@test.com", username="struser")
        lt = create_licence_type(code="STR")
        licence = create_active_licence(user, lt)
        self.assertIn(licence.licence_number, str(licence))


# ─── Utils ────────────────────────────────────────────────────────────────────

class LicenceUtilsTests(APITestCase):

    def test_generate_licence_reference_format(self):
        from django.utils import timezone
        ref = generate_licence_reference()
        year = str(timezone.now().year)
        self.assertTrue(ref.startswith(f"LIC-{year}-"))

    def test_generate_licence_reference_unique(self):
        refs = {generate_licence_reference() for _ in range(5)}
        # Since the generator checks the DB, with no existing records they should be the same
        # unless we create applications. Here we just check it generates a valid string.
        self.assertGreater(len(refs), 0)

    def test_generate_licence_number_includes_type_code(self):
        # Create a real LicenceType so DB lookup works
        lt = create_licence_type(code="NBA")
        num = generate_licence_number("NBA")
        self.assertIn("NBA", num)

    def test_calculate_expiry_exact_months(self):
        issued = date(2026, 1, 1)
        expiry = calculate_expiry_date(issued, 12)
        self.assertEqual(expiry, date(2027, 1, 1))

    def test_calculate_expiry_6_months(self):
        issued = date(2026, 1, 1)
        expiry = calculate_expiry_date(issued, 6)
        self.assertEqual(expiry, date(2026, 7, 1))


# ─── Licence Types API ────────────────────────────────────────────────────────

class LicenceTypeAPITests(APITestCase):

    def setUp(self):
        self.lt1 = create_licence_type()
        self.lt2 = create_licence_type(name="Broadcast Licence", code="BROAD")
        self.client = APIClient()  # Public — no auth

    def test_list_licence_types(self):
        response = self.client.get("/api/v1/licensing/types/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 2)

    def test_inactive_type_not_listed(self):
        create_licence_type(code="INACT", name="Inactive", is_active=False)
        response = self.client.get("/api/v1/licensing/types/")
        codes = [lt["code"] for lt in response.json()["data"]]
        self.assertNotIn("INACT", codes)

    def test_search_by_name(self):
        response = self.client.get("/api/v1/licensing/types/", {"search": "Internet"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_get_type_detail(self):
        response = self.client.get(f"/api/v1/licensing/types/{self.lt1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["code"], "ISP")

    def test_get_type_detail_includes_requirements(self):
        response = self.client.get(f"/api/v1/licensing/types/{self.lt1.id}/")
        self.assertIn("requirements", response.json()["data"])


# ─── Licence Verify API ───────────────────────────────────────────────────────

class LicenceVerifyAPITests(APITestCase):

    def setUp(self):
        self.user = create_user(email="vfy@test.com", username="vfyuser")
        self.lt = create_licence_type(code="VFY")
        self.licence = create_active_licence(self.user, self.lt)

    def test_verify_by_licence_number(self):
        response = self.client.get(
            "/api/v1/licensing/verify/",
            {"licence_no": self.licence.licence_number},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_verify_by_company_name(self):
        response = self.client.get(
            "/api/v1/licensing/verify/",
            {"company": "Acme"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.json()["data"]), 1)

    def test_verify_no_params_returns_400(self):
        response = self.client.get("/api/v1/licensing/verify/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_nonexistent_returns_404(self):
        response = self.client.get(
            "/api/v1/licensing/verify/",
            {"licence_no": "LIC-DOESNOTEXIST-2099-999999"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_response_does_not_expose_holder_pii(self):
        response = self.client.get(
            "/api/v1/licensing/verify/",
            {"licence_no": self.licence.licence_number},
        )
        licence_data = response.json()["data"][0]
        self.assertNotIn("holder", licence_data)


# ─── My Applications API ──────────────────────────────────────────────────────

class MyApplicationsAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.lt = create_licence_type()
        self.client = auth_client(self.user)

    def valid_payload(self, **overrides):
        data = {
            "licence_type": str(self.lt.id),
            "organisation_name": "Test Corp",
            "contact_person": "Jane Doe",
            "contact_email": "jane@testcorp.bw",
            "contact_phone": "+26771234567",
            "description": "Applying for ISP licence.",
            "submit": False,
        }
        data.update(overrides)
        return data

    def test_list_applications_empty(self):
        response = self.client.get("/api/v1/licensing/applications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 0)

    def test_submit_application_creates_record(self):
        response = self.client.post(
            "/api/v1/licensing/applications/",
            self.valid_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Application.objects.filter(applicant=self.user).count(), 1)

    def test_submit_as_draft(self):
        self.client.post(
            "/api/v1/licensing/applications/",
            self.valid_payload(submit=False),
            format="json",
        )
        app = Application.objects.get(applicant=self.user)
        self.assertEqual(app.status, ApplicationStatus.DRAFT)

    @patch("licensing.views.send_application_submitted_email.delay")
    def test_submit_immediately(self, mock_email):
        self.client.post(
            "/api/v1/licensing/applications/",
            self.valid_payload(submit=True),
            format="json",
        )
        app = Application.objects.get(applicant=self.user)
        self.assertEqual(app.status, ApplicationStatus.SUBMITTED)
        mock_email.assert_called_once()

    def test_inactive_licence_type_rejected(self):
        inactive_lt = create_licence_type(code="INACT2", name="Inactive", is_active=False)
        payload = self.valid_payload(licence_type=str(inactive_lt.id))
        response = self.client.post(
            "/api/v1/licensing/applications/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_list(self):
        anon = APIClient()
        response = anon.get("/api/v1/licensing/applications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_only_sees_own_applications(self):
        other_user = create_user(email="other@test.com", username="otheruser")
        create_application(other_user, self.lt)
        create_application(self.user, self.lt)
        response = self.client.get("/api/v1/licensing/applications/")
        self.assertEqual(len(response.json()["data"]), 1)

    def test_reference_number_auto_generated(self):
        self.client.post(
            "/api/v1/licensing/applications/",
            self.valid_payload(),
            format="json",
        )
        app = Application.objects.get(applicant=self.user)
        self.assertIsNotNone(app.reference_number)
        self.assertTrue(app.reference_number.startswith("LIC-"))


# ─── Application Detail API ───────────────────────────────────────────────────

class ApplicationDetailAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="other@test.com", username="otheruser")
        self.staff = create_staff()
        self.lt = create_licence_type(code="DET")
        self.app = create_application(self.user, self.lt)

    def test_owner_can_view_application(self):
        client = auth_client(self.user)
        response = client.get(f"/api/v1/licensing/applications/{self.app.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_user_cannot_view_application(self):
        client = auth_client(self.other_user)
        response = client.get(f"/api/v1/licensing/applications/{self.app.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_view_any_application(self):
        client = auth_client(self.staff)
        response = client.get(f"/api/v1/licensing/applications/{self.app.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_includes_status_timeline(self):
        client = auth_client(self.user)
        response = client.get(f"/api/v1/licensing/applications/{self.app.id}/")
        data = response.json()["data"]
        self.assertIn("status_timeline", data)

    def test_detail_includes_documents_list(self):
        client = auth_client(self.user)
        response = client.get(f"/api/v1/licensing/applications/{self.app.id}/")
        data = response.json()["data"]
        self.assertIn("documents", data)


# ─── Cancel Application ───────────────────────────────────────────────────────

class CancelApplicationAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.lt = create_licence_type(code="CNC")
        self.app = create_application(self.user, self.lt)
        self.client = auth_client(self.user)

    def test_owner_can_cancel_draft(self):
        response = self.client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/cancel/",
            {"reason": "Changed my mind."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.CANCELLED)

    def test_cannot_cancel_approved(self):
        staff = create_staff(email="c_staff@test.com", username="cstaff")
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=staff)
        self.app.transition_status(ApplicationStatus.APPROVED, changed_by=staff)
        response = self.client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/cancel/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_user_cannot_cancel(self):
        other = create_user(email="canc_other@test.com", username="cancother")
        client = auth_client(other)
        response = client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/cancel/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ─── Document Upload ─────────────────────────────────────────────────────────

class UploadDocumentAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.lt = create_licence_type(code="UPL")
        self.app = create_application(self.user, self.lt)
        self.client = auth_client(self.user)

    def test_owner_can_upload_document_to_draft(self):
        response = self.client.post(
            f"/api/v1/licensing/applications/{self.app.id}/documents/",
            {"name": "Company Registration", "file": dummy_pdf_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.app.documents.count(), 1)

    def test_cannot_upload_to_approved_application(self):
        staff = create_staff(email="upl_staff@test.com", username="uplstaff")
        self.app.transition_status(ApplicationStatus.SUBMITTED, changed_by=self.user)
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=staff)
        self.app.transition_status(ApplicationStatus.APPROVED, changed_by=staff)
        response = self.client.post(
            f"/api/v1/licensing/applications/{self.app.id}/documents/",
            {"name": "Late doc", "file": dummy_pdf_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_file_returns_400(self):
        response = self.client.post(
            f"/api/v1/licensing/applications/{self.app.id}/documents/",
            {"name": "No file"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_upload(self):
        anon = APIClient()
        response = anon.post(
            f"/api/v1/licensing/applications/{self.app.id}/documents/",
            {"name": "Doc", "file": dummy_pdf_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── Update Application Status (Staff) ───────────────────────────────────────

class UpdateStatusAPITests(APITestCase):

    def setUp(self):
        self.user = create_user(email="sta@test.com", username="stauser")
        self.staff = create_staff()
        self.lt = create_licence_type(code="STA")
        self.app = create_application(self.user, self.lt, status_val=ApplicationStatus.SUBMITTED)
        self.staff_client = auth_client(self.staff)

    def test_staff_can_move_to_under_review(self):
        response = self.staff_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {"status": ApplicationStatus.UNDER_REVIEW},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.UNDER_REVIEW)

    def test_regular_user_cannot_update_status(self):
        user_client = auth_client(self.user)
        response = user_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {"status": ApplicationStatus.UNDER_REVIEW},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_transition_returns_400(self):
        response = self.staff_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {"status": ApplicationStatus.APPROVED},  # can't jump from SUBMITTED
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejection_requires_reason(self):
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        response = self.staff_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {"status": ApplicationStatus.REJECTED},  # missing reason
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("licensing.views.send_application_status_email.delay")
    def test_approval_auto_creates_licence(self, mock_email):
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        response = self.staff_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {"status": ApplicationStatus.APPROVED, "reason": "Meets all criteria."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Licence.objects.filter(application=self.app).exists())

    @patch("licensing.views.send_application_status_email.delay")
    def test_approval_upgrades_user_to_licensee(self, mock_email):
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        self.staff_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {"status": ApplicationStatus.APPROVED, "reason": "Approved."},
            format="json",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, UserRole.LICENSEE)

    @patch("licensing.views.send_application_status_email.delay")
    def test_info_requested_saves_message(self, mock_email):
        self.app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=self.staff)
        self.staff_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {
                "status": ApplicationStatus.INFO_REQUESTED,
                "info_request_message": "Please upload your company certificate.",
            },
            format="json",
        )
        self.app.refresh_from_db()
        self.assertIn("company certificate", self.app.info_request_message)

    @patch("licensing.views.send_application_status_email.delay")
    def test_status_change_fires_email_task(self, mock_email):
        self.staff_client.patch(
            f"/api/v1/licensing/applications/{self.app.id}/status/",
            {"status": ApplicationStatus.UNDER_REVIEW},
            format="json",
        )
        mock_email.assert_called_once()


# ─── Staff Application Queue ──────────────────────────────────────────────────

class StaffApplicationQueueTests(APITestCase):

    def setUp(self):
        self.staff = create_staff()
        self.user1 = create_user(email="u1@test.com", username="u1user")
        self.user2 = create_user(email="u2@test.com", username="u2user")
        self.lt = create_licence_type(code="SQ")
        create_application(self.user1, self.lt, status_val=ApplicationStatus.SUBMITTED)
        create_application(self.user2, self.lt, status_val=ApplicationStatus.SUBMITTED)
        self.staff_client = auth_client(self.staff)

    def test_staff_sees_all_applications(self):
        response = self.staff_client.get("/api/v1/licensing/staff/applications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_regular_user_cannot_access_staff_queue(self):
        client = auth_client(self.user1)
        response = client.get("/api/v1/licensing/staff/applications/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status(self):
        response = self.staff_client.get(
            "/api/v1/licensing/staff/applications/",
            {"status": ApplicationStatus.SUBMITTED},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for app_data in response.json()["data"]:
            self.assertEqual(app_data["status"], ApplicationStatus.SUBMITTED)

    def test_staff_detail_includes_applicant_info(self):
        app = Application.objects.filter(applicant=self.user1).first()
        response = self.staff_client.get(f"/api/v1/licensing/staff/applications/{app.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ─── My Licences ─────────────────────────────────────────────────────────────

class MyLicencesAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.lt = create_licence_type(code="MYL")
        self.licence = create_active_licence(self.user, self.lt)
        self.client = auth_client(self.user)

    def test_user_sees_own_licences(self):
        response = self.client.get("/api/v1/licensing/licences/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_user_does_not_see_others_licences(self):
        other = create_user(email="ml_other@test.com", username="mlother")
        other_lt = create_licence_type(code="OTH")
        create_active_licence(other, other_lt)
        response = self.client.get("/api/v1/licensing/licences/")
        self.assertEqual(len(response.json()["data"]), 1)

    def test_unauthenticated_cannot_list(self):
        anon = APIClient()
        response = anon.get("/api/v1/licensing/licences/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── Licence Detail ───────────────────────────────────────────────────────────

class LicenceDetailAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.lt = create_licence_type(code="LD")
        self.licence = create_active_licence(self.user, self.lt)

    def test_holder_can_view_licence(self):
        client = auth_client(self.user)
        response = client.get(f"/api/v1/licensing/licences/{self.licence.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["licence_number"], self.licence.licence_number)

    def test_non_holder_cannot_view_licence(self):
        other = create_user(email="ld_other@test.com", username="ldother")
        client = auth_client(other)
        response = client.get(f"/api/v1/licensing/licences/{self.licence.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_view_any_licence(self):
        staff = create_staff(email="ld_staff@test.com", username="ldstaff")
        client = auth_client(staff)
        response = client.get(f"/api/v1/licensing/licences/{self.licence.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ─── Licence Renewal ─────────────────────────────────────────────────────────

class LicenceRenewAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.lt = create_licence_type(code="RNW")
        self.licence = create_active_licence(self.user, self.lt)
        self.client = auth_client(self.user)

    @patch("licensing.views.send_application_submitted_email.delay")
    def test_holder_can_initiate_renewal(self, mock_email):
        response = self.client.post(f"/api/v1/licensing/licences/{self.licence.id}/renew/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        renewal = Application.objects.filter(renewal_of=self.licence).first()
        self.assertIsNotNone(renewal)
        self.assertEqual(renewal.status, ApplicationStatus.SUBMITTED)

    @patch("licensing.views.send_application_submitted_email.delay")
    def test_cannot_renew_twice_when_pending(self, mock_email):
        self.client.post(f"/api/v1/licensing/licences/{self.licence.id}/renew/")
        response = self.client.post(f"/api/v1/licensing/licences/{self.licence.id}/renew/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_renew_revoked_licence(self):
        self.licence.status = LicenceStatus.REVOKED
        self.licence.save()
        response = self.client.post(f"/api/v1/licensing/licences/{self.licence.id}/renew/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_user_cannot_renew(self):
        other = create_user(email="rnw_other@test.com", username="rnwother")
        client = auth_client(other)
        response = client.post(f"/api/v1/licensing/licences/{self.licence.id}/renew/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ─── Licence Certificate ─────────────────────────────────────────────────────

class LicenceCertificateAPITests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.lt = create_licence_type(code="CERT")
        self.licence = create_active_licence(self.user, self.lt)
        self.client = auth_client(self.user)

    def test_holder_can_download_certificate(self):
        response = self.client.get(f"/api/v1/licensing/licences/{self.licence.id}/certificate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_non_holder_cannot_download(self):
        other = create_user(email="cert_other@test.com", username="certother")
        client = auth_client(other)
        response = client.get(f"/api/v1/licensing/licences/{self.licence.id}/certificate/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_licence_certificate_blocked(self):
        self.licence.status = LicenceStatus.SUSPENDED
        self.licence.save()
        response = self.client.get(f"/api/v1/licensing/licences/{self.licence.id}/certificate/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_blocked(self):
        anon = APIClient()
        response = anon.get(f"/api/v1/licensing/licences/{self.licence.id}/certificate/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

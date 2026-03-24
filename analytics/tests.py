"""
Tests for the analytics app.

Test groups
───────────
NetworkOperatorModelTests       — Operator model str, active filter
TelecomsStatModelTests          — Stat model str, unique constraint
QoSRecordModelTests             — QoS meets_benchmark logic
OperatorListAPITests            — GET /telecoms/operators/
TelecomsOverviewAPITests        — GET /telecoms/overview/
QoSListAPITests                 — GET /qos/
QoSByOperatorAPITests           — GET /qos/by-operator/          (staff)
ComplaintsSummaryAPITests       — GET /complaints/summary/       (staff)
LicensingSummaryAPITests        — GET /licensing/summary/        (staff)
PublicDashboardAPITests         — GET /dashboard/public/
StaffDashboardAPITests          — GET /dashboard/staff/          (staff)
UsersSummaryAPITests            — GET /users/summary/            (staff)
ApplicationsTrendAPITests       — GET /applications/trend/       (staff)
ComplaintsTrendAPITests         — GET /complaints/trend/         (staff)
PublicationsSummaryAPITests     — GET /publications/summary/     (staff)
TendersSummaryAPITests          — GET /tenders/summary/          (staff)
NewsSummaryAPITests             — GET /news/summary/             (staff)
ContentOverviewAPITests         — GET /content/overview/         (staff)
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserRole
from analytics.models import (
    MetricType,
    NetworkOperator,
    QoSRecord,
    Technology,
    TelecomsStat,
)

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
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def create_operator(name="Mascom Wireless", code="MASCOM", **kwargs):
    defaults = dict(name=name, code=code, is_active=True)
    defaults.update(kwargs)
    return NetworkOperator.objects.create(**defaults)


def create_stat(operator, period=None, technology=Technology.FOUR_G, **kwargs):
    defaults = dict(
        operator=operator,
        period=period or date(2026, 3, 1),
        technology=technology,
        subscriber_count=500000,
        market_share_percent=Decimal("35.00"),
    )
    defaults.update(kwargs)
    return TelecomsStat.objects.create(**defaults)


def create_qos(operator, period=None, metric_type=MetricType.CALL_SUCCESS, **kwargs):
    defaults = dict(
        operator=operator,
        period=period or date(2026, 3, 1),
        metric_type=metric_type,
        value=Decimal("97.50"),
        unit="%",
        region="Gaborone",
        benchmark=Decimal("95.00"),
    )
    defaults.update(kwargs)
    return QoSRecord.objects.create(**defaults)


# ─── MODEL TESTS ──────────────────────────────────────────────────────────────

class NetworkOperatorModelTests(APITestCase):

    def test_str(self):
        op = create_operator()
        self.assertIn("Mascom", str(op))
        self.assertIn("MASCOM", str(op))

    def test_code_unique(self):
        create_operator()
        with self.assertRaises(IntegrityError):
            create_operator(name="Duplicate", code="MASCOM")


class TelecomsStatModelTests(APITestCase):

    def setUp(self):
        self.op = create_operator()

    def test_str(self):
        stat = create_stat(self.op)
        s = str(stat)
        self.assertIn("MASCOM", s)
        self.assertIn("4G", s)

    def test_unique_together(self):
        create_stat(self.op, period=date(2026, 3, 1), technology=Technology.FOUR_G)
        with self.assertRaises(IntegrityError):
            create_stat(self.op, period=date(2026, 3, 1), technology=Technology.FOUR_G)


class QoSRecordModelTests(APITestCase):

    def setUp(self):
        self.op = create_operator()

    def test_str(self):
        qos = create_qos(self.op)
        self.assertIn("MASCOM", str(qos))

    def test_meets_benchmark_higher_is_better(self):
        qos = create_qos(self.op, metric_type=MetricType.CALL_SUCCESS,
                          value=Decimal("97.50"), benchmark=Decimal("95.00"))
        self.assertTrue(qos.meets_benchmark)

    def test_fails_benchmark_higher_is_better(self):
        qos = create_qos(self.op, metric_type=MetricType.DATA_SPEED,
                          value=Decimal("10.00"), benchmark=Decimal("20.00"))
        self.assertFalse(qos.meets_benchmark)

    def test_meets_benchmark_lower_is_better(self):
        qos = create_qos(self.op, metric_type=MetricType.DROP_RATE,
                          value=Decimal("1.50"), benchmark=Decimal("2.00"))
        self.assertTrue(qos.meets_benchmark)

    def test_fails_benchmark_lower_is_better(self):
        qos = create_qos(self.op, metric_type=MetricType.LATENCY,
                          value=Decimal("50.00"), benchmark=Decimal("30.00"))
        self.assertFalse(qos.meets_benchmark)

    def test_meets_benchmark_none_when_no_benchmark(self):
        qos = create_qos(self.op, benchmark=None)
        self.assertIsNone(qos.meets_benchmark)


# ─── OPERATOR LIST TESTS ──────────────────────────────────────────────────────

class OperatorListAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:telecoms-operators")
        create_operator(name="Mascom", code="MASCOM")
        create_operator(name="Orange", code="ORANGE")
        create_operator(name="Inactive", code="INACTIVE", is_active=False)

    def test_returns_active_operators(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 2)

    def test_public_access(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ─── TELECOMS OVERVIEW TESTS ──────────────────────────────────────────────────

class TelecomsOverviewAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:telecoms-overview")
        self.op1 = create_operator(name="Mascom", code="MASCOM")
        self.op2 = create_operator(name="Orange", code="ORANGE")
        period = date(2026, 3, 1)
        create_stat(self.op1, period=period, technology=Technology.FOUR_G,
                     subscriber_count=800000, market_share_percent=Decimal("50.00"))
        create_stat(self.op2, period=period, technology=Technology.FOUR_G,
                     subscriber_count=400000, market_share_percent=Decimal("25.00"))

    def test_overview_returns_data(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["total_subscribers"], 1200000)

    def test_overview_by_operator(self):
        resp = self.client.get(self.url)
        by_op = resp.data["data"]["by_operator"]
        self.assertEqual(len(by_op), 2)

    def test_date_range_filter(self):
        old_period = date(2025, 1, 1)
        create_stat(self.op1, period=old_period, technology=Technology.THREE_G,
                     subscriber_count=100000)
        resp = self.client.get(self.url, {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["total_subscribers"], 100000)


# ─── QOS LIST TESTS ───────────────────────────────────────────────────────────

class QoSListAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:qos-list")
        self.op = create_operator()
        create_qos(self.op, period=date(2026, 3, 1),
                    metric_type=MetricType.CALL_SUCCESS)
        create_qos(self.op, period=date(2026, 3, 1),
                    metric_type=MetricType.DROP_RATE,
                    value=Decimal("1.20"), unit="%", benchmark=Decimal("2.00"))

    def test_public_access(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 2)

    def test_includes_meets_benchmark(self):
        resp = self.client.get(self.url)
        for record in resp.data["data"]:
            self.assertIn("meets_benchmark", record)


# ─── QOS BY OPERATOR TESTS ────────────────────────────────────────────────────

class QoSByOperatorAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:qos-by-operator")
        self.staff = create_staff()
        op = create_operator()
        create_qos(op, metric_type=MetricType.CALL_SUCCESS)
        create_qos(op, metric_type=MetricType.DATA_SPEED,
                    value=Decimal("25.00"), unit="Mbps", benchmark=Decimal("10.00"))

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data["data"]), 0)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── COMPLAINTS SUMMARY TESTS ─────────────────────────────────────────────────

class ComplaintsSummaryAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:complaints-summary")
        self.staff = create_staff()

        # Create some complaints for aggregation
        from complaints.models import (
            Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus,
        )
        from complaints.utils import generate_complaint_reference
        for i in range(3):
            Complaint.objects.create(
                reference_number=generate_complaint_reference(),
                complainant_name=f"User {i}",
                complainant_email=f"user{i}@example.com",
                against_operator_name="Mascom",
                category=ComplaintCategory.SERVICE_QUALITY,
                subject=f"Complaint {i}",
                description="Test",
                priority=ComplaintPriority.MEDIUM,
                status=ComplaintStatus.SUBMITTED,
                sla_deadline=timezone.now() + timedelta(days=14),
            )
        # One resolved
        Complaint.objects.create(
            reference_number=generate_complaint_reference(),
            complainant_name="Resolved User",
            complainant_email="resolved@example.com",
            against_operator_name="Orange",
            category=ComplaintCategory.BILLING,
            subject="Billing resolved",
            description="Test",
            priority=ComplaintPriority.HIGH,
            status=ComplaintStatus.RESOLVED,
            resolved_at=timezone.now(),
            sla_deadline=timezone.now() + timedelta(days=7),
        )

    def test_staff_gets_summary(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertEqual(data["total"], 4)
        self.assertEqual(data["resolved"], 1)
        self.assertIn("by_status", data)
        self.assertIn("by_category", data)
        self.assertIn("resolution_rate_percent", data)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── LICENSING SUMMARY TESTS ──────────────────────────────────────────────────

class LicensingSummaryAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:licensing-summary")
        self.staff = create_staff()

    def test_staff_gets_summary(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("licences", data)
        self.assertIn("renewals_due", data)
        self.assertIn("applications", data)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── PUBLIC DASHBOARD TESTS ───────────────────────────────────────────────────

class PublicDashboardAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:dashboard-public")
        # Set up some data
        op = create_operator()
        create_stat(op, subscriber_count=1000000)

    def test_public_access(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_expected_keys(self):
        resp = self.client.get(self.url)
        data = resp.data["data"]
        self.assertIn("active_licences", data)
        self.assertIn("total_complaints", data)
        self.assertIn("resolved_complaints", data)
        self.assertIn("total_subscribers", data)
        self.assertIn("active_operators", data)
        self.assertIn("published_publications", data)
        self.assertIn("open_tenders", data)
        self.assertIn("published_articles", data)

    def test_subscriber_count_correct(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["data"]["total_subscribers"], 1000000)


# ─── STAFF DASHBOARD TESTS ────────────────────────────────────────────────────

class StaffDashboardAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:dashboard-staff")
        self.staff = create_staff()
        op = create_operator()
        create_stat(op)

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_all_sections(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("users", data)
        self.assertIn("licensing", data)
        self.assertIn("applications", data)
        self.assertIn("complaints", data)
        self.assertIn("telecoms", data)
        self.assertIn("content", data)
        self.assertIn("notifications", data)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ═══════════════════════════════════════════════════════════════════════════════
#  NEW ANALYTICS ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── USERS SUMMARY ────────────────────────────────────────────────────────────

class UsersSummaryAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:users-summary")
        self.staff = create_staff()
        create_user(email="citizen1@test.bw", username="citizen1", role=UserRole.REGISTERED)
        create_user(email="citizen2@test.bw", username="citizen2", role=UserRole.CITIZEN)

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_expected_keys(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("total", data)
        self.assertIn("by_role", data)
        self.assertIn("email_verified", data)
        self.assertIn("verification_rate_percent", data)
        self.assertIn("locked_accounts", data)
        self.assertIn("new_last_7_days", data)
        self.assertIn("new_last_30_days", data)
        self.assertIn("registration_trend", data)

    def test_total_count(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.data["data"]["total"], 3)

    def test_citizen_denied(self):
        citizen = create_user(email="noaccess@test.bw", username="noaccess")
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── APPLICATIONS TREND ───────────────────────────────────────────────────────

class ApplicationsTrendAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:applications-trend")
        self.staff = create_staff()

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_expected_keys(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("total", data)
        self.assertIn("by_licence_type", data)
        self.assertIn("approved", data)
        self.assertIn("rejected", data)
        self.assertIn("approval_rate_percent", data)
        self.assertIn("avg_processing_days", data)
        self.assertIn("volume_trend", data)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── COMPLAINTS TREND ─────────────────────────────────────────────────────────

class ComplaintsTrendAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:complaints-trend")
        self.staff = create_staff()

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_expected_keys(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("volume_trend", data)
        self.assertIn("resolution_trend", data)
        self.assertIn("top_targeted_operators", data)
        self.assertIn("staff_workload", data)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── PUBLICATIONS SUMMARY ─────────────────────────────────────────────────────

class PublicationsSummaryAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:publications-summary")
        self.staff = create_staff()

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_expected_keys(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("total", data)
        self.assertIn("by_status", data)
        self.assertIn("by_category", data)
        self.assertIn("total_downloads", data)
        self.assertIn("top_downloaded", data)
        self.assertIn("publishing_trend", data)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── TENDERS SUMMARY ──────────────────────────────────────────────────────────

class TendersSummaryAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:tenders-summary")
        self.staff = create_staff()

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_expected_keys(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("total", data)
        self.assertIn("by_status", data)
        self.assertIn("by_category", data)
        self.assertIn("awards", data)
        self.assertIn("volume_trend", data)
        awards = data["awards"]
        self.assertIn("total_awarded", awards)
        self.assertIn("total_amount", awards)
        self.assertIn("avg_amount", awards)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── NEWS SUMMARY ─────────────────────────────────────────────────────────────

class NewsSummaryAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:news-summary")
        self.staff = create_staff()

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_expected_keys(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("total", data)
        self.assertIn("by_status", data)
        self.assertIn("by_category", data)
        self.assertIn("total_views", data)
        self.assertIn("top_viewed", data)
        self.assertIn("publishing_trend", data)

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── CONTENT OVERVIEW ─────────────────────────────────────────────────────────

class ContentOverviewAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("analytics:content-overview")
        self.staff = create_staff()

    def test_staff_access(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_returns_all_content_sections(self):
        client = auth_client(self.staff)
        resp = client.get(self.url)
        data = resp.data["data"]
        self.assertIn("publications", data)
        self.assertIn("tenders", data)
        self.assertIn("news", data)
        for section in ["publications", "tenders", "news"]:
            self.assertIn("total", data[section])

    def test_citizen_denied(self):
        citizen = create_user()
        client = auth_client(citizen)
        resp = client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

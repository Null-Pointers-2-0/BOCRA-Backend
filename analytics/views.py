"""
Analytics / Dashboard API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints (15)
──────────────
GET /api/v1/analytics/dashboard/public/        PublicDashboardView       [Public]
GET /api/v1/analytics/dashboard/staff/         StaffDashboardView        [Staff]
GET /api/v1/analytics/telecoms/overview/       TelecomsOverviewView      [Public]
GET /api/v1/analytics/telecoms/operators/      OperatorListView          [Public]
GET /api/v1/analytics/qos/                     QoSListView               [Public]
GET /api/v1/analytics/qos/by-operator/         QoSByOperatorView         [Staff]
GET /api/v1/analytics/complaints/summary/      ComplaintsSummaryView     [Staff]
GET /api/v1/analytics/complaints/trend/        ComplaintsTrendView       [Staff]
GET /api/v1/analytics/licensing/summary/       LicensingSummaryView      [Staff]
GET /api/v1/analytics/applications/trend/      ApplicationsTrendView     [Staff]
GET /api/v1/analytics/users/summary/           UsersSummaryView          [Staff]
GET /api/v1/analytics/publications/summary/    PublicationsSummaryView   [Staff]
GET /api/v1/analytics/tenders/summary/         TendersSummaryView        [Staff]
GET /api/v1/analytics/news/summary/            NewsSummaryView           [Staff]
GET /api/v1/analytics/content/overview/        ContentOverviewView       [Staff]
"""

import logging
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, Max, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers as drf_serializers

from accounts.permissions import IsStaff
from core.utils import api_error, api_success
from .models import NetworkOperator, QoSRecord, TelecomsStat
from .serializers import (
    NetworkOperatorSerializer,
    QoSRecordSerializer,
    TelecomsStatSerializer,
)

logger = logging.getLogger(__name__)


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def _parse_period_params(request):
    """Extract optional date range from query params."""
    start = request.query_params.get("start_date")
    end = request.query_params.get("end_date")
    start_date = None
    end_date = None
    if start:
        try:
            start_date = date.fromisoformat(start)
        except ValueError:
            pass
    if end:
        try:
            end_date = date.fromisoformat(end)
        except ValueError:
            pass
    return start_date, end_date


# ─── OPERATOR LIST (Public) ───────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Public"], summary="List all network operators")
class OperatorListView(generics.ListAPIView):
    """
    GET /api/v1/analytics/telecoms/operators/

    List all active network operators.
    Auth: Public
    """

    serializer_class = NetworkOperatorSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return NetworkOperator.objects.filter(is_active=True, is_deleted=False)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Operators retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── TELECOMS OVERVIEW (Public) ───────────────────────────────────────────────

@extend_schema(
    tags=["Analytics — Public"],
    summary="Telecoms market overview — subscribers by operator and technology",
    parameters=[
        OpenApiParameter("start_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("end_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
    ],
)
class TelecomsOverviewView(APIView):
    """
    GET /api/v1/analytics/telecoms/overview/

    Aggregated telecoms market data. Supports optional date range filtering.
    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = TelecomsStatSerializer

    def get(self, request):
        start_date, end_date = _parse_period_params(request)

        qs = TelecomsStat.objects.filter(
            is_deleted=False, operator__is_active=True
        ).select_related("operator")

        if start_date:
            qs = qs.filter(period__gte=start_date)
        if end_date:
            qs = qs.filter(period__lte=end_date)

        # Get the latest period stats if no filter
        if not start_date and not end_date:
            latest_period = qs.order_by("-period").values_list("period", flat=True).first()
            if latest_period:
                qs = qs.filter(period=latest_period)

        # Aggregate by operator
        by_operator = (
            qs.values("operator__name", "operator__code")
            .annotate(
                total_subscribers=Sum("subscriber_count"),
                avg_market_share=Avg("market_share_percent"),
            )
            .order_by("-total_subscribers")
        )

        # Aggregate by technology
        by_technology = (
            qs.values("technology")
            .annotate(total_subscribers=Sum("subscriber_count"))
            .order_by("technology")
        )

        # Total
        total = qs.aggregate(total_subscribers=Sum("subscriber_count"))

        data = {
            "total_subscribers": total["total_subscribers"] or 0,
            "by_operator": list(by_operator),
            "by_technology": list(by_technology),
            "period": str(qs.order_by("-period").values_list("period", flat=True).first()) if qs.exists() else None,
        }

        return Response(
            api_success(data, "Telecoms overview retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── QOS LIST (Public) ────────────────────────────────────────────────────────

@extend_schema(
    tags=["Analytics — Public"],
    summary="Quality of Service metrics (latest period)",
    parameters=[
        OpenApiParameter("start_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("end_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
    ],
)
class QoSListView(generics.ListAPIView):
    """
    GET /api/v1/analytics/qos/

    List QoS records. Defaults to latest reporting period.
    Auth: Public
    """

    serializer_class = QoSRecordSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["metric_type", "operator"]
    ordering_fields = ["period", "value", "metric_type"]
    ordering = ["-period"]

    def get_queryset(self):
        qs = QoSRecord.objects.filter(
            is_deleted=False, operator__is_active=True
        ).select_related("operator")

        start_date, end_date = _parse_period_params(self.request)
        if start_date:
            qs = qs.filter(period__gte=start_date)
        if end_date:
            qs = qs.filter(period__lte=end_date)

        # Default to latest period
        if not start_date and not end_date:
            latest = qs.order_by("-period").values_list("period", flat=True).first()
            if latest:
                qs = qs.filter(period=latest)

        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "QoS records retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── QOS BY OPERATOR (Staff) ──────────────────────────────────────────────────

@extend_schema(
    tags=["Analytics — Staff"],
    summary="Detailed QoS breakdown per operator (staff)",
    parameters=[
        OpenApiParameter("start_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("end_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
    ],
    responses={200: OpenApiTypes.OBJECT},
)
class QoSByOperatorView(APIView):
    """
    GET /api/v1/analytics/qos/by-operator/

    Detailed QoS grouped by operator with averages.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        start_date, end_date = _parse_period_params(request)

        qs = QoSRecord.objects.filter(
            is_deleted=False, operator__is_active=True
        ).select_related("operator")

        if start_date:
            qs = qs.filter(period__gte=start_date)
        if end_date:
            qs = qs.filter(period__lte=end_date)

        by_operator = (
            qs.values("operator__name", "operator__code", "metric_type")
            .annotate(
                avg_value=Avg("value"),
                record_count=Count("id"),
            )
            .order_by("operator__name", "metric_type")
        )

        return Response(
            api_success(list(by_operator), "QoS by operator retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── COMPLAINTS SUMMARY (Staff) ───────────────────────────────────────────────

@extend_schema(tags=["Analytics — Staff"], summary="Complaint analytics summary (staff)", responses={200: OpenApiTypes.OBJECT})
class ComplaintsSummaryView(APIView):
    """
    GET /api/v1/analytics/complaints/summary/

    Aggregate complaint stats — volume, by category, resolution rates, SLA.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from complaints.models import Complaint, ComplaintStatus

        all_complaints = Complaint.objects.filter(is_deleted=False)

        total = all_complaints.count()
        by_status = dict(
            all_complaints.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        by_category = dict(
            all_complaints.values_list("category")
            .annotate(count=Count("id"))
            .values_list("category", "count")
        )
        by_priority = dict(
            all_complaints.values_list("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        )

        # Open complaints
        open_statuses = [
            ComplaintStatus.SUBMITTED, ComplaintStatus.ASSIGNED,
            ComplaintStatus.INVESTIGATING, ComplaintStatus.AWAITING_RESPONSE,
            ComplaintStatus.REOPENED,
        ]
        open_count = all_complaints.filter(status__in=open_statuses).count()

        # SLA overdue
        overdue_count = all_complaints.filter(
            status__in=open_statuses,
            sla_deadline__lt=timezone.now(),
        ).count()

        # Resolution stats
        resolved = all_complaints.filter(
            status__in=[ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]
        )
        resolved_count = resolved.count()
        resolution_rate = round((resolved_count / total * 100), 1) if total else 0

        # Average resolution time (days)
        avg_resolution = None
        resolved_with_dates = resolved.filter(resolved_at__isnull=False)
        if resolved_with_dates.exists():
            from django.db.models import ExpressionWrapper, DurationField
            durations = resolved_with_dates.annotate(
                duration=ExpressionWrapper(
                    F("resolved_at") - F("created_at"),
                    output_field=DurationField()
                )
            ).aggregate(avg_duration=Avg("duration"))
            if durations["avg_duration"]:
                avg_resolution = round(durations["avg_duration"].total_seconds() / 86400, 1)

        data = {
            "total": total,
            "open": open_count,
            "resolved": resolved_count,
            "resolution_rate_percent": resolution_rate,
            "avg_resolution_days": avg_resolution,
            "overdue": overdue_count,
            "by_status": by_status,
            "by_category": by_category,
            "by_priority": by_priority,
        }

        return Response(
            api_success(data, "Complaints summary retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── LICENSING SUMMARY (Staff) ────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Staff"], summary="Licensing analytics summary (staff)", responses={200: OpenApiTypes.OBJECT})
class LicensingSummaryView(APIView):
    """
    GET /api/v1/analytics/licensing/summary/

    Licence pipeline stats — active, by type, renewals due, applications in progress.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from licensing.models import Application, ApplicationStatus, Licence, LicenceStatus

        # Active licences
        all_licences = Licence.objects.filter(is_deleted=False)
        active = all_licences.filter(status=LicenceStatus.ACTIVE).count()
        expired = all_licences.filter(status=LicenceStatus.EXPIRED).count()
        suspended = all_licences.filter(status=LicenceStatus.SUSPENDED).count()
        total_licences = all_licences.count()

        # By type
        by_type = dict(
            all_licences.filter(status=LicenceStatus.ACTIVE)
            .values_list("licence_type__name")
            .annotate(count=Count("id"))
            .values_list("licence_type__name", "count")
        )

        # Renewals due in 30/60/90 days
        today = date.today()
        renewals_30 = all_licences.filter(
            status=LicenceStatus.ACTIVE,
            expiry_date__lte=today + timedelta(days=30),
            expiry_date__gte=today,
        ).count()
        renewals_60 = all_licences.filter(
            status=LicenceStatus.ACTIVE,
            expiry_date__lte=today + timedelta(days=60),
            expiry_date__gte=today,
        ).count()
        renewals_90 = all_licences.filter(
            status=LicenceStatus.ACTIVE,
            expiry_date__lte=today + timedelta(days=90),
            expiry_date__gte=today,
        ).count()

        # Application pipeline
        all_apps = Application.objects.filter(is_deleted=False)
        apps_by_status = dict(
            all_apps.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        data = {
            "licences": {
                "total": total_licences,
                "active": active,
                "expired": expired,
                "suspended": suspended,
                "by_type": by_type,
            },
            "renewals_due": {
                "30_days": renewals_30,
                "60_days": renewals_60,
                "90_days": renewals_90,
            },
            "applications": {
                "total": all_apps.count(),
                "by_status": apps_by_status,
            },
        }

        return Response(
            api_success(data, "Licensing summary retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC DASHBOARD ──────────────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Dashboard"], summary="Public dashboard — aggregated safe stats", responses={200: OpenApiTypes.OBJECT})
class PublicDashboardView(APIView):
    """
    GET /api/v1/analytics/dashboard/public/

    Single endpoint returning aggregated public-safe statistics.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from complaints.models import Complaint, ComplaintStatus
        from licensing.models import Licence, LicenceStatus
        from news.models import Article, ArticleStatus
        from publications.models import Publication, PublicationStatus
        from tenders.models import Tender, TenderStatus

        # Licensing
        active_licences = Licence.objects.filter(
            is_deleted=False, status=LicenceStatus.ACTIVE
        ).count()

        # Complaints
        total_complaints = Complaint.objects.filter(is_deleted=False).count()
        resolved_complaints = Complaint.objects.filter(
            is_deleted=False,
            status__in=[ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED],
        ).count()

        # Telecoms
        total_subscribers = 0
        latest_period = (
            TelecomsStat.objects.filter(is_deleted=False)
            .order_by("-period")
            .values_list("period", flat=True)
            .first()
        )
        if latest_period:
            total_subscribers = (
                TelecomsStat.objects.filter(is_deleted=False, period=latest_period)
                .aggregate(total=Sum("subscriber_count"))["total"] or 0
            )

        # Operators
        operator_count = NetworkOperator.objects.filter(
            is_active=True, is_deleted=False
        ).count()

        # Content
        published_publications = Publication.objects.filter(
            is_deleted=False, status=PublicationStatus.PUBLISHED
        ).count()
        open_tenders = Tender.objects.filter(
            is_deleted=False, status__in=[TenderStatus.OPEN, TenderStatus.CLOSING_SOON]
        ).count()
        published_articles = Article.objects.filter(
            is_deleted=False, status=ArticleStatus.PUBLISHED
        ).count()

        data = {
            "active_licences": active_licences,
            "total_complaints": total_complaints,
            "resolved_complaints": resolved_complaints,
            "total_subscribers": total_subscribers,
            "active_operators": operator_count,
            "telecoms_period": str(latest_period) if latest_period else None,
            "published_publications": published_publications,
            "open_tenders": open_tenders,
            "published_articles": published_articles,
        }

        return Response(
            api_success(data, "Public dashboard stats retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF DASHBOARD ──────────────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Dashboard"], summary="Staff dashboard — full operational metrics", responses={200: OpenApiTypes.OBJECT})
class StaffDashboardView(APIView):
    """
    GET /api/v1/analytics/dashboard/staff/

    Comprehensive operational dashboard for BOCRA staff.
    Pulls from all platform modules: users, licensing, domains, complaints,
    telecoms, coverage, QoE, scorecard, alerts, and content.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from complaints.models import Complaint, ComplaintStatus
        from licensing.models import (
            Application, ApplicationStatus,
            Licence, LicenceStatus, LicenceSector,
        )
        from domains.models import (
            Domain, DomainApplication, DomainApplicationStatus,
            DomainStatus, DomainZone,
        )
        from news.models import Article, ArticleStatus
        from notifications.models import Notification
        from alerts.models import AlertCategory, AlertSubscription, AlertLog
        from publications.models import Publication, PublicationStatus
        from tenders.models import Tender, TenderStatus

        User = get_user_model()

        today = date.today()
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        six_months_ago = now - timedelta(days=180)

        # ── Users ────────────────────────────────────────────────────────────
        all_users = User.objects.filter(is_deleted=False)
        total_users = all_users.count()
        verified_users = all_users.filter(email_verified=True).count()
        user_data = {
            "total": total_users,
            "new_this_month": all_users.filter(date_joined__gte=thirty_days_ago).count(),
            "verified": verified_users,
            "verification_rate": round((verified_users / total_users * 100), 1) if total_users else 0,
            "by_role": dict(
                all_users.values_list("role")
                .annotate(count=Count("id"))
                .values_list("role", "count")
            ),
        }

        # ── Licensing ────────────────────────────────────────────────────────
        all_licences = Licence.objects.filter(is_deleted=False)
        active_licences = all_licences.filter(status=LicenceStatus.ACTIVE).count()
        expired_licences = all_licences.filter(status=LicenceStatus.EXPIRED).count()
        suspended_licences = all_licences.filter(status=LicenceStatus.SUSPENDED).count()

        by_sector = dict(
            all_licences.filter(status=LicenceStatus.ACTIVE)
            .values_list("licence_type__sector__name")
            .annotate(count=Count("id"))
            .values_list("licence_type__sector__name", "count")
        )

        licence_data = {
            "total": all_licences.count(),
            "active": active_licences,
            "expired": expired_licences,
            "suspended": suspended_licences,
            "renewals_due_30d": all_licences.filter(
                status=LicenceStatus.ACTIVE,
                expiry_date__lte=today + timedelta(days=30),
                expiry_date__gte=today,
            ).count(),
            "renewals_due_60d": all_licences.filter(
                status=LicenceStatus.ACTIVE,
                expiry_date__lte=today + timedelta(days=60),
                expiry_date__gte=today,
            ).count(),
            "by_sector": by_sector,
        }

        # Applications pipeline
        all_apps = Application.objects.filter(is_deleted=False)
        total_apps = all_apps.count()
        approved_apps = all_apps.filter(status=ApplicationStatus.APPROVED).count()
        rejected_apps = all_apps.filter(status=ApplicationStatus.REJECTED).count()
        decided_apps = approved_apps + rejected_apps

        # Avg processing time
        from django.db.models import ExpressionWrapper, DurationField
        avg_processing = None
        decided_qs = all_apps.filter(
            submitted_at__isnull=False,
            decision_date__isnull=False,
            status__in=[ApplicationStatus.APPROVED, ApplicationStatus.REJECTED],
        )
        if decided_qs.exists():
            durations = decided_qs.annotate(
                duration=ExpressionWrapper(
                    F("decision_date") - F("submitted_at"),
                    output_field=DurationField(),
                )
            ).aggregate(avg_duration=Avg("duration"))
            if durations["avg_duration"]:
                avg_processing = round(durations["avg_duration"].total_seconds() / 86400, 1)

        # Application trend (6 months)
        app_trend = list(
            all_apps.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in app_trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        app_data = {
            "total": total_apps,
            "pending_review": all_apps.filter(status=ApplicationStatus.SUBMITTED).count(),
            "under_review": all_apps.filter(status=ApplicationStatus.UNDER_REVIEW).count(),
            "info_requested": all_apps.filter(status=ApplicationStatus.INFO_REQUESTED).count(),
            "approved_total": approved_apps,
            "rejected_total": rejected_apps,
            "approval_rate": round((approved_apps / decided_apps * 100), 1) if decided_apps else 0,
            "avg_processing_days": avg_processing,
            "recent_30d": all_apps.filter(created_at__gte=thirty_days_ago).count(),
            "trend_6m": app_trend,
        }

        # ── Domains ──────────────────────────────────────────────────────────
        all_domains = Domain.objects.filter(is_deleted=False)
        active_domains = all_domains.filter(status=DomainStatus.ACTIVE).count()
        domain_apps = DomainApplication.objects.filter(is_deleted=False)

        by_zone = dict(
            all_domains.filter(status=DomainStatus.ACTIVE)
            .values_list("zone__name")
            .annotate(count=Count("id"))
            .values_list("zone__name", "count")
        )

        domain_data = {
            "total": all_domains.count(),
            "active": active_domains,
            "expired": all_domains.filter(status=DomainStatus.EXPIRED).count(),
            "expiring_30d": all_domains.filter(
                status=DomainStatus.ACTIVE,
                expires_at__lte=now + timedelta(days=30),
                expires_at__gte=now,
            ).count(),
            "by_zone": by_zone,
            "applications": {
                "total": domain_apps.count(),
                "pending": domain_apps.filter(status=DomainApplicationStatus.SUBMITTED).count(),
                "under_review": domain_apps.filter(status=DomainApplicationStatus.UNDER_REVIEW).count(),
            },
        }

        # ── Complaints ───────────────────────────────────────────────────────
        all_complaints = Complaint.objects.filter(is_deleted=False)
        total_complaints = all_complaints.count()
        open_statuses = [
            ComplaintStatus.SUBMITTED, ComplaintStatus.ASSIGNED,
            ComplaintStatus.INVESTIGATING, ComplaintStatus.AWAITING_RESPONSE,
            ComplaintStatus.REOPENED,
        ]
        open_count = all_complaints.filter(status__in=open_statuses).count()
        overdue_count = all_complaints.filter(
            status__in=open_statuses, sla_deadline__lt=now
        ).count()
        resolved_qs = all_complaints.filter(
            status__in=[ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]
        )
        resolved_count = resolved_qs.count()
        resolution_rate = round((resolved_count / total_complaints * 100), 1) if total_complaints else 0

        # SLA compliance: on-time resolved / total resolved
        on_time = resolved_qs.filter(
            sla_deadline__isnull=False,
            resolved_at__lte=F("sla_deadline"),
        ).count()
        sla_compliance = round((on_time / resolved_count * 100), 1) if resolved_count else 0

        # Avg resolution time
        avg_resolution = None
        resolved_with_dates = resolved_qs.filter(resolved_at__isnull=False)
        if resolved_with_dates.exists():
            durations = resolved_with_dates.annotate(
                duration=ExpressionWrapper(
                    F("resolved_at") - F("created_at"),
                    output_field=DurationField()
                )
            ).aggregate(avg_duration=Avg("duration"))
            if durations["avg_duration"]:
                avg_resolution = round(durations["avg_duration"].total_seconds() / 86400, 1)

        # Complaint trend (6 months)
        complaint_trend = list(
            all_complaints.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in complaint_trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        complaint_data = {
            "total": total_complaints,
            "open": open_count,
            "resolved": resolved_count,
            "overdue": overdue_count,
            "unassigned": all_complaints.filter(
                status=ComplaintStatus.SUBMITTED, assigned_to__isnull=True
            ).count(),
            "resolution_rate": resolution_rate,
            "sla_compliance": sla_compliance,
            "avg_resolution_days": avg_resolution,
            "by_category": dict(
                all_complaints.filter(status__in=open_statuses)
                .values_list("category")
                .annotate(count=Count("id"))
                .values_list("category", "count")
            ),
            "by_priority": dict(
                all_complaints.filter(status__in=open_statuses)
                .values_list("priority")
                .annotate(count=Count("id"))
                .values_list("priority", "count")
            ),
            "trend_6m": complaint_trend,
        }

        # ── Telecoms ─────────────────────────────────────────────────────────
        total_subscribers = 0
        latest_period = (
            TelecomsStat.objects.filter(is_deleted=False)
            .order_by("-period")
            .values_list("period", flat=True)
            .first()
        )
        by_operator_telecoms = []
        if latest_period:
            period_stats = TelecomsStat.objects.filter(
                is_deleted=False, period=latest_period
            ).select_related("operator")
            total_subscribers = (
                period_stats.aggregate(total=Sum("subscriber_count"))["total"] or 0
            )
            by_operator_telecoms = list(
                period_stats.values("operator__name", "operator__code")
                .annotate(
                    subscribers=Sum("subscriber_count"),
                    share=Avg("market_share_percent"),
                )
                .order_by("-subscribers")
            )
        operator_count = NetworkOperator.objects.filter(
            is_active=True, is_deleted=False
        ).count()

        telecoms_data = {
            "total_subscribers": total_subscribers,
            "active_operators": operator_count,
            "latest_period": str(latest_period) if latest_period else None,
            "by_operator": by_operator_telecoms,
        }

        # ── Coverage ─────────────────────────────────────────────────────────
        try:
            from coverages.models import CoverageArea, CoverageUpload
            all_coverage = CoverageArea.objects.filter(is_deleted=False)
            coverage_data = {
                "total_areas": all_coverage.count(),
                "avg_coverage_percent": round(
                    float(all_coverage.aggregate(avg=Avg("coverage_percentage"))["avg"] or 0), 1
                ),
                "by_operator": dict(
                    all_coverage.values_list("operator__name")
                    .annotate(count=Count("id"))
                    .values_list("operator__name", "count")
                ),
                "by_technology": dict(
                    all_coverage.values_list("technology")
                    .annotate(count=Count("id"))
                    .values_list("technology", "count")
                ),
                "pending_uploads": CoverageUpload.objects.filter(
                    is_deleted=False, status="PENDING"
                ).count(),
            }
        except ImportError:
            coverage_data = None

        # ── QoE ──────────────────────────────────────────────────────────────
        try:
            from qoe.models import QoEReport
            all_qoe = QoEReport.objects.filter(is_deleted=False)
            total_qoe = all_qoe.count()
            avg_rating = all_qoe.aggregate(avg=Avg("rating"))["avg"]

            qoe_by_operator = list(
                all_qoe.values("operator__name", "operator__code")
                .annotate(
                    avg_rating=Avg("rating"),
                    report_count=Count("id"),
                )
                .order_by("-avg_rating")
            )

            qoe_data = {
                "total_reports": total_qoe,
                "avg_rating": round(float(avg_rating), 2) if avg_rating else None,
                "reports_last_30d": all_qoe.filter(submitted_at__gte=thirty_days_ago).count(),
                "flagged_reports": all_qoe.filter(is_flagged=True).count(),
                "by_operator": qoe_by_operator,
            }
        except ImportError:
            qoe_data = None

        # ── Scorecard ────────────────────────────────────────────────────────
        try:
            from scorecard.models import OperatorScore
            latest_score_period = (
                OperatorScore.objects.filter(is_deleted=False)
                .order_by("-period")
                .values_list("period", flat=True)
                .first()
            )
            latest_scores = []
            if latest_score_period:
                latest_scores = list(
                    OperatorScore.objects.filter(
                        is_deleted=False, period=latest_score_period
                    )
                    .select_related("operator")
                    .order_by("rank")
                    .values(
                        "operator__name", "operator__code",
                        "composite_score", "rank",
                        "coverage_score", "qoe_score",
                        "complaints_score", "qos_score",
                    )
                )

            scorecard_data = {
                "latest_scores": latest_scores,
                "latest_period": str(latest_score_period) if latest_score_period else None,
            }
        except ImportError:
            scorecard_data = None

        # ── Alerts ───────────────────────────────────────────────────────────
        try:
            all_subs = AlertSubscription.objects.filter(is_deleted=False)
            alerts_data = {
                "total_subscribers": all_subs.count(),
                "confirmed": all_subs.filter(is_confirmed=True).count(),
                "active": all_subs.filter(is_active=True, is_confirmed=True).count(),
                "alerts_sent_30d": AlertLog.objects.filter(
                    is_deleted=False, status="SENT",
                    sent_at__gte=thirty_days_ago,
                ).count(),
                "alerts_failed_30d": AlertLog.objects.filter(
                    is_deleted=False, status="FAILED",
                    created_at__gte=thirty_days_ago,
                ).count(),
            }
        except Exception:
            alerts_data = None

        # ── Content ──────────────────────────────────────────────────────────
        content_data = {
            "publications": {
                "total": Publication.objects.filter(is_deleted=False).count(),
                "published": Publication.objects.filter(is_deleted=False, status=PublicationStatus.PUBLISHED).count(),
                "draft": Publication.objects.filter(is_deleted=False, status=PublicationStatus.DRAFT).count(),
            },
            "tenders": {
                "total": Tender.objects.filter(is_deleted=False).count(),
                "open": Tender.objects.filter(is_deleted=False, status__in=[TenderStatus.OPEN, TenderStatus.CLOSING_SOON]).count(),
                "closing_soon": Tender.objects.filter(is_deleted=False, status=TenderStatus.CLOSING_SOON).count(),
                "awarded": Tender.objects.filter(is_deleted=False, status=TenderStatus.AWARDED).count(),
            },
            "news": {
                "total": Article.objects.filter(is_deleted=False).count(),
                "published": Article.objects.filter(is_deleted=False, status=ArticleStatus.PUBLISHED).count(),
                "draft": Article.objects.filter(is_deleted=False, status=ArticleStatus.DRAFT).count(),
            },
        }

        # ── Notifications ────────────────────────────────────────────────────
        notification_data = {
            "total_sent": Notification.objects.count(),
            "unread": Notification.objects.filter(is_read=False).count(),
        }

        data = {
            "users": user_data,
            "licensing": licence_data,
            "applications": app_data,
            "domains": domain_data,
            "complaints": complaint_data,
            "telecoms": telecoms_data,
            "coverage": coverage_data,
            "qoe": qoe_data,
            "scorecard": scorecard_data,
            "alerts": alerts_data,
            "content": content_data,
            "notifications": notification_data,
        }

        return Response(
            api_success(data, "Staff dashboard retrieved."),
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  NEW ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── USERS SUMMARY (Staff) ────────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Staff"], summary="User registration and account analytics", responses={200: OpenApiTypes.OBJECT})
class UsersSummaryView(APIView):
    """
    GET /api/v1/analytics/users/summary/

    User stats: totals, by role, new registrations over time, locked, verification.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        User = get_user_model()
        now = timezone.now()
        all_users = User.objects.filter(is_deleted=False)
        total = all_users.count()

        # By role
        by_role = dict(
            all_users.values_list("role")
            .annotate(count=Count("id"))
            .values_list("role", "count")
        )

        # Active / locked / unverified
        locked = all_users.filter(locked_until__gt=now).count()
        email_verified = all_users.filter(email_verified=True).count()
        verification_rate = round((email_verified / total * 100), 1) if total else 0

        # Registration trend — last 12 months
        twelve_months_ago = now - timedelta(days=365)
        trend = list(
            all_users.filter(date_joined__gte=twelve_months_ago)
            .annotate(month=TruncMonth("date_joined"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        # New this period
        new_7d = all_users.filter(date_joined__gte=now - timedelta(days=7)).count()
        new_30d = all_users.filter(date_joined__gte=now - timedelta(days=30)).count()

        data = {
            "total": total,
            "by_role": by_role,
            "email_verified": email_verified,
            "verification_rate_percent": verification_rate,
            "locked_accounts": locked,
            "new_last_7_days": new_7d,
            "new_last_30_days": new_30d,
            "registration_trend": trend,
        }

        return Response(
            api_success(data, "User analytics retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── APPLICATIONS TREND (Staff) ───────────────────────────────────────────────

@extend_schema(
    tags=["Analytics — Staff"],
    summary="Application volume trend and processing times",
    responses={200: OpenApiTypes.OBJECT},
)
class ApplicationsTrendView(APIView):
    """
    GET /api/v1/analytics/applications/trend/

    Application submission volume by month, approval/rejection rates, avg processing time.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from licensing.models import Application, ApplicationStatus

        all_apps = Application.objects.filter(is_deleted=False)
        total = all_apps.count()

        # Volume trend — last 12 months
        twelve_months_ago = timezone.now() - timedelta(days=365)
        volume_trend = list(
            all_apps.filter(created_at__gte=twelve_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in volume_trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        # By licence type
        by_type = dict(
            all_apps.values_list("licence_type__name")
            .annotate(count=Count("id"))
            .values_list("licence_type__name", "count")
        )

        # Approval / rejection rates
        approved = all_apps.filter(status=ApplicationStatus.APPROVED).count()
        rejected = all_apps.filter(status=ApplicationStatus.REJECTED).count()
        decided = approved + rejected
        approval_rate = round((approved / decided * 100), 1) if decided else 0

        # Avg processing time (submitted → decision)
        from django.db.models import ExpressionWrapper, DurationField
        decided_apps = all_apps.filter(
            submitted_at__isnull=False,
            decision_date__isnull=False,
            status__in=[ApplicationStatus.APPROVED, ApplicationStatus.REJECTED],
        )
        avg_processing = None
        if decided_apps.exists():
            durations = decided_apps.annotate(
                duration=ExpressionWrapper(
                    F("decision_date") - F("submitted_at"),
                    output_field=DurationField(),
                )
            ).aggregate(avg_duration=Avg("duration"))
            if durations["avg_duration"]:
                avg_processing = round(durations["avg_duration"].total_seconds() / 86400, 1)

        data = {
            "total": total,
            "by_licence_type": by_type,
            "approved": approved,
            "rejected": rejected,
            "approval_rate_percent": approval_rate,
            "avg_processing_days": avg_processing,
            "volume_trend": volume_trend,
        }

        return Response(
            api_success(data, "Applications trend retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── COMPLAINTS TREND (Staff) ─────────────────────────────────────────────────

@extend_schema(
    tags=["Analytics — Staff"],
    summary="Complaint volume trend, top operators, staff workload",
    responses={200: OpenApiTypes.OBJECT},
)
class ComplaintsTrendView(APIView):
    """
    GET /api/v1/analytics/complaints/trend/

    Monthly complaint volumes, top targeted operators, staff assignment stats.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from complaints.models import Complaint, ComplaintStatus

        all_complaints = Complaint.objects.filter(is_deleted=False)

        # Volume trend — last 12 months
        twelve_months_ago = timezone.now() - timedelta(days=365)
        volume_trend = list(
            all_complaints.filter(created_at__gte=twelve_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in volume_trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        # Resolution trend — resolved per month
        resolved_trend = list(
            all_complaints.filter(
                resolved_at__isnull=False,
                resolved_at__gte=twelve_months_ago,
            )
            .annotate(month=TruncMonth("resolved_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in resolved_trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        # Top targeted operators (by operator name)
        top_operators = list(
            all_complaints.exclude(against_operator_name="")
            .values("against_operator_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Staff workload — complaints assigned per staff member
        staff_workload = list(
            all_complaints.filter(assigned_to__isnull=False)
            .values("assigned_to__email", "assigned_to__first_name", "assigned_to__last_name")
            .annotate(
                assigned=Count("id"),
                resolved=Count("id", filter=Q(
                    status__in=[ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]
                )),
            )
            .order_by("-assigned")[:10]
        )

        data = {
            "volume_trend": volume_trend,
            "resolution_trend": resolved_trend,
            "top_targeted_operators": top_operators,
            "staff_workload": staff_workload,
        }

        return Response(
            api_success(data, "Complaints trend retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLICATIONS SUMMARY (Staff) ─────────────────────────────────────────────

@extend_schema(tags=["Analytics — Staff"], summary="Publications analytics", responses={200: OpenApiTypes.OBJECT})
class PublicationsSummaryView(APIView):
    """
    GET /api/v1/analytics/publications/summary/

    Total publications, by category/status, top downloaded, publishing trend.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from publications.models import Publication, PublicationStatus

        all_pubs = Publication.objects.filter(is_deleted=False)
        total = all_pubs.count()

        by_status = dict(
            all_pubs.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        by_category = dict(
            all_pubs.values_list("category")
            .annotate(count=Count("id"))
            .values_list("category", "count")
        )

        # Total downloads
        total_downloads = all_pubs.aggregate(total=Sum("download_count"))["total"] or 0

        # Top 5 downloaded
        top_downloaded = list(
            all_pubs.filter(download_count__gt=0)
            .order_by("-download_count")
            .values("id", "title", "category", "download_count")[:5]
        )

        # Publishing trend — last 12 months
        twelve_months_ago = timezone.now() - timedelta(days=365)
        trend = list(
            all_pubs.filter(
                status=PublicationStatus.PUBLISHED,
                published_date__isnull=False,
                published_date__gte=twelve_months_ago.date(),
            )
            .annotate(month=TruncMonth("published_date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        data = {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "total_downloads": total_downloads,
            "top_downloaded": top_downloaded,
            "publishing_trend": trend,
        }

        return Response(
            api_success(data, "Publications analytics retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── TENDERS SUMMARY (Staff) ──────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Staff"], summary="Tenders analytics", responses={200: OpenApiTypes.OBJECT})
class TendersSummaryView(APIView):
    """
    GET /api/v1/analytics/tenders/summary/

    Tender stats by status/category, award totals, volume trend.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from tenders.models import Tender, TenderAward, TenderStatus

        all_tenders = Tender.objects.filter(is_deleted=False)
        total = all_tenders.count()

        by_status = dict(
            all_tenders.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        by_category = dict(
            all_tenders.values_list("category")
            .annotate(count=Count("id"))
            .values_list("category", "count")
        )

        # Awards
        all_awards = TenderAward.objects.filter(is_deleted=False)
        total_awards = all_awards.count()
        total_award_amount = all_awards.aggregate(total=Sum("award_amount"))["total"] or 0
        avg_award_amount = all_awards.aggregate(avg=Avg("award_amount"))["avg"] or 0

        # Volume trend — last 12 months
        twelve_months_ago = timezone.now() - timedelta(days=365)
        trend = list(
            all_tenders.filter(created_at__gte=twelve_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        data = {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "awards": {
                "total_awarded": total_awards,
                "total_amount": float(total_award_amount),
                "avg_amount": round(float(avg_award_amount), 2),
            },
            "volume_trend": trend,
        }

        return Response(
            api_success(data, "Tenders analytics retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── NEWS SUMMARY (Staff) ─────────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Staff"], summary="News articles analytics", responses={200: OpenApiTypes.OBJECT})
class NewsSummaryView(APIView):
    """
    GET /api/v1/analytics/news/summary/

    Article stats by category/status, top viewed, publishing trend.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from news.models import Article, ArticleStatus

        all_articles = Article.objects.filter(is_deleted=False)
        total = all_articles.count()

        by_status = dict(
            all_articles.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        by_category = dict(
            all_articles.values_list("category")
            .annotate(count=Count("id"))
            .values_list("category", "count")
        )

        # Total views
        total_views = all_articles.aggregate(total=Sum("view_count"))["total"] or 0

        # Top 5 viewed
        top_viewed = list(
            all_articles.filter(view_count__gt=0)
            .order_by("-view_count")
            .values("id", "title", "category", "view_count")[:5]
        )

        # Publishing trend — last 12 months
        twelve_months_ago = timezone.now() - timedelta(days=365)
        trend = list(
            all_articles.filter(
                status=ArticleStatus.PUBLISHED,
                published_at__isnull=False,
                published_at__gte=twelve_months_ago,
            )
            .annotate(month=TruncMonth("published_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        for entry in trend:
            entry["month"] = entry["month"].strftime("%Y-%m")

        data = {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "total_views": total_views,
            "top_viewed": top_viewed,
            "publishing_trend": trend,
        }

        return Response(
            api_success(data, "News analytics retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── CONTENT OVERVIEW (Staff) ─────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Staff"], summary="Combined content metrics — publications, tenders, news", responses={200: OpenApiTypes.OBJECT})
class ContentOverviewView(APIView):
    """
    GET /api/v1/analytics/content/overview/

    One-call summary of all content types for the dashboard header.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from news.models import Article, ArticleStatus
        from publications.models import Publication, PublicationStatus
        from tenders.models import Tender, TenderStatus

        pub_qs = Publication.objects.filter(is_deleted=False)
        tnd_qs = Tender.objects.filter(is_deleted=False)
        art_qs = Article.objects.filter(is_deleted=False)

        data = {
            "publications": {
                "total": pub_qs.count(),
                "published": pub_qs.filter(status=PublicationStatus.PUBLISHED).count(),
                "draft": pub_qs.filter(status=PublicationStatus.DRAFT).count(),
                "archived": pub_qs.filter(status=PublicationStatus.ARCHIVED).count(),
                "total_downloads": pub_qs.aggregate(total=Sum("download_count"))["total"] or 0,
            },
            "tenders": {
                "total": tnd_qs.count(),
                "open": tnd_qs.filter(status__in=[TenderStatus.OPEN, TenderStatus.CLOSING_SOON]).count(),
                "closed": tnd_qs.filter(status=TenderStatus.CLOSED).count(),
                "awarded": tnd_qs.filter(status=TenderStatus.AWARDED).count(),
                "draft": tnd_qs.filter(status=TenderStatus.DRAFT).count(),
            },
            "news": {
                "total": art_qs.count(),
                "published": art_qs.filter(status=ArticleStatus.PUBLISHED).count(),
                "draft": art_qs.filter(status=ArticleStatus.DRAFT).count(),
                "archived": art_qs.filter(status=ArticleStatus.ARCHIVED).count(),
                "total_views": art_qs.aggregate(total=Sum("view_count"))["total"] or 0,
            },
        }

        return Response(
            api_success(data, "Content overview retrieved."),
            status=status.HTTP_200_OK,
        )

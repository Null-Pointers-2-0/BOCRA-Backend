"""
Analytics / Dashboard API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
GET /api/v1/analytics/dashboard/public/        PublicDashboardView      [Public]
GET /api/v1/analytics/dashboard/staff/         StaffDashboardView       [Staff]
GET /api/v1/analytics/telecoms/overview/       TelecomsOverviewView     [Public]
GET /api/v1/analytics/telecoms/operators/      OperatorListView         [Public]
GET /api/v1/analytics/qos/                     QoSListView              [Public]
GET /api/v1/analytics/qos/by-operator/         QoSByOperatorView        [Staff]
GET /api/v1/analytics/complaints/summary/      ComplaintsSummaryView    [Staff]
GET /api/v1/analytics/licensing/summary/       LicensingSummaryView     [Staff]
"""

import logging
from datetime import date, timedelta

from django.db.models import Avg, Count, F, Q, Sum
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
)

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

@extend_schema(tags=["Analytics — Staff"], summary="Complaint analytics summary (staff)")
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

@extend_schema(tags=["Analytics — Staff"], summary="Licensing analytics summary (staff)")
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

@extend_schema(tags=["Analytics — Dashboard"], summary="Public dashboard — aggregated safe stats")
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

        data = {
            "active_licences": active_licences,
            "total_complaints": total_complaints,
            "resolved_complaints": resolved_complaints,
            "total_subscribers": total_subscribers,
            "active_operators": operator_count,
            "telecoms_period": str(latest_period) if latest_period else None,
        }

        return Response(
            api_success(data, "Public dashboard stats retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF DASHBOARD ──────────────────────────────────────────────────────────

@extend_schema(tags=["Analytics — Dashboard"], summary="Staff dashboard — full operational metrics")
class StaffDashboardView(APIView):
    """
    GET /api/v1/analytics/dashboard/staff/

    Combined operational dashboard for BOCRA staff.
    Pulls from licensing, complaints, and telecoms data.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        from complaints.models import Complaint, ComplaintStatus
        from licensing.models import Application, ApplicationStatus, Licence, LicenceStatus

        today = date.today()
        now = timezone.now()

        # ── Licensing ────────────────────────────────────────────────────────
        all_licences = Licence.objects.filter(is_deleted=False)
        licence_data = {
            "active": all_licences.filter(status=LicenceStatus.ACTIVE).count(),
            "expired": all_licences.filter(status=LicenceStatus.EXPIRED).count(),
            "suspended": all_licences.filter(status=LicenceStatus.SUSPENDED).count(),
            "renewals_due_30d": all_licences.filter(
                status=LicenceStatus.ACTIVE,
                expiry_date__lte=today + timedelta(days=30),
                expiry_date__gte=today,
            ).count(),
        }

        # Applications pipeline
        all_apps = Application.objects.filter(is_deleted=False)
        app_data = {
            "pending_review": all_apps.filter(status=ApplicationStatus.SUBMITTED).count(),
            "under_review": all_apps.filter(status=ApplicationStatus.UNDER_REVIEW).count(),
            "info_requested": all_apps.filter(status=ApplicationStatus.INFO_REQUESTED).count(),
            "approved_total": all_apps.filter(status=ApplicationStatus.APPROVED).count(),
            "rejected_total": all_apps.filter(status=ApplicationStatus.REJECTED).count(),
        }

        # ── Complaints ───────────────────────────────────────────────────────
        all_complaints = Complaint.objects.filter(is_deleted=False)
        open_statuses = [
            ComplaintStatus.SUBMITTED, ComplaintStatus.ASSIGNED,
            ComplaintStatus.INVESTIGATING, ComplaintStatus.AWAITING_RESPONSE,
            ComplaintStatus.REOPENED,
        ]
        complaint_data = {
            "open": all_complaints.filter(status__in=open_statuses).count(),
            "resolved": all_complaints.filter(
                status__in=[ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]
            ).count(),
            "overdue": all_complaints.filter(
                status__in=open_statuses, sla_deadline__lt=now
            ).count(),
            "unassigned": all_complaints.filter(
                status=ComplaintStatus.SUBMITTED, assigned_to__isnull=True
            ).count(),
            "by_category": dict(
                all_complaints.filter(status__in=open_statuses)
                .values_list("category")
                .annotate(count=Count("id"))
                .values_list("category", "count")
            ),
        }

        # ── Telecoms ─────────────────────────────────────────────────────────
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
        operator_count = NetworkOperator.objects.filter(
            is_active=True, is_deleted=False
        ).count()

        telecoms_data = {
            "total_subscribers": total_subscribers,
            "active_operators": operator_count,
            "latest_period": str(latest_period) if latest_period else None,
        }

        data = {
            "licensing": licence_data,
            "applications": app_data,
            "complaints": complaint_data,
            "telecoms": telecoms_data,
        }

        return Response(
            api_success(data, "Staff dashboard retrieved."),
            status=status.HTTP_200_OK,
        )

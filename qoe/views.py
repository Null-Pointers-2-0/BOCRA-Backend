"""
QoE Reporter API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints (13)
--------------
POST /api/v1/qoe/reports/                 QoEReportCreateView         [Public]
GET  /api/v1/qoe/reports/                 QoEReportListView           [Staff]
GET  /api/v1/qoe/reports/{id}/            QoEReportDetailView         [Staff]
GET  /api/v1/qoe/speedtest-file/          SpeedTestFileView           [Public]
POST /api/v1/qoe/speedtest-upload/        SpeedTestUploadView         [Public]
GET  /api/v1/qoe/ping/                    PingView                    [Public]
GET  /api/v1/qoe/heatmap/                 QoEHeatmapView              [Public]
GET  /api/v1/qoe/summary/                 QoESummaryView              [Public]
GET  /api/v1/qoe/trends/                  QoETrendsView               [Public]
GET  /api/v1/qoe/speeds/                  QoESpeedDistributionView    [Public]
GET  /api/v1/qoe/analytics/               QoEAnalyticsView            [Staff]
GET  /api/v1/qoe/compare/                 QoEVsQoSCompareView         [Staff]
GET  /api/v1/qoe/districts/               QoEDistrictsView            [Public]
"""

import hashlib
import logging
import os
import time
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Max, Min, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)

from accounts.permissions import IsStaff
from analytics.models import NetworkOperator, QoSRecord
from core.utils import api_error, api_success
from coverages.models import District

from .models import ConnectionType, QoEReport, ServiceType
from .serializers import QoEReportListSerializer, QoEReportSubmitSerializer

logger = logging.getLogger(__name__)


# -- HELPERS -------------------------------------------------------------------

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_HOURS = 1


def _hash_ip(ip_address):
    """SHA-256 hash of IP address."""
    if not ip_address:
        return ""
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()


def _get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _check_rate_limit(ip_hash):
    """Check if IP hash has exceeded rate limit. Returns (ok, count)."""
    cutoff = timezone.now() - timedelta(hours=RATE_LIMIT_WINDOW_HOURS)
    count = QoEReport.objects.filter(
        ip_hash=ip_hash,
        submitted_at__gte=cutoff,
        is_deleted=False,
    ).count()
    return count < RATE_LIMIT_MAX, count


class QoEReportPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


# -- PUBLIC: REPORT SUBMISSION -------------------------------------------------

@extend_schema(
    tags=["QoE Reporter"],
    summary="Submit a QoE report",
    description=(
        "Submit a citizen network experience report. No authentication required. "
        "If the user is logged in, the report is linked to their account. "
        "Rate limited to 5 reports per IP per hour."
    ),
)
class QoEReportCreateView(generics.CreateAPIView):
    """
    POST /api/v1/qoe/reports/

    Submit a QoE report. Auth: Public (anonymous or authenticated).
    Rate limited: 5 reports per IP per hour.
    """

    serializer_class = QoEReportSubmitSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        # Rate limiting
        client_ip = _get_client_ip(request)
        ip_hash = _hash_ip(client_ip)
        ok, count = _check_rate_limit(ip_hash)
        if not ok:
            return Response(
                api_error(
                    f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX} reports per hour.",
                    errors={"rate_limit": f"{count}/{RATE_LIMIT_MAX} used"},
                ),
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            api_success(serializer.data, "QoE report submitted successfully. Thank you!"),
            status=status.HTTP_201_CREATED,
        )


# -- STAFF: REPORT LISTING ----------------------------------------------------

@extend_schema(
    tags=["QoE Reporter -- Staff"],
    summary="List all QoE reports",
    parameters=[
        OpenApiParameter("operator", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         required=False, description="Filter by operator code (e.g. MASCOM)"),
        OpenApiParameter("district", OpenApiTypes.UUID, OpenApiParameter.QUERY,
                         required=False, description="Filter by district UUID"),
        OpenApiParameter("connection_type", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         required=False, description="Filter by connection type (3G, 4G, 5G)"),
        OpenApiParameter("service_type", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         required=False, description="Filter by service type"),
        OpenApiParameter("rating", OpenApiTypes.INT, OpenApiParameter.QUERY,
                         required=False, description="Filter by exact rating (1-5)"),
        OpenApiParameter("is_flagged", OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                         required=False, description="Filter flagged reports"),
        OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY,
                         required=False, description="Filter reports from this date"),
        OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY,
                         required=False, description="Filter reports up to this date"),
    ],
)
class QoEReportListView(generics.ListAPIView):
    """
    GET /api/v1/qoe/reports/

    List all QoE reports (paginated, filtered). Auth: Staff
    """

    serializer_class = QoEReportListSerializer
    permission_classes = [IsStaff]
    pagination_class = QoEReportPagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ["description", "operator__name", "district__name"]
    ordering_fields = ["submitted_at", "rating", "download_speed", "operator__name"]
    ordering = ["-submitted_at"]

    def get_queryset(self):
        qs = (
            QoEReport.objects
            .filter(is_deleted=False)
            .select_related("operator", "district", "submitted_by")
        )

        params = self.request.query_params

        operator = params.get("operator")
        if operator:
            qs = qs.filter(operator__code__iexact=operator)

        district = params.get("district")
        if district:
            qs = qs.filter(district_id=district)

        connection_type = params.get("connection_type")
        if connection_type:
            qs = qs.filter(connection_type=connection_type)

        service_type = params.get("service_type")
        if service_type:
            qs = qs.filter(service_type=service_type)

        rating = params.get("rating")
        if rating:
            qs = qs.filter(rating=int(rating))

        is_flagged = params.get("is_flagged")
        if is_flagged is not None:
            qs = qs.filter(is_flagged=is_flagged.lower() in ("true", "1"))

        date_from = params.get("date_from")
        if date_from:
            qs = qs.filter(submitted_at__date__gte=date_from)

        date_to = params.get("date_to")
        if date_to:
            qs = qs.filter(submitted_at__date__lte=date_to)

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return Response(
                api_success(paginated.data, "QoE reports retrieved."),
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            api_success(serializer.data, "QoE reports retrieved."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["QoE Reporter -- Staff"], summary="Single QoE report detail")
class QoEReportDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/qoe/reports/{id}/

    Single QoE report detail. Auth: Staff
    """

    serializer_class = QoEReportListSerializer
    permission_classes = [IsStaff]
    lookup_field = "pk"

    def get_queryset(self):
        return (
            QoEReport.objects
            .filter(is_deleted=False)
            .select_related("operator", "district", "submitted_by")
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "QoE report detail retrieved."),
            status=status.HTTP_200_OK,
        )


# -- PUBLIC: SPEED TEST ENDPOINTS ----------------------------------------------

@extend_schema(
    tags=["QoE Reporter"],
    summary="Download test file for speed measurement",
    description="Returns a 1MB binary blob. Client measures download time.",
)
class SpeedTestFileView(APIView):
    """
    GET /api/v1/qoe/speedtest-file/

    Serve a 1MB random-byte blob for client-side download speed measurement.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        size = 1024 * 1024  # 1 MB
        data = os.urandom(size)
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Length"] = size
        response["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response["Content-Disposition"] = 'attachment; filename="speedtest.bin"'
        return response


@extend_schema(
    tags=["QoE Reporter"],
    summary="Upload test for speed measurement",
    description=(
        "Client POSTs a binary blob. Server measures receipt time and "
        "returns elapsed milliseconds for upload speed calculation."
    ),
)
class SpeedTestUploadView(APIView):
    """
    POST /api/v1/qoe/speedtest-upload/

    Accept a binary blob upload and return elapsed time for speed calculation.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def post(self, request):
        start = time.monotonic()

        # Read the request body to measure upload
        body = request.body
        size_bytes = len(body)

        elapsed_ms = (time.monotonic() - start) * 1000

        return Response(
            api_success(
                {
                    "size_bytes": size_bytes,
                    "elapsed_ms": round(elapsed_ms, 2),
                },
                "Upload speed test completed.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["QoE Reporter"],
    summary="Latency ping endpoint",
    description="Returns minimal JSON response for client-side latency measurement.",
)
class PingView(APIView):
    """
    GET /api/v1/qoe/ping/

    Minimal JSON response for client-side round-trip latency measurement.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {"pong": True, "ts": int(time.time() * 1000)},
            status=status.HTTP_200_OK,
        )


# -- PUBLIC: AGGREGATION ENDPOINTS ---------------------------------------------

@extend_schema(
    tags=["QoE Reporter"],
    summary="QoE heatmap data by district",
    parameters=[
        OpenApiParameter("operator", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         required=False, description="Filter by operator code"),
        OpenApiParameter("connection_type", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         required=False, description="Filter by connection type"),
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY,
                         required=False, description="Lookback window in days (default: 30)"),
    ],
)
class QoEHeatmapView(APIView):
    """
    GET /api/v1/qoe/heatmap/

    Aggregated QoE data per district for heatmap rendering.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        cutoff = timezone.now() - timedelta(days=days)

        qs = QoEReport.objects.filter(
            is_deleted=False,
            is_flagged=False,
            submitted_at__gte=cutoff,
            district__isnull=False,
        )

        operator = request.query_params.get("operator")
        if operator:
            qs = qs.filter(operator__code__iexact=operator)

        connection_type = request.query_params.get("connection_type")
        if connection_type:
            qs = qs.filter(connection_type=connection_type)

        aggregated = (
            qs.values(
                "district__id",
                "district__name",
                "district__code",
                "district__center_lat",
                "district__center_lng",
            )
            .annotate(
                report_count=Count("id"),
                avg_rating=Avg("rating"),
                avg_download=Avg("download_speed"),
                avg_upload=Avg("upload_speed"),
                avg_latency=Avg("latency_ms"),
            )
            .order_by("-avg_rating")
        )

        heatmap_data = []
        for row in aggregated:
            heatmap_data.append({
                "district_id": str(row["district__id"]),
                "district_name": row["district__name"],
                "district_code": row["district__code"],
                "center_lat": float(row["district__center_lat"]) if row["district__center_lat"] else None,
                "center_lng": float(row["district__center_lng"]) if row["district__center_lng"] else None,
                "report_count": row["report_count"],
                "avg_rating": round(float(row["avg_rating"]), 2) if row["avg_rating"] else None,
                "avg_download_mbps": round(float(row["avg_download"]), 2) if row["avg_download"] else None,
                "avg_upload_mbps": round(float(row["avg_upload"]), 2) if row["avg_upload"] else None,
                "avg_latency_ms": round(float(row["avg_latency"]), 1) if row["avg_latency"] else None,
            })

        return Response(
            api_success(
                {"days": days, "districts": heatmap_data},
                "QoE heatmap data retrieved.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["QoE Reporter"],
    summary="QoE summary statistics",
    parameters=[
        OpenApiParameter("operator", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         required=False, description="Filter by operator code"),
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY,
                         required=False, description="Lookback window in days (default: 30)"),
    ],
)
class QoESummaryView(APIView):
    """
    GET /api/v1/qoe/summary/

    QoE summary stats: overall average rating, per-operator breakdown,
    speed averages. Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        cutoff = timezone.now() - timedelta(days=days)

        qs = QoEReport.objects.filter(
            is_deleted=False,
            is_flagged=False,
            submitted_at__gte=cutoff,
        )

        operator_filter = request.query_params.get("operator")
        if operator_filter:
            qs = qs.filter(operator__code__iexact=operator_filter)

        # Overall stats
        overall = qs.aggregate(
            total_reports=Count("id"),
            avg_rating=Avg("rating"),
            avg_download=Avg("download_speed"),
            avg_upload=Avg("upload_speed"),
            avg_latency=Avg("latency_ms"),
        )

        # Per-operator breakdown
        by_operator = (
            qs.values("operator__code", "operator__name")
            .annotate(
                report_count=Count("id"),
                avg_rating=Avg("rating"),
                avg_download=Avg("download_speed"),
                avg_upload=Avg("upload_speed"),
                avg_latency=Avg("latency_ms"),
            )
            .order_by("operator__name")
        )

        operators = []
        for row in by_operator:
            operators.append({
                "operator": row["operator__code"],
                "operator_name": row["operator__name"],
                "report_count": row["report_count"],
                "avg_rating": round(float(row["avg_rating"]), 2) if row["avg_rating"] else None,
                "avg_download_mbps": round(float(row["avg_download"]), 2) if row["avg_download"] else None,
                "avg_upload_mbps": round(float(row["avg_upload"]), 2) if row["avg_upload"] else None,
                "avg_latency_ms": round(float(row["avg_latency"]), 1) if row["avg_latency"] else None,
            })

        # Rating distribution
        rating_dist = (
            qs.values("rating")
            .annotate(count=Count("id"))
            .order_by("rating")
        )
        distribution = {str(r["rating"]): r["count"] for r in rating_dist}

        return Response(
            api_success(
                {
                    "days": days,
                    "total_reports": overall["total_reports"],
                    "avg_rating": round(float(overall["avg_rating"]), 2) if overall["avg_rating"] else None,
                    "avg_download_mbps": round(float(overall["avg_download"]), 2) if overall["avg_download"] else None,
                    "avg_upload_mbps": round(float(overall["avg_upload"]), 2) if overall["avg_upload"] else None,
                    "avg_latency_ms": round(float(overall["avg_latency"]), 1) if overall["avg_latency"] else None,
                    "rating_distribution": distribution,
                    "by_operator": operators,
                },
                "QoE summary retrieved.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["QoE Reporter"],
    summary="QoE trends over time",
    parameters=[
        OpenApiParameter("months", OpenApiTypes.INT, OpenApiParameter.QUERY,
                         required=False, description="Lookback in months (default: 6)"),
    ],
)
class QoETrendsView(APIView):
    """
    GET /api/v1/qoe/trends/

    Monthly QoE score trends per operator. Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        months = int(request.query_params.get("months", 6))
        cutoff = timezone.now() - timedelta(days=months * 30)

        qs = QoEReport.objects.filter(
            is_deleted=False,
            is_flagged=False,
            submitted_at__gte=cutoff,
        )

        monthly = (
            qs.annotate(month=TruncMonth("submitted_at"))
            .values("month", "operator__code", "operator__name")
            .annotate(
                avg_rating=Avg("rating"),
                avg_download=Avg("download_speed"),
                report_count=Count("id"),
            )
            .order_by("month", "operator__name")
        )

        # Group by month
        trends = defaultdict(dict)
        for row in monthly:
            month_str = row["month"].strftime("%Y-%m")
            trends[month_str][row["operator__code"]] = {
                "operator_name": row["operator__name"],
                "avg_rating": round(float(row["avg_rating"]), 2) if row["avg_rating"] else None,
                "avg_download_mbps": round(float(row["avg_download"]), 2) if row["avg_download"] else None,
                "report_count": row["report_count"],
            }

        result = [
            {"month": month, "operators": ops}
            for month, ops in sorted(trends.items())
        ]

        return Response(
            api_success(
                {"months": months, "trends": result},
                "QoE trends retrieved.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["QoE Reporter"],
    summary="Speed test distribution by operator",
    parameters=[
        OpenApiParameter("connection_type", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         required=False, description="Filter by connection type (3G, 4G, 5G)"),
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY,
                         required=False, description="Lookback window in days (default: 30)"),
    ],
)
class QoESpeedDistributionView(APIView):
    """
    GET /api/v1/qoe/speeds/

    Speed test distribution per operator (avg, min, max, percentiles).
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        cutoff = timezone.now() - timedelta(days=days)

        qs = QoEReport.objects.filter(
            is_deleted=False,
            is_flagged=False,
            submitted_at__gte=cutoff,
            download_speed__isnull=False,
        )

        connection_type = request.query_params.get("connection_type")
        if connection_type:
            qs = qs.filter(connection_type=connection_type)

        by_operator = (
            qs.values("operator__code", "operator__name")
            .annotate(
                sample_count=Count("id"),
                avg_download=Avg("download_speed"),
                min_download=Min("download_speed"),
                max_download=Max("download_speed"),
                avg_upload=Avg("upload_speed"),
                min_upload=Min("upload_speed"),
                max_upload=Max("upload_speed"),
                avg_latency=Avg("latency_ms"),
                min_latency=Min("latency_ms"),
                max_latency=Max("latency_ms"),
            )
            .order_by("operator__name")
        )

        # Per-connection-type breakdown
        by_tech = (
            qs.values("operator__code", "connection_type")
            .annotate(
                sample_count=Count("id"),
                avg_download=Avg("download_speed"),
                avg_upload=Avg("upload_speed"),
                avg_latency=Avg("latency_ms"),
            )
            .order_by("operator__code", "connection_type")
        )

        tech_lookup = defaultdict(list)
        for row in by_tech:
            tech_lookup[row["operator__code"]].append({
                "connection_type": row["connection_type"],
                "sample_count": row["sample_count"],
                "avg_download_mbps": round(float(row["avg_download"]), 2) if row["avg_download"] else None,
                "avg_upload_mbps": round(float(row["avg_upload"]), 2) if row["avg_upload"] else None,
                "avg_latency_ms": round(float(row["avg_latency"]), 1) if row["avg_latency"] else None,
            })

        operators = []
        for row in by_operator:
            code = row["operator__code"]
            operators.append({
                "operator": code,
                "operator_name": row["operator__name"],
                "sample_count": row["sample_count"],
                "download": {
                    "avg_mbps": round(float(row["avg_download"]), 2) if row["avg_download"] else None,
                    "min_mbps": round(float(row["min_download"]), 2) if row["min_download"] else None,
                    "max_mbps": round(float(row["max_download"]), 2) if row["max_download"] else None,
                },
                "upload": {
                    "avg_mbps": round(float(row["avg_upload"]), 2) if row["avg_upload"] else None,
                    "min_mbps": round(float(row["min_upload"]), 2) if row["min_upload"] else None,
                    "max_mbps": round(float(row["max_upload"]), 2) if row["max_upload"] else None,
                },
                "latency": {
                    "avg_ms": round(float(row["avg_latency"]), 1) if row["avg_latency"] else None,
                    "min_ms": row["min_latency"],
                    "max_ms": row["max_latency"],
                },
                "by_connection_type": tech_lookup.get(code, []),
            })

        return Response(
            api_success(
                {"days": days, "operators": operators},
                "Speed distribution retrieved.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["QoE Reporter"],
    summary="Districts with QoE data",
)
class QoEDistrictsView(APIView):
    """
    GET /api/v1/qoe/districts/

    List districts that have QoE data, with report count and avg rating.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        districts = (
            QoEReport.objects
            .filter(is_deleted=False, is_flagged=False, district__isnull=False)
            .values(
                "district__id",
                "district__name",
                "district__code",
                "district__center_lat",
                "district__center_lng",
            )
            .annotate(
                report_count=Count("id"),
                avg_rating=Avg("rating"),
            )
            .order_by("-report_count")
        )

        result = []
        for row in districts:
            result.append({
                "district_id": str(row["district__id"]),
                "district_name": row["district__name"],
                "district_code": row["district__code"],
                "center_lat": float(row["district__center_lat"]) if row["district__center_lat"] else None,
                "center_lng": float(row["district__center_lng"]) if row["district__center_lng"] else None,
                "report_count": row["report_count"],
                "avg_rating": round(float(row["avg_rating"]), 2) if row["avg_rating"] else None,
            })

        return Response(
            api_success(result, "QoE districts retrieved."),
            status=status.HTTP_200_OK,
        )


# -- STAFF: ANALYTICS ENDPOINTS ------------------------------------------------

@extend_schema(
    tags=["QoE Reporter -- Staff"],
    summary="Full QoE analytics for BOCRA staff",
    parameters=[
        OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY,
                         required=False, description="Lookback window in days (default: 30)"),
    ],
)
class QoEAnalyticsView(APIView):
    """
    GET /api/v1/qoe/analytics/

    Comprehensive QoE analytics: totals, operator breakdown, district ranking,
    service type split, connection type split, flagged count.
    Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        cutoff = timezone.now() - timedelta(days=days)

        qs = QoEReport.objects.filter(
            is_deleted=False,
            submitted_at__gte=cutoff,
        )

        total = qs.count()
        flagged = qs.filter(is_flagged=True).count()
        verified = qs.filter(is_verified=True).count()
        with_speed = qs.filter(download_speed__isnull=False).count()
        with_location = qs.filter(latitude__isnull=False).count()

        clean_qs = qs.filter(is_flagged=False)

        # Overall averages
        overall = clean_qs.aggregate(
            avg_rating=Avg("rating"),
            avg_download=Avg("download_speed"),
            avg_upload=Avg("upload_speed"),
            avg_latency=Avg("latency_ms"),
        )

        # Per-operator
        by_operator = list(
            clean_qs.values("operator__code", "operator__name")
            .annotate(
                report_count=Count("id"),
                avg_rating=Avg("rating"),
                avg_download=Avg("download_speed"),
                avg_upload=Avg("upload_speed"),
                avg_latency=Avg("latency_ms"),
            )
            .order_by("operator__name")
        )
        for row in by_operator:
            for key in ("avg_rating", "avg_download", "avg_upload"):
                if row[key] is not None:
                    row[key] = round(float(row[key]), 2)
            if row["avg_latency"] is not None:
                row["avg_latency"] = round(float(row["avg_latency"]), 1)

        # Per-service type
        by_service = list(
            clean_qs.values("service_type")
            .annotate(count=Count("id"), avg_rating=Avg("rating"))
            .order_by("service_type")
        )
        for row in by_service:
            if row["avg_rating"] is not None:
                row["avg_rating"] = round(float(row["avg_rating"]), 2)

        # Per-connection type
        by_connection = list(
            clean_qs.values("connection_type")
            .annotate(
                count=Count("id"),
                avg_rating=Avg("rating"),
                avg_download=Avg("download_speed"),
            )
            .order_by("connection_type")
        )
        for row in by_connection:
            for key in ("avg_rating", "avg_download"):
                if row[key] is not None:
                    row[key] = round(float(row[key]), 2)

        # Top districts by report count
        top_districts = list(
            clean_qs.filter(district__isnull=False)
            .values("district__name", "district__code")
            .annotate(
                report_count=Count("id"),
                avg_rating=Avg("rating"),
            )
            .order_by("-report_count")[:10]
        )
        for row in top_districts:
            if row["avg_rating"] is not None:
                row["avg_rating"] = round(float(row["avg_rating"]), 2)

        return Response(
            api_success(
                {
                    "days": days,
                    "total_reports": total,
                    "flagged_reports": flagged,
                    "verified_reports": verified,
                    "reports_with_speed_test": with_speed,
                    "reports_with_location": with_location,
                    "overall": {
                        "avg_rating": round(float(overall["avg_rating"]), 2) if overall["avg_rating"] else None,
                        "avg_download_mbps": round(float(overall["avg_download"]), 2) if overall["avg_download"] else None,
                        "avg_upload_mbps": round(float(overall["avg_upload"]), 2) if overall["avg_upload"] else None,
                        "avg_latency_ms": round(float(overall["avg_latency"]), 1) if overall["avg_latency"] else None,
                    },
                    "by_operator": by_operator,
                    "by_service_type": by_service,
                    "by_connection_type": by_connection,
                    "top_districts": top_districts,
                },
                "QoE analytics retrieved.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["QoE Reporter -- Staff"],
    summary="QoS vs QoE comparison",
    description=(
        "Compare operator-reported QoS metrics (from analytics.QoSRecord) "
        "against citizen-reported QoE data. Highlights discrepancies."
    ),
)
class QoEVsQoSCompareView(APIView):
    """
    GET /api/v1/qoe/compare/

    QoS (operator-reported from analytics app) vs QoE (citizen-reported)
    side-by-side comparison. Auth: Staff
    """

    permission_classes = [IsStaff]

    def get(self, request):
        # Citizen QoE: last 30 days
        cutoff = timezone.now() - timedelta(days=30)
        qoe_qs = QoEReport.objects.filter(
            is_deleted=False,
            is_flagged=False,
            submitted_at__gte=cutoff,
        )

        qoe_by_operator = (
            qoe_qs.values("operator__code", "operator__name")
            .annotate(
                citizen_avg_rating=Avg("rating"),
                citizen_avg_download=Avg("download_speed"),
                citizen_avg_upload=Avg("upload_speed"),
                citizen_avg_latency=Avg("latency_ms"),
                citizen_report_count=Count("id"),
            )
        )
        qoe_lookup = {row["operator__code"]: row for row in qoe_by_operator}

        # Operator-reported QoS: latest period
        latest_qos_period = (
            QoSRecord.objects
            .filter(is_deleted=False)
            .order_by("-period")
            .values_list("period", flat=True)
            .first()
        )

        qos_lookup = {}
        if latest_qos_period:
            qos_records = (
                QoSRecord.objects
                .filter(is_deleted=False, period=latest_qos_period)
                .select_related("operator")
            )
            for record in qos_records:
                code = record.operator.code
                if code not in qos_lookup:
                    qos_lookup[code] = {"operator_name": record.operator.name, "metrics": {}}
                qos_lookup[code]["metrics"][record.metric_type] = {
                    "value": float(record.value),
                    "unit": record.unit,
                    "benchmark": float(record.benchmark) if record.benchmark else None,
                }

        # Build comparison
        operators = NetworkOperator.objects.filter(
            is_active=True, is_deleted=False,
        ).order_by("name")

        comparison = []
        for op in operators:
            qoe = qoe_lookup.get(op.code, {})
            qos = qos_lookup.get(op.code, {})

            comparison.append({
                "operator": op.code,
                "operator_name": op.name,
                "citizen_qoe": {
                    "report_count": qoe.get("citizen_report_count", 0),
                    "avg_rating": round(float(qoe["citizen_avg_rating"]), 2) if qoe.get("citizen_avg_rating") else None,
                    "avg_download_mbps": round(float(qoe["citizen_avg_download"]), 2) if qoe.get("citizen_avg_download") else None,
                    "avg_upload_mbps": round(float(qoe["citizen_avg_upload"]), 2) if qoe.get("citizen_avg_upload") else None,
                    "avg_latency_ms": round(float(qoe["citizen_avg_latency"]), 1) if qoe.get("citizen_avg_latency") else None,
                },
                "operator_qos": {
                    "period": str(latest_qos_period) if latest_qos_period else None,
                    "metrics": qos.get("metrics", {}),
                },
            })

        return Response(
            api_success(
                {
                    "qoe_window_days": 30,
                    "qos_period": str(latest_qos_period) if latest_qos_period else None,
                    "comparison": comparison,
                },
                "QoS vs QoE comparison retrieved.",
            ),
            status=status.HTTP_200_OK,
        )

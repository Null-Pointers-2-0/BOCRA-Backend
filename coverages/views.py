"""
Coverage Map API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints (11)
--------------
GET  /api/v1/coverages/districts/                 DistrictListView           [Public]
GET  /api/v1/coverages/districts/geojson/         DistrictGeoJSONView        [Public]
GET  /api/v1/coverages/districts/{id}/            DistrictDetailView         [Public]
GET  /api/v1/coverages/operators/                 CoverageOperatorListView   [Public]
GET  /api/v1/coverages/areas/                     CoverageAreaListView       [Public]
GET  /api/v1/coverages/areas/geojson/             CoverageAreaGeoJSONView    [Public]
GET  /api/v1/coverages/summary/                   CoverageSummaryView        [Public]
GET  /api/v1/coverages/summary/{district_id}/     DistrictCoverageSummary    [Public]
GET  /api/v1/coverages/compare/                   CoverageCompareView        [Public]
POST /api/v1/coverages/upload/                    CoverageUploadCreateView   [Admin]
GET  /api/v1/coverages/uploads/                   CoverageUploadListView     [Staff]
GET  /api/v1/coverages/stats/                     CoverageStatsView          [Staff]
"""

import logging
from datetime import date

from django.db.models import Avg, Count, Max, Q, Sum
from django.db.models.functions import Coalesce

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)

from accounts.permissions import IsAdmin, IsStaff
from analytics.models import NetworkOperator
from core.utils import api_error, api_success

from .models import CoverageArea, CoverageLevel, CoverageUpload, District
from .serializers import (
    CoverageAreaGeoJSONSerializer,
    CoverageAreaSerializer,
    CoverageUploadSerializer,
    DistrictDetailSerializer,
    DistrictGeoJSONSerializer,
    DistrictListSerializer,
)

logger = logging.getLogger(__name__)


# -- HELPERS -------------------------------------------------------------------

def _get_latest_period():
    """Return the most recent coverage reporting period."""
    return (
        CoverageArea.objects
        .filter(is_deleted=False)
        .order_by("-period")
        .values_list("period", flat=True)
        .first()
    )


# -- DISTRICT ENDPOINTS --------------------------------------------------------

@extend_schema(tags=["Coverage Map"], summary="List all districts")
class DistrictListView(generics.ListAPIView):
    """
    GET /api/v1/coverages/districts/

    List all active Botswana districts (lightweight -- no boundary GeoJSON).
    Auth: Public
    """

    serializer_class = DistrictListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return District.objects.filter(is_active=True, is_deleted=False)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Districts retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Coverage Map"], summary="District boundaries as GeoJSON FeatureCollection")
class DistrictGeoJSONView(APIView):
    """
    GET /api/v1/coverages/districts/geojson/

    All district boundaries as a GeoJSON FeatureCollection for Leaflet rendering.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        districts = District.objects.filter(is_active=True, is_deleted=False)
        features = DistrictGeoJSONSerializer(districts, many=True).data
        feature_collection = {
            "type": "FeatureCollection",
            "features": features,
        }
        return Response(
            api_success(feature_collection, "District boundaries retrieved."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Coverage Map"], summary="Single district detail with boundary")
class DistrictDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/coverages/districts/{id}/

    Full district detail including boundary GeoJSON and coverage summary.
    Auth: Public
    """

    serializer_class = DistrictDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "pk"

    def get_queryset(self):
        return District.objects.filter(is_active=True, is_deleted=False)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Attach coverage summary for this district
        latest_period = _get_latest_period()
        coverage_data = []
        if latest_period:
            areas = (
                CoverageArea.objects
                .filter(
                    district=instance,
                    period=latest_period,
                    is_deleted=False,
                )
                .select_related("operator")
                .order_by("operator__name", "technology")
            )
            coverage_data = CoverageAreaSerializer(areas, many=True).data

        data = serializer.data
        data["coverage"] = coverage_data
        data["coverage_period"] = str(latest_period) if latest_period else None

        return Response(
            api_success(data, "District detail retrieved."),
            status=status.HTTP_200_OK,
        )


# -- OPERATOR ENDPOINT ---------------------------------------------------------

@extend_schema(tags=["Coverage Map"], summary="Operators with coverage metadata")
class CoverageOperatorListView(APIView):
    """
    GET /api/v1/coverages/operators/

    List operators that have coverage data, with metadata for map filtering.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        operators = (
            NetworkOperator.objects
            .filter(is_active=True, is_deleted=False)
            .order_by("name")
        )

        latest_period = _get_latest_period()
        result = []
        for op in operators:
            district_count = 0
            technologies = []
            if latest_period:
                areas = CoverageArea.objects.filter(
                    operator=op,
                    period=latest_period,
                    is_deleted=False,
                ).exclude(coverage_level=CoverageLevel.NONE)
                district_count = areas.values("district").distinct().count()
                technologies = list(
                    areas.values_list("technology", flat=True).distinct().order_by("technology")
                )

            result.append({
                "id": str(op.id),
                "name": op.name,
                "code": op.code,
                "logo": op.logo.url if op.logo else None,
                "districts_covered": district_count,
                "technologies": technologies,
            })

        return Response(
            api_success(result, "Coverage operators retrieved."),
            status=status.HTTP_200_OK,
        )


# -- COVERAGE AREA ENDPOINTS ---------------------------------------------------

@extend_schema(
    tags=["Coverage Map"],
    summary="Coverage areas with filters",
    parameters=[
        OpenApiParameter("operator", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False,
                         description="Operator code (e.g. MASCOM)"),
        OpenApiParameter("technology", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False,
                         description="Technology tier (2G, 3G, 4G)"),
        OpenApiParameter("district", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=False,
                         description="District UUID"),
        OpenApiParameter("period", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False,
                         description="Reporting period (YYYY-MM-DD)"),
        OpenApiParameter("coverage_level", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False,
                         description="Coverage level (FULL, PARTIAL, MINIMAL, NONE)"),
    ],
)
class CoverageAreaListView(generics.ListAPIView):
    """
    GET /api/v1/coverages/areas/

    Paginated list of coverage area records. Supports filtering by operator,
    technology, district, period, and coverage level.
    Auth: Public
    """

    serializer_class = CoverageAreaSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    ordering_fields = ["period", "coverage_percentage", "operator__name", "district__name"]
    search_fields = ["district__name", "operator__name"]

    def get_queryset(self):
        qs = (
            CoverageArea.objects
            .filter(is_deleted=False)
            .select_related("operator", "district")
        )

        operator = self.request.query_params.get("operator")
        technology = self.request.query_params.get("technology")
        district = self.request.query_params.get("district")
        period = self.request.query_params.get("period")
        coverage_level = self.request.query_params.get("coverage_level")

        if operator:
            qs = qs.filter(operator__code__iexact=operator)
        if technology:
            qs = qs.filter(technology=technology)
        if district:
            qs = qs.filter(district_id=district)
        if period:
            try:
                qs = qs.filter(period=date.fromisoformat(period))
            except ValueError:
                pass
        if coverage_level:
            qs = qs.filter(coverage_level=coverage_level.upper())

        # Default to latest period if no period filter
        if not period:
            latest = _get_latest_period()
            if latest:
                qs = qs.filter(period=latest)

        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return Response(
                api_success(paginated.data, "Coverage areas retrieved."),
                status=status.HTTP_200_OK,
            )
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Coverage areas retrieved."),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Coverage Map"],
    summary="Coverage areas as GeoJSON FeatureCollection (map-ready)",
    parameters=[
        OpenApiParameter("operator", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("technology", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("period", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
    ],
)
class CoverageAreaGeoJSONView(APIView):
    """
    GET /api/v1/coverages/areas/geojson/

    Coverage areas as a GeoJSON FeatureCollection for direct Leaflet consumption.
    Filters by operator and technology. Defaults to latest period.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        qs = (
            CoverageArea.objects
            .filter(is_deleted=False)
            .select_related("operator", "district")
        )

        operator = request.query_params.get("operator")
        technology = request.query_params.get("technology")
        period = request.query_params.get("period")

        if operator:
            qs = qs.filter(operator__code__iexact=operator)
        if technology:
            qs = qs.filter(technology=technology)
        if period:
            try:
                qs = qs.filter(period=date.fromisoformat(period))
            except ValueError:
                pass
        else:
            latest = _get_latest_period()
            if latest:
                qs = qs.filter(period=latest)

        # Exclude NONE coverage from map display
        qs = qs.exclude(coverage_level=CoverageLevel.NONE)

        features = CoverageAreaGeoJSONSerializer(qs, many=True).data
        feature_collection = {
            "type": "FeatureCollection",
            "features": features,
        }

        return Response(
            api_success(feature_collection, "Coverage GeoJSON retrieved."),
            status=status.HTTP_200_OK,
        )


# -- SUMMARY ENDPOINTS ---------------------------------------------------------

@extend_schema(
    tags=["Coverage Map"],
    summary="National coverage summary statistics",
    parameters=[
        OpenApiParameter("technology", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
    ],
)
class CoverageSummaryView(APIView):
    """
    GET /api/v1/coverages/summary/

    National-level coverage summary: overall %, per-operator, white spots.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        latest_period = _get_latest_period()
        if not latest_period:
            return Response(
                api_success({}, "No coverage data available."),
                status=status.HTTP_200_OK,
            )

        technology = request.query_params.get("technology", "4G")

        areas = (
            CoverageArea.objects
            .filter(
                period=latest_period,
                technology=technology,
                is_deleted=False,
            )
            .select_related("operator", "district")
        )

        total_districts = District.objects.filter(is_active=True, is_deleted=False).count()

        # Per-operator summary
        by_operator = []
        operators = NetworkOperator.objects.filter(is_active=True, is_deleted=False)
        for op in operators:
            op_areas = areas.filter(operator=op)
            avg_pct = op_areas.aggregate(avg=Avg("coverage_percentage"))["avg"]
            districts_with_coverage = op_areas.exclude(
                coverage_level=CoverageLevel.NONE
            ).values("district").distinct().count()
            total_pop = op_areas.aggregate(total=Sum("population_covered"))["total"]

            by_operator.append({
                "operator": op.code,
                "operator_name": op.name,
                "avg_coverage_percentage": round(float(avg_pct), 2) if avg_pct else 0,
                "districts_covered": districts_with_coverage,
                "total_districts": total_districts,
                "population_covered": total_pop or 0,
            })

        # White spots -- districts where NO operator has FULL or PARTIAL coverage
        white_spot_districts = []
        for district in District.objects.filter(is_active=True, is_deleted=False):
            has_coverage = areas.filter(
                district=district,
            ).exclude(
                coverage_level__in=[CoverageLevel.NONE, CoverageLevel.MINIMAL]
            ).exists()
            if not has_coverage:
                white_spot_districts.append({
                    "id": str(district.id),
                    "name": district.name,
                    "code": district.code,
                })

        # National average
        national_avg = areas.aggregate(avg=Avg("coverage_percentage"))["avg"]

        data = {
            "period": str(latest_period),
            "technology": technology,
            "national_avg_coverage": round(float(national_avg), 2) if national_avg else 0,
            "total_districts": total_districts,
            "by_operator": by_operator,
            "white_spots": white_spot_districts,
            "white_spot_count": len(white_spot_districts),
        }

        return Response(
            api_success(data, "Coverage summary retrieved."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Coverage Map"], summary="Coverage summary for a specific district")
class DistrictCoverageSummaryView(APIView):
    """
    GET /api/v1/coverages/summary/{district_id}/

    Coverage breakdown for a single district: per-operator, per-technology.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request, district_id):
        try:
            district = District.objects.get(
                pk=district_id, is_active=True, is_deleted=False
            )
        except District.DoesNotExist:
            return Response(
                api_error("District not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        latest_period = _get_latest_period()
        if not latest_period:
            return Response(
                api_success({}, "No coverage data available for this district."),
                status=status.HTTP_200_OK,
            )

        areas = (
            CoverageArea.objects
            .filter(
                district=district,
                period=latest_period,
                is_deleted=False,
            )
            .select_related("operator")
            .order_by("operator__name", "technology")
        )

        # Group by operator
        operators_data = {}
        for area in areas:
            code = area.operator.code
            if code not in operators_data:
                operators_data[code] = {
                    "operator": code,
                    "operator_name": area.operator.name,
                    "technologies": {},
                }
            operators_data[code]["technologies"][area.technology] = {
                "coverage_level": area.coverage_level,
                "coverage_percentage": float(area.coverage_percentage),
                "population_covered": area.population_covered,
                "signal_strength_avg": (
                    float(area.signal_strength_avg) if area.signal_strength_avg else None
                ),
            }

        data = {
            "district": {
                "id": str(district.id),
                "name": district.name,
                "code": district.code,
                "population": district.population,
            },
            "period": str(latest_period),
            "operators": list(operators_data.values()),
        }

        return Response(
            api_success(data, f"Coverage summary for {district.name} retrieved."),
            status=status.HTTP_200_OK,
        )


# -- COMPARE ENDPOINT ---------------------------------------------------------

@extend_schema(
    tags=["Coverage Map"],
    summary="Side-by-side operator coverage comparison",
    parameters=[
        OpenApiParameter("technology", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
    ],
)
class CoverageCompareView(APIView):
    """
    GET /api/v1/coverages/compare/

    All operators side by side for every district at a given technology.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        latest_period = _get_latest_period()
        if not latest_period:
            return Response(
                api_success([], "No coverage data available."),
                status=status.HTTP_200_OK,
            )

        technology = request.query_params.get("technology", "4G")

        areas = (
            CoverageArea.objects
            .filter(
                period=latest_period,
                technology=technology,
                is_deleted=False,
            )
            .select_related("operator", "district")
            .order_by("district__name", "operator__name")
        )

        # Pivot: rows = districts, columns = operators
        districts = District.objects.filter(is_active=True, is_deleted=False).order_by("name")
        operators = NetworkOperator.objects.filter(is_active=True, is_deleted=False).order_by("name")

        # Build lookup
        area_lookup = {}
        for area in areas:
            key = (str(area.district_id), str(area.operator_id))
            area_lookup[key] = {
                "coverage_level": area.coverage_level,
                "coverage_percentage": float(area.coverage_percentage),
            }

        comparison = []
        for district in districts:
            row = {
                "district": district.name,
                "district_code": district.code,
                "district_id": str(district.id),
                "operators": {},
            }
            for op in operators:
                key = (str(district.id), str(op.id))
                entry = area_lookup.get(key)
                row["operators"][op.code] = entry or {
                    "coverage_level": "NONE",
                    "coverage_percentage": 0.0,
                }
            comparison.append(row)

        data = {
            "period": str(latest_period),
            "technology": technology,
            "operators": [{"code": op.code, "name": op.name} for op in operators],
            "comparison": comparison,
        }

        return Response(
            api_success(data, "Coverage comparison retrieved."),
            status=status.HTTP_200_OK,
        )


# -- UPLOAD ENDPOINTS (Admin/Staff) --------------------------------------------

@extend_schema(tags=["Coverage Map — Staff"], summary="Upload new coverage GeoJSON")
class CoverageUploadCreateView(generics.CreateAPIView):
    """
    POST /api/v1/coverages/upload/

    Admin uploads coverage data file from an operator.
    Auth: Admin
    """

    serializer_class = CoverageUploadSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            api_success(
                CoverageUploadSerializer(instance).data,
                "Coverage data uploaded. Processing will begin shortly.",
            ),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Coverage Map — Staff"], summary="List coverage upload history")
class CoverageUploadListView(generics.ListAPIView):
    """
    GET /api/v1/coverages/uploads/

    List all coverage data uploads with their processing status.
    Auth: Staff
    """

    serializer_class = CoverageUploadSerializer
    permission_classes = [IsAuthenticated, IsStaff]

    def get_queryset(self):
        return (
            CoverageUpload.objects
            .filter(is_deleted=False)
            .select_related("operator", "created_by")
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return Response(
                api_success(paginated.data, "Upload history retrieved."),
                status=status.HTTP_200_OK,
            )
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Upload history retrieved."),
            status=status.HTTP_200_OK,
        )


# -- STATS ENDPOINT (Staff) ---------------------------------------------------

@extend_schema(tags=["Coverage Map — Staff"], summary="Coverage analytics and growth trends")
class CoverageStatsView(APIView):
    """
    GET /api/v1/coverages/stats/

    Coverage analytics: growth trends over time, top/bottom coverage districts,
    operator expansion tracking.
    Auth: Staff
    """

    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        technology = request.query_params.get("technology", "4G")

        # All periods available
        periods = (
            CoverageArea.objects
            .filter(is_deleted=False, technology=technology)
            .values_list("period", flat=True)
            .distinct()
            .order_by("period")
        )

        # Trend: average coverage per period per operator
        trends = []
        operators = NetworkOperator.objects.filter(is_active=True, is_deleted=False)
        for period in periods:
            period_data = {"period": str(period), "operators": {}}
            for op in operators:
                avg = (
                    CoverageArea.objects
                    .filter(
                        operator=op,
                        technology=technology,
                        period=period,
                        is_deleted=False,
                    )
                    .aggregate(avg=Avg("coverage_percentage"))["avg"]
                )
                period_data["operators"][op.code] = round(float(avg), 2) if avg else 0
            trends.append(period_data)

        # Latest period district ranking
        latest_period = _get_latest_period()
        district_ranking = []
        if latest_period:
            districts = District.objects.filter(is_active=True, is_deleted=False)
            for district in districts:
                avg = (
                    CoverageArea.objects
                    .filter(
                        district=district,
                        technology=technology,
                        period=latest_period,
                        is_deleted=False,
                    )
                    .aggregate(avg=Avg("coverage_percentage"))["avg"]
                )
                district_ranking.append({
                    "district": district.name,
                    "code": district.code,
                    "avg_coverage": round(float(avg), 2) if avg else 0,
                })
            district_ranking.sort(key=lambda x: x["avg_coverage"], reverse=True)

        data = {
            "technology": technology,
            "trends": trends,
            "district_ranking": district_ranking,
            "total_records": CoverageArea.objects.filter(is_deleted=False).count(),
            "periods_available": [str(p) for p in periods],
        }

        return Response(
            api_success(data, "Coverage statistics retrieved."),
            status=status.HTTP_200_OK,
        )

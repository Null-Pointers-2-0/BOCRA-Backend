"""
Scorecard API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints (9)
-------------
GET  /api/v1/scorecard/weights/                     ScorecardWeightsView             [Public]
PUT  /api/v1/scorecard/weights/{dimension}/          ScorecardWeightUpdateView        [Admin]
GET  /api/v1/scorecard/scores/                       CurrentScoresView                [Public]
GET  /api/v1/scorecard/scores/history/               ScoreHistoryView                 [Public]
GET  /api/v1/scorecard/scores/{operator_code}/       OperatorScoreDetailView          [Public]
POST /api/v1/scorecard/scores/compute/               ComputeScoresView                [Admin]
GET  /api/v1/scorecard/manual-metrics/               ManualMetricListView             [Staff]
POST /api/v1/scorecard/manual-metrics/               ManualMetricCreateView           [Staff]
GET  /api/v1/scorecard/rankings/                     RankingsView                     [Public]
"""

import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Max, Q
from django.utils import timezone

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)

from accounts.permissions import IsAdmin, IsStaff
from analytics.models import NetworkOperator, QoSRecord
from complaints.models import Complaint
from core.utils import api_error, api_success
from coverages.models import CoverageArea
from qoe.models import QoEReport

from .models import (
    ManualMetricEntry,
    OperatorScore,
    ScorecardWeightConfig,
    ScoringDimension,
)
from .serializers import (
    ManualMetricEntrySerializer,
    OperatorScoreDetailSerializer,
    OperatorScoreSerializer,
    ScorecardWeightSerializer,
    ScorecardWeightUpdateSerializer,
)

logger = logging.getLogger(__name__)


# -- HELPERS -------------------------------------------------------------------

def _compute_coverage_score(operator, period_start, period_end):
    """
    Coverage score (0-100): average coverage_percentage across all districts
    and technologies for this operator in the period.
    """
    areas = CoverageArea.objects.filter(
        operator=operator,
        is_deleted=False,
        period__lte=period_end,
    )
    if not areas.exists():
        return Decimal("0"), {}

    agg = areas.aggregate(avg_pct=Avg("coverage_percentage"))
    avg_pct = agg["avg_pct"] or Decimal("0")
    score = min(Decimal("100"), max(Decimal("0"), avg_pct))

    meta = {
        "area_count": areas.count(),
        "avg_coverage_pct": float(avg_pct),
    }
    return round(score, 2), meta


def _compute_qoe_score(operator, period_start, period_end):
    """
    QoE score (0-100): normalized average citizen rating (1-5 mapped to 0-100).
    Formula: (avg_rating - 1) / 4 * 100
    """
    reports = QoEReport.objects.filter(
        operator=operator,
        is_deleted=False,
        submitted_at__gte=period_start,
        submitted_at__lt=period_end,
    )
    if not reports.exists():
        return Decimal("0"), {}

    agg = reports.aggregate(avg_rating=Avg("rating"), count=Count("id"))
    avg_rating = Decimal(str(agg["avg_rating"] or 0))
    count = agg["count"]

    # Map 1-5 to 0-100
    score = (avg_rating - Decimal("1")) / Decimal("4") * Decimal("100")
    score = min(Decimal("100"), max(Decimal("0"), score))

    meta = {
        "report_count": count,
        "avg_rating": float(avg_rating),
    }
    return round(score, 2), meta


def _compute_complaints_score(operator, period_start, period_end):
    """
    Complaints score (0-100): inverse of complaint volume.
    Fewer complaints per operator = higher score.

    Formula: max(0, 100 - (complaint_count * penalty_per_complaint))
    Penalty = 2 points per complaint (caps at 0 for 50+ complaints).
    """
    # Match complaints by operator name (against_operator_name contains operator name)
    complaints = Complaint.objects.filter(
        is_deleted=False,
        created_at__gte=period_start,
        created_at__lt=period_end,
        against_operator_name__icontains=operator.name,
    )
    count = complaints.count()

    # Also check resolved ratio for bonus
    resolved = complaints.filter(
        status__in=["RESOLVED", "CLOSED"],
    ).count()
    resolution_rate = (resolved / count * 100) if count > 0 else 100

    # Base score: fewer complaints = higher
    penalty_per_complaint = Decimal("2")
    base_score = Decimal("100") - (Decimal(str(count)) * penalty_per_complaint)
    base_score = max(Decimal("0"), base_score)

    # Resolution bonus: up to 10 points for 100% resolution rate
    resolution_bonus = Decimal(str(resolution_rate)) / Decimal("10")
    score = min(Decimal("100"), base_score + resolution_bonus)

    meta = {
        "complaint_count": count,
        "resolved_count": resolved,
        "resolution_rate_pct": round(resolution_rate, 1),
    }
    return round(score, 2), meta


def _compute_qos_score(operator, period_start, period_end):
    """
    QoS compliance score (0-100): how well the operator meets BOCRA benchmarks.

    For each QoS metric with a benchmark:
    - If value meets/exceeds benchmark: 100 points for that metric
    - Otherwise: proportional score (value / benchmark * 100)

    Special handling: LATENCY and DROP_RATE are "lower is better".
    """
    records = QoSRecord.objects.filter(
        operator=operator,
        is_deleted=False,
        period__gte=period_start,
        period__lt=period_end,
        benchmark__isnull=False,
    )
    if not records.exists():
        return Decimal("50"), {"note": "No QoS records with benchmarks found, default score."}

    metric_scores = []
    details = []

    for record in records:
        benchmark = record.benchmark
        value = record.value

        if benchmark == 0:
            continue

        # For LATENCY and DROP_RATE, lower is better
        if record.metric_type in ("LATENCY", "DROP_RATE"):
            if value <= benchmark:
                m_score = Decimal("100")
            else:
                m_score = (benchmark / value) * Decimal("100")
        else:
            if value >= benchmark:
                m_score = Decimal("100")
            else:
                m_score = (value / benchmark) * Decimal("100")

        m_score = min(Decimal("100"), max(Decimal("0"), m_score))
        metric_scores.append(m_score)
        details.append({
            "metric": record.metric_type,
            "value": float(value),
            "benchmark": float(benchmark),
            "unit": record.unit,
            "score": float(round(m_score, 2)),
        })

    if not metric_scores:
        return Decimal("50"), {"note": "No scoreable QoS metrics found."}

    avg_score = sum(metric_scores) / len(metric_scores)

    meta = {
        "metric_count": len(metric_scores),
        "metrics": details,
    }
    return round(avg_score, 2), meta


def _compute_all_scores(period_start, period_end):
    """
    Compute scores for all active operators for the given period.
    Returns list of created/updated OperatorScore objects.
    """
    operators = NetworkOperator.objects.filter(is_active=True, is_deleted=False)
    weights = {w.dimension: w.weight for w in ScorecardWeightConfig.objects.all()}

    # Default weights if not configured
    w_coverage = weights.get(ScoringDimension.COVERAGE, Decimal("0.30"))
    w_qoe = weights.get(ScoringDimension.QOE, Decimal("0.30"))
    w_complaints = weights.get(ScoringDimension.COMPLAINTS, Decimal("0.20"))
    w_qos = weights.get(ScoringDimension.QOS, Decimal("0.20"))

    scores_data = []
    for op in operators:
        cov_score, cov_meta = _compute_coverage_score(op, period_start, period_end)
        qoe_score, qoe_meta = _compute_qoe_score(op, period_start, period_end)
        comp_score, comp_meta = _compute_complaints_score(op, period_start, period_end)
        qos_score, qos_meta = _compute_qos_score(op, period_start, period_end)

        composite = (
            cov_score * w_coverage
            + qoe_score * w_qoe
            + comp_score * w_complaints
            + qos_score * w_qos
        )
        composite = min(Decimal("100"), max(Decimal("0"), round(composite, 2)))

        metadata = {
            "weights": {
                "coverage": float(w_coverage),
                "qoe": float(w_qoe),
                "complaints": float(w_complaints),
                "qos": float(w_qos),
            },
            "coverage": cov_meta,
            "qoe": qoe_meta,
            "complaints": comp_meta,
            "qos": qos_meta,
        }

        scores_data.append({
            "operator": op,
            "coverage_score": cov_score,
            "qoe_score": qoe_score,
            "complaints_score": comp_score,
            "qos_score": qos_score,
            "composite_score": composite,
            "metadata": metadata,
        })

    # Sort by composite score descending to assign ranks
    scores_data.sort(key=lambda x: x["composite_score"], reverse=True)

    results = []
    for rank, data in enumerate(scores_data, start=1):
        obj, _ = OperatorScore.objects.update_or_create(
            operator=data["operator"],
            period=period_start,
            defaults={
                "coverage_score": data["coverage_score"],
                "qoe_score": data["qoe_score"],
                "complaints_score": data["complaints_score"],
                "qos_score": data["qos_score"],
                "composite_score": data["composite_score"],
                "rank": rank,
                "metadata": data["metadata"],
                "is_deleted": False,
            },
        )
        results.append(obj)

    return results


# -- PAGINATION ----------------------------------------------------------------

class ScoreHistoryPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class ManualMetricPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


# -- PUBLIC VIEWS --------------------------------------------------------------

class ScorecardWeightsView(APIView):
    """GET current scorecard weight configuration."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Scorecard"],
        summary="Get scorecard weights",
        description="Returns the current weight configuration for all scoring dimensions.",
        responses={200: ScorecardWeightSerializer(many=True)},
    )
    def get(self, request):
        weights = ScorecardWeightConfig.objects.filter(is_deleted=False)
        serializer = ScorecardWeightSerializer(weights, many=True)
        return Response(api_success(
            message="Scorecard weights retrieved.",
            data=serializer.data,
        ))


class ScorecardWeightUpdateView(APIView):
    """PUT update a single scoring dimension weight. Admin only."""

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Scorecard -- Admin"],
        summary="Update a scoring weight",
        description="Update the weight for a specific scoring dimension. Admin only.",
        request=ScorecardWeightUpdateSerializer,
        responses={200: ScorecardWeightSerializer},
    )
    def put(self, request, dimension):
        dimension = dimension.upper()
        valid_dimensions = [d.value for d in ScoringDimension]
        if dimension not in valid_dimensions:
            return Response(
                api_error(message=f"Invalid dimension. Must be one of: {', '.join(valid_dimensions)}"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            weight_obj = ScorecardWeightConfig.objects.get(dimension=dimension, is_deleted=False)
        except ScorecardWeightConfig.DoesNotExist:
            return Response(
                api_error(message=f"Weight config for {dimension} not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ScorecardWeightUpdateSerializer(weight_obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                api_error(message="Validation failed.", errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(updated_by=request.user)
        result = ScorecardWeightSerializer(weight_obj)
        return Response(api_success(
            message=f"Weight for {dimension} updated.",
            data=result.data,
        ))


class CurrentScoresView(APIView):
    """GET latest scorecard for all operators (most recent period)."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Scorecard"],
        summary="Get current operator scores",
        description="Returns the latest scorecard scores for all operators.",
        responses={200: OperatorScoreSerializer(many=True)},
    )
    def get(self, request):
        latest_period = OperatorScore.objects.filter(
            is_deleted=False,
        ).order_by("-period").values_list("period", flat=True).first()

        if not latest_period:
            return Response(api_success(
                message="No scorecard data available.",
                data={"period": None, "scores": []},
            ))

        scores = OperatorScore.objects.filter(
            period=latest_period,
            is_deleted=False,
        ).select_related("operator").order_by("rank")

        serializer = OperatorScoreSerializer(scores, many=True)
        return Response(api_success(
            message="Current operator scores retrieved.",
            data={
                "period": str(latest_period),
                "scores": serializer.data,
            },
        ))


class ScoreHistoryView(APIView):
    """GET monthly scorecard history for all operators."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Scorecard"],
        summary="Get score history",
        description="Returns monthly scorecard history. Optionally filter by operator.",
        parameters=[
            OpenApiParameter("operator", OpenApiTypes.STR, description="Filter by operator code"),
            OpenApiParameter("months", OpenApiTypes.INT, description="Number of months (default 6)"),
        ],
        responses={200: OperatorScoreSerializer(many=True)},
    )
    def get(self, request):
        months = int(request.query_params.get("months", 6))
        operator_code = request.query_params.get("operator")

        cutoff = timezone.now().date().replace(day=1) - timedelta(days=months * 31)

        qs = OperatorScore.objects.filter(
            is_deleted=False,
            period__gte=cutoff,
        ).select_related("operator").order_by("-period", "rank")

        if operator_code:
            qs = qs.filter(operator__code__iexact=operator_code)

        # Group by period
        history = defaultdict(list)
        for score in qs:
            period_str = str(score.period)
            history[period_str].append(OperatorScoreSerializer(score).data)

        periods = []
        for period_str in sorted(history.keys()):
            periods.append({
                "period": period_str,
                "scores": history[period_str],
            })

        return Response(api_success(
            message="Score history retrieved.",
            data={
                "months": months,
                "periods": periods,
            },
        ))


class OperatorScoreDetailView(APIView):
    """GET detailed scorecard for a single operator (latest + history)."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Scorecard"],
        summary="Get operator score detail",
        description="Returns the latest score and recent history for a specific operator.",
        parameters=[
            OpenApiParameter("months", OpenApiTypes.INT, description="History months (default 6)"),
        ],
        responses={200: OperatorScoreDetailSerializer},
    )
    def get(self, request, operator_code):
        try:
            operator = NetworkOperator.objects.get(
                code__iexact=operator_code, is_active=True, is_deleted=False,
            )
        except NetworkOperator.DoesNotExist:
            return Response(
                api_error(message=f"Operator '{operator_code}' not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        months = int(request.query_params.get("months", 6))
        cutoff = timezone.now().date().replace(day=1) - timedelta(days=months * 31)

        scores = OperatorScore.objects.filter(
            operator=operator,
            is_deleted=False,
            period__gte=cutoff,
        ).order_by("-period")

        latest = scores.first()
        if not latest:
            return Response(api_success(
                message=f"No scorecard data for {operator.name}.",
                data={
                    "operator": str(operator.id),
                    "operator_name": operator.name,
                    "operator_code": operator.code,
                    "latest": None,
                    "history": [],
                },
            ))

        return Response(api_success(
            message=f"Scorecard for {operator.name} retrieved.",
            data={
                "operator": str(operator.id),
                "operator_name": operator.name,
                "operator_code": operator.code,
                "latest": OperatorScoreDetailSerializer(latest).data,
                "history": OperatorScoreSerializer(scores, many=True).data,
            },
        ))


class RankingsView(APIView):
    """GET operator leaderboard ranked by composite score."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Scorecard"],
        summary="Get operator rankings",
        description="Returns the operator leaderboard for the latest period, ranked by composite score.",
        responses={200: OperatorScoreSerializer(many=True)},
    )
    def get(self, request):
        latest_period = OperatorScore.objects.filter(
            is_deleted=False,
        ).order_by("-period").values_list("period", flat=True).first()

        if not latest_period:
            return Response(api_success(
                message="No ranking data available.",
                data={"period": None, "rankings": []},
            ))

        scores = OperatorScore.objects.filter(
            period=latest_period,
            is_deleted=False,
        ).select_related("operator").order_by("rank")

        serializer = OperatorScoreSerializer(scores, many=True)

        rankings = []
        for item in serializer.data:
            rankings.append({
                **item,
                "trend": None,  # populated below if history exists
            })

        # Add trend vs previous period
        prev_scores = OperatorScore.objects.filter(
            is_deleted=False,
            period__lt=latest_period,
        ).order_by("-period")

        if prev_scores.exists():
            prev_period = prev_scores.first().period
            prev_map = {
                s.operator.code: s
                for s in OperatorScore.objects.filter(
                    period=prev_period, is_deleted=False,
                ).select_related("operator")
            }
            for r in rankings:
                prev = prev_map.get(r["operator_code"])
                if prev:
                    diff = float(r["composite_score"]) - float(prev.composite_score)
                    rank_diff = prev.rank - r["rank"]
                    r["trend"] = {
                        "score_change": round(diff, 2),
                        "rank_change": rank_diff,
                        "previous_rank": prev.rank,
                        "previous_composite": float(prev.composite_score),
                    }

        return Response(api_success(
            message="Operator rankings retrieved.",
            data={
                "period": str(latest_period),
                "rankings": rankings,
            },
        ))


# -- ADMIN VIEWS ---------------------------------------------------------------

class ComputeScoresView(APIView):
    """POST trigger score computation for a given period. Admin only."""

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Scorecard -- Admin"],
        summary="Compute operator scores",
        description=(
            "Trigger score computation for a given period. "
            "If no period is provided, computes for the current month. "
            "Admin only."
        ),
        parameters=[
            OpenApiParameter("period", OpenApiTypes.DATE, description="Period as YYYY-MM-DD (first of month)"),
        ],
    )
    def post(self, request):
        period_str = request.query_params.get("period") or request.data.get("period")

        if period_str:
            try:
                from datetime import date as date_type
                parts = period_str.split("-")
                period_start = date_type(int(parts[0]), int(parts[1]), 1)
            except (ValueError, IndexError):
                return Response(
                    api_error(message="Invalid period format. Use YYYY-MM-DD."),
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            today = timezone.now().date()
            period_start = today.replace(day=1)

        # Period end = first day of next month
        if period_start.month == 12:
            from datetime import date as date_type
            period_end = date_type(period_start.year + 1, 1, 1)
        else:
            from datetime import date as date_type
            period_end = date_type(period_start.year, period_start.month + 1, 1)

        results = _compute_all_scores(period_start, period_end)

        return Response(api_success(
            message=f"Scores computed for {period_start}. {len(results)} operator(s) scored.",
            data={
                "period": str(period_start),
                "scores": OperatorScoreSerializer(results, many=True).data,
            },
        ), status=status.HTTP_200_OK)


# -- STAFF VIEWS ---------------------------------------------------------------

class ManualMetricListView(APIView):
    """GET list manual metric entries. Staff only."""

    permission_classes = [IsStaff]

    @extend_schema(
        tags=["Scorecard -- Staff"],
        summary="List manual metrics",
        description="Returns paginated list of manual metric entries.",
        parameters=[
            OpenApiParameter("operator", OpenApiTypes.STR, description="Filter by operator code"),
            OpenApiParameter("period", OpenApiTypes.DATE, description="Filter by period"),
            OpenApiParameter("page", OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT),
        ],
        responses={200: ManualMetricEntrySerializer(many=True)},
    )
    def get(self, request):
        qs = ManualMetricEntry.objects.filter(
            is_deleted=False,
        ).select_related("operator", "entered_by")

        operator_code = request.query_params.get("operator")
        if operator_code:
            qs = qs.filter(operator__code__iexact=operator_code)

        period = request.query_params.get("period")
        if period:
            qs = qs.filter(period=period)

        paginator = ManualMetricPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ManualMetricEntrySerializer(page, many=True)

        return Response(api_success(
            message="Manual metrics retrieved.",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        ))


class ManualMetricCreateView(APIView):
    """POST create a manual metric entry. Staff only."""

    permission_classes = [IsStaff]

    @extend_schema(
        tags=["Scorecard -- Staff"],
        summary="Create manual metric",
        description="Add a manual metric entry for an operator/period.",
        request=ManualMetricEntrySerializer,
        responses={201: ManualMetricEntrySerializer},
    )
    def post(self, request):
        serializer = ManualMetricEntrySerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(
                api_error(message="Validation failed.", errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(
            api_success(message="Manual metric entry created.", data=serializer.data),
            status=status.HTTP_201_CREATED,
        )

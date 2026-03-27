"""
Cybersecurity API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
POST   /api/v1/cybersecurity/request-audit/              RequestAuditView           [Public]
GET    /api/v1/cybersecurity/my-requests/                 MyAuditRequestsView        [Authenticated]
GET    /api/v1/cybersecurity/my-requests/<pk>/            MyAuditRequestDetailView   [Authenticated]
GET    /api/v1/cybersecurity/staff/                       StaffAuditRequestListView  [Staff]
GET    /api/v1/cybersecurity/staff/counts/                AuditRequestCountView      [Staff]
GET    /api/v1/cybersecurity/staff/<pk>/                  StaffAuditRequestDetailView[Staff]
PATCH  /api/v1/cybersecurity/staff/<pk>/status/           UpdateAuditStatusView      [Staff]
PATCH  /api/v1/cybersecurity/staff/<pk>/assign/           AssignAuditRequestView     [Staff]
"""

from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from accounts.models import User
from accounts.permissions import IsStaff
from core.utils import api_error, api_success
from .models import AuditRequest, AuditRequestStatus
from .serializers import (
    AuditRequestAssignSerializer,
    AuditRequestCreateSerializer,
    AuditRequestDetailSerializer,
    AuditRequestListSerializer,
    AuditRequestStatusUpdateSerializer,
)


# ─── PUBLIC ───────────────────────────────────────────────────────────────────

class RequestAuditView(APIView):
    """Submit a cybersecurity audit request. Works with or without auth."""

    permission_classes = [AllowAny]

    @extend_schema(request=AuditRequestCreateSerializer, responses={201: AuditRequestDetailSerializer})
    def post(self, request):
        serializer = AuditRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        audit_request = AuditRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            **data,
        )

        return Response(
            api_success(
                AuditRequestDetailSerializer(audit_request).data,
                "Audit request submitted successfully",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── AUTHENTICATED USER ──────────────────────────────────────────────────────

class MyAuditRequestsView(APIView):
    """List the current user's audit requests."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: AuditRequestListSerializer(many=True)})
    def get(self, request):
        qs = AuditRequest.objects.filter(user=request.user, is_deleted=False)
        return Response(
            api_success(AuditRequestListSerializer(qs, many=True).data),
            status=status.HTTP_200_OK,
        )


class MyAuditRequestDetailView(APIView):
    """Get detail of current user's audit request."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: AuditRequestDetailSerializer})
    def get(self, request, pk):
        audit_request = get_object_or_404(
            AuditRequest, pk=pk, user=request.user, is_deleted=False
        )
        return Response(
            api_success(AuditRequestDetailSerializer(audit_request).data),
            status=status.HTTP_200_OK,
        )


# ─── STAFF ────────────────────────────────────────────────────────────────────

class StaffAuditRequestListView(APIView):
    """Staff view — list all audit requests with filtering and search."""

    permission_classes = [IsStaff]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status"),
            OpenApiParameter("audit_type", OpenApiTypes.STR, description="Filter by audit type"),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search reference, org, email"),
            OpenApiParameter("page", OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT),
        ],
        responses={200: AuditRequestListSerializer(many=True)},
    )
    def get(self, request):
        qs = AuditRequest.objects.filter(is_deleted=False)

        # Filters
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        audit_type = request.query_params.get("audit_type")
        if audit_type:
            qs = qs.filter(audit_type=audit_type)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(reference_number__icontains=search)
                | Q(organization__icontains=search)
                | Q(requester_email__icontains=search)
                | Q(requester_name__icontains=search)
            )

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        qs = qs.order_by(ordering)

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        start = (page - 1) * page_size
        total = qs.count()

        results = AuditRequestListSerializer(qs[start : start + page_size], many=True).data

        return Response(
            api_success(
                {
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "results": results,
                }
            ),
            status=status.HTTP_200_OK,
        )


class AuditRequestCountView(APIView):
    """Staff view — return count breakdowns for dashboard cards."""

    permission_classes = [IsStaff]

    def get(self, request):
        qs = AuditRequest.objects.filter(is_deleted=False)
        total = qs.count()
        by_status = {}
        for s in AuditRequestStatus.choices:
            by_status[s[0].lower()] = qs.filter(status=s[0]).count()

        return Response(
            api_success({"total": total, **by_status}),
            status=status.HTTP_200_OK,
        )


class StaffAuditRequestDetailView(APIView):
    """Staff view — get full detail of any audit request."""

    permission_classes = [IsStaff]

    @extend_schema(responses={200: AuditRequestDetailSerializer})
    def get(self, request, pk):
        audit_request = get_object_or_404(AuditRequest, pk=pk, is_deleted=False)
        return Response(
            api_success(AuditRequestDetailSerializer(audit_request).data),
            status=status.HTTP_200_OK,
        )


class UpdateAuditStatusView(APIView):
    """Staff view — transition audit request status."""

    permission_classes = [IsStaff]

    @extend_schema(request=AuditRequestStatusUpdateSerializer, responses={200: AuditRequestDetailSerializer})
    def patch(self, request, pk):
        audit_request = get_object_or_404(AuditRequest, pk=pk, is_deleted=False)
        serializer = AuditRequestStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = serializer.validated_data["status"]
        if not audit_request.can_transition_to(new_status):
            return Response(
                api_error(f"Cannot transition from {audit_request.status} to {new_status}"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if serializer.validated_data.get("staff_notes"):
            audit_request.staff_notes = serializer.validated_data["staff_notes"]
        if serializer.validated_data.get("resolution"):
            audit_request.resolution = serializer.validated_data["resolution"]

        audit_request.transition_status(new_status)

        return Response(
            api_success(
                AuditRequestDetailSerializer(audit_request).data,
                f"Status updated to {new_status}",
            ),
            status=status.HTTP_200_OK,
        )


class AssignAuditRequestView(APIView):
    """Staff view — assign an audit request to a staff member."""

    permission_classes = [IsStaff]

    @extend_schema(request=AuditRequestAssignSerializer, responses={200: AuditRequestDetailSerializer})
    def patch(self, request, pk):
        audit_request = get_object_or_404(AuditRequest, pk=pk, is_deleted=False)
        serializer = AuditRequestAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            staff_user = User.objects.get(pk=serializer.validated_data["assigned_to"])
        except User.DoesNotExist:
            return Response(
                api_error("Staff user not found"),
                status=status.HTTP_404_NOT_FOUND,
            )

        audit_request.assigned_to = staff_user
        audit_request.save(update_fields=["assigned_to", "updated_at"])

        return Response(
            api_success(
                AuditRequestDetailSerializer(audit_request).data,
                "Audit request assigned",
            ),
            status=status.HTTP_200_OK,
        )

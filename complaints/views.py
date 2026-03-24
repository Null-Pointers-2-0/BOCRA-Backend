"""
Complaints API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
POST   /api/v1/complaints/                              SubmitComplaintView        [Public]
GET    /api/v1/complaints/track/                         TrackComplaintView         [Public]
GET    /api/v1/complaints/categories/                    ComplaintCategoriesView    [Public]
GET    /api/v1/complaints/                               MyComplaintsView           [Registered]
GET    /api/v1/complaints/<pk>/                          ComplaintDetailView        [Owner/Staff]
POST   /api/v1/complaints/<pk>/documents/                UploadEvidenceView         [Owner/Staff]
PATCH  /api/v1/complaints/<pk>/assign/                   AssignComplaintView        [Staff]
PATCH  /api/v1/complaints/<pk>/status/                   UpdateComplaintStatusView  [Staff]
POST   /api/v1/complaints/<pk>/notes/                    AddCaseNoteView            [Staff]
POST   /api/v1/complaints/<pk>/resolve/                  ResolveComplaintView       [Staff]
GET    /api/v1/complaints/staff/                         StaffComplaintListView     [Staff]
GET    /api/v1/complaints/staff/<pk>/                    StaffComplaintDetailView   [Staff]
"""

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404

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

from accounts.models import User, UserRole
from accounts.permissions import IsStaff
from core.utils import api_error, api_success
from .models import (
    CaseNote,
    Complaint,
    ComplaintCategory,
    ComplaintDocument,
    ComplaintStatus,
)
from .serializers import (
    AssignSerializer,
    CaseNoteCreateSerializer,
    CaseNoteSerializer,
    ComplaintCategorySerializer,
    ComplaintCreateSerializer,
    ComplaintDetailSerializer,
    ComplaintListSerializer,
    ComplaintTrackSerializer,
    DocumentUploadSerializer,
    ResolveSerializer,
    StaffComplaintDetailSerializer,
    StaffComplaintListSerializer,
    StatusUpdateSerializer,
)
from .tasks import send_complaint_status_email, send_complaint_submitted_email

logger = logging.getLogger(__name__)


# ─── SUBMIT COMPLAINT (Public — anon or authenticated) ────────────────────────

@extend_schema(tags=["Complaints — Public"], summary="Submit a new complaint (anonymous or authenticated)")
class SubmitComplaintView(APIView):
    """
    POST /api/v1/complaints/

    Submit a regulatory complaint. Both anonymous and logged-in users
    can submit. Authenticated users have their name/email auto-populated.
    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = ComplaintCreateSerializer

    def post(self, request):
        serializer = ComplaintCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                api_error("Complaint submission failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        complaint = serializer.save()

        # Fire notification email
        try:
            send_complaint_submitted_email.delay(str(complaint.id))
        except Exception:
            logger.warning("Celery unavailable — skipping complaint submission email.")

        return Response(
            api_success(
                {
                    "id": str(complaint.id),
                    "reference_number": complaint.reference_number,
                    "status": complaint.status,
                    "sla_deadline": complaint.sla_deadline.isoformat() if complaint.sla_deadline else None,
                },
                f"Complaint submitted successfully. Your reference number is {complaint.reference_number}.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── TRACK COMPLAINT (Public — by reference number) ───────────────────────────

@extend_schema(
    tags=["Complaints — Public"],
    summary="Track a complaint by reference number (no login required)",
    parameters=[
        OpenApiParameter(
            "ref",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            description="Complaint reference number (e.g. CMP-2026-000001).",
            required=True,
        ),
    ],
)
class TrackComplaintView(APIView):
    """
    GET /api/v1/complaints/track/?ref=CMP-2026-000001

    Public endpoint — track complaint status by reference number.
    Returns safe public-facing fields only.
    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = ComplaintTrackSerializer

    def get(self, request):
        ref = request.query_params.get("ref", "").strip()
        if not ref:
            return Response(
                api_error("Provide a complaint reference number as ?ref=CMP-..."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        complaint = Complaint.objects.filter(
            reference_number__iexact=ref, is_deleted=False
        ).first()

        if not complaint:
            return Response(
                api_error("No complaint found with that reference number."),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ComplaintTrackSerializer(complaint)
        return Response(
            api_success(serializer.data, "Complaint found."),
            status=status.HTTP_200_OK,
        )


# ─── COMPLAINT CATEGORIES (Public) ────────────────────────────────────────────

@extend_schema(tags=["Complaints — Public"], summary="List all complaint categories")
class ComplaintCategoriesView(APIView):
    """
    GET /api/v1/complaints/categories/

    Returns available complaint categories (enum values).
    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = ComplaintCategorySerializer

    def get(self, request):
        categories = [
            {"value": choice[0], "label": choice[1]}
            for choice in ComplaintCategory.choices
        ]
        return Response(
            api_success(categories, "Complaint categories retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── MY COMPLAINTS (Authenticated complainant) ────────────────────────────────

@extend_schema(tags=["Complaints — Complainant"], summary="List my complaints")
class MyComplaintsView(generics.ListAPIView):
    """
    GET /api/v1/complaints/

    List complaints submitted by the authenticated user.
    Auth: Registered user
    """

    serializer_class = ComplaintListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "category", "priority"]
    ordering_fields = ["created_at", "status", "priority", "sla_deadline"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Complaint.objects.none()
        return Complaint.objects.filter(
            complainant=self.request.user, is_deleted=False
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Complaints retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── COMPLAINT DETAIL (Owner or Staff) ────────────────────────────────────────

@extend_schema(tags=["Complaints — Complainant"], summary="Retrieve complaint details, documents, and timeline")
class ComplaintDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/complaints/<pk>/

    Full complaint detail including documents, status timeline, and notes.
    Auth: Complaint owner or Staff
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if getattr(self, "swagger_fake_view", False):
            return ComplaintDetailSerializer
        user = self.request.user
        if user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return StaffComplaintDetailSerializer
        return ComplaintDetailSerializer

    def get_object(self):
        user = self.request.user
        qs = Complaint.objects.filter(is_deleted=False).select_related(
            "assigned_to", "complainant", "against_licensee"
        ).prefetch_related("documents", "status_logs__changed_by", "notes__author")

        if user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return get_object_or_404(qs, pk=self.kwargs["pk"])
        return get_object_or_404(qs, pk=self.kwargs["pk"], complainant=user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Complaint retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── UPLOAD EVIDENCE ──────────────────────────────────────────────────────────

@extend_schema(tags=["Complaints — Complainant"], summary="Upload evidence to a complaint")
class UploadEvidenceView(APIView):
    """
    POST /api/v1/complaints/<pk>/documents/

    Upload evidence files to a complaint.
    Auth: Complaint owner or Staff
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DocumentUploadSerializer

    def _get_complaint(self, pk, user):
        qs = Complaint.objects.filter(is_deleted=False)
        if user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return get_object_or_404(qs, pk=pk)
        return get_object_or_404(qs, pk=pk, complainant=user)

    def post(self, request, pk):
        complaint = self._get_complaint(pk, request.user)

        # Evidence can be added while the case is still open
        if complaint.status in (ComplaintStatus.CLOSED,):
            return Response(
                api_error("Cannot upload evidence to a closed complaint."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("File upload failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = serializer.validated_data["file"]
        doc = ComplaintDocument.objects.create(
            complaint=complaint,
            name=serializer.validated_data["name"],
            file=uploaded_file,
            file_type=getattr(uploaded_file, "content_type", ""),
            file_size=uploaded_file.size,
            uploaded_by=request.user,
        )
        return Response(
            api_success(
                {"id": str(doc.id), "name": doc.name},
                "Evidence uploaded successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── ASSIGN CASE HANDLER (Staff) ──────────────────────────────────────────────

@extend_schema(tags=["Complaints — Staff"], summary="Assign a staff member as case handler")
class AssignComplaintView(APIView):
    """
    PATCH /api/v1/complaints/<pk>/assign/

    Assign a BOCRA staff member to handle this complaint.
    Auto-transitions status from SUBMITTED → ASSIGNED.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = AssignSerializer

    def patch(self, request, pk):
        complaint = get_object_or_404(
            Complaint.objects.select_related("assigned_to"),
            pk=pk,
            is_deleted=False,
        )

        serializer = AssignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Assignment failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        assigned_user = User.objects.get(id=serializer.validated_data["assigned_to"])

        with transaction.atomic():
            complaint.assigned_to = assigned_user
            complaint.save(update_fields=["assigned_to", "updated_at"])

            # Auto-transition to ASSIGNED if currently SUBMITTED
            if complaint.status == ComplaintStatus.SUBMITTED:
                complaint.transition_status(
                    ComplaintStatus.ASSIGNED,
                    changed_by=request.user,
                    reason=f"Assigned to {assigned_user.get_full_name() or assigned_user.email}.",
                )

        try:
            send_complaint_status_email.delay(str(complaint.id), complaint.status)
        except Exception:
            logger.warning("Celery unavailable — skipping assignment email.")

        return Response(
            api_success(
                {
                    "assigned_to": str(assigned_user.id),
                    "assigned_to_name": assigned_user.get_full_name() or assigned_user.email,
                    "status": complaint.status,
                },
                f"Complaint assigned to {assigned_user.get_full_name() or assigned_user.email}.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── UPDATE COMPLAINT STATUS (Staff) ──────────────────────────────────────────

@extend_schema(tags=["Complaints — Staff"], summary="Update complaint status (staff state machine)")
class UpdateComplaintStatusView(APIView):
    """
    PATCH /api/v1/complaints/<pk>/status/

    Staff drives the complaint state machine.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = StatusUpdateSerializer

    def patch(self, request, pk):
        complaint = get_object_or_404(
            Complaint, pk=pk, is_deleted=False
        )

        serializer = StatusUpdateSerializer(
            data=request.data,
            context={"complaint": complaint, "request": request},
        )
        if not serializer.is_valid():
            return Response(
                api_error("Status update failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = serializer.validated_data["status"]
        reason = serializer.validated_data.get("reason", "")

        with transaction.atomic():
            complaint.transition_status(
                new_status, changed_by=request.user, reason=reason
            )

        try:
            send_complaint_status_email.delay(str(complaint.id), new_status)
        except Exception:
            logger.warning("Celery unavailable — skipping status change email.")

        return Response(
            api_success(
                {"status": new_status},
                f"Complaint status updated to '{complaint.get_status_display()}'.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── ADD CASE NOTE (Staff) ────────────────────────────────────────────────────

@extend_schema(tags=["Complaints — Staff"], summary="Add an internal case note to a complaint")
class AddCaseNoteView(APIView):
    """
    POST /api/v1/complaints/<pk>/notes/

    Staff adds a case note (internal or visible to complainant).
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = CaseNoteCreateSerializer

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk, is_deleted=False)

        serializer = CaseNoteCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Failed to add note.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        note = CaseNote.objects.create(
            complaint=complaint,
            author=request.user,
            content=serializer.validated_data["content"],
            is_internal=serializer.validated_data.get("is_internal", True),
        )

        return Response(
            api_success(
                CaseNoteSerializer(note).data,
                "Case note added successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── RESOLVE COMPLAINT (Staff) ────────────────────────────────────────────────

@extend_schema(tags=["Complaints — Staff"], summary="Submit a formal resolution for the complaint")
class ResolveComplaintView(APIView):
    """
    POST /api/v1/complaints/<pk>/resolve/

    Staff submits a formal resolution. Auto-transitions to RESOLVED.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = ResolveSerializer

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk, is_deleted=False)

        if not complaint.can_transition_to(ComplaintStatus.RESOLVED):
            return Response(
                api_error(
                    f"Cannot resolve a complaint in '{complaint.get_status_display()}' status. "
                    f"Must be in 'Investigating' or 'Awaiting Response'."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResolveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Resolution failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            complaint.resolution = serializer.validated_data["resolution"]
            complaint.save(update_fields=["resolution", "updated_at"])
            complaint.transition_status(
                ComplaintStatus.RESOLVED,
                changed_by=request.user,
                reason="Formal resolution submitted.",
            )

        try:
            send_complaint_status_email.delay(str(complaint.id), ComplaintStatus.RESOLVED)
        except Exception:
            logger.warning("Celery unavailable — skipping resolution email.")

        return Response(
            api_success(
                {"status": complaint.status, "resolved_at": complaint.resolved_at.isoformat()},
                "Complaint resolved successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── STAFF COMPLAINT QUEUE ────────────────────────────────────────────────────

@extend_schema(tags=["Complaints — Staff"], summary="List all complaints across all users (staff queue)")
class StaffComplaintListView(generics.ListAPIView):
    """
    GET /api/v1/complaints/staff/

    Staff view — all complaints, filterable by status, category, priority.
    Auth: Staff
    """

    serializer_class = StaffComplaintListSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "category", "priority", "assigned_to"]
    search_fields = [
        "reference_number", "subject", "against_operator_name",
        "complainant_name", "complainant_email",
    ]
    ordering_fields = [
        "created_at", "status", "priority", "sla_deadline", "category",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Complaint.objects.filter(is_deleted=False).select_related(
            "assigned_to", "complainant", "against_licensee"
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Complaints retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF COMPLAINT DETAIL ───────────────────────────────────────────────────

@extend_schema(tags=["Complaints — Staff"], summary="Retrieve any complaint with internal notes (staff)")
class StaffComplaintDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/complaints/staff/<pk>/

    Staff full view including internal case notes.
    Auth: Staff
    """

    serializer_class = StaffComplaintDetailSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return Complaint.objects.filter(is_deleted=False).select_related(
            "assigned_to", "complainant", "against_licensee"
        ).prefetch_related("documents", "status_logs__changed_by", "notes__author")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Complaint retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── COMPLAINT COUNTS ─────────────────────────────────────────────────────────

@extend_schema(
    tags=["Complaints — Staff"],
    summary="Get complaint counts by status (staff)",
    responses={200: OpenApiTypes.OBJECT},
)
class ComplaintCountView(generics.GenericAPIView):
    """
    GET /api/v1/complaints/staff/counts/

    Quick badge counts for the admin UI sidebar.
    Returns total active complaints and breakdown by status.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = StaffComplaintListSerializer  # schema placeholder

    def get(self, request):
        qs = Complaint.objects.filter(is_deleted=False)
        total = qs.count()
        new = qs.filter(status=ComplaintStatus.SUBMITTED).count()
        active = qs.exclude(
            status__in=[ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]
        ).count()
        return Response(
            api_success(
                {"total": total, "new": new, "active": active},
                "Complaint counts retrieved.",
            ),
            status=status.HTTP_200_OK,
        )

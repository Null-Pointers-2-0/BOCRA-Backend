"""
Tenders API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
GET    /api/v1/tenders/                                    PublicTenderListView          [Public]
GET    /api/v1/tenders/categories/                         TenderCategoriesView          [Public]
GET    /api/v1/tenders/<pk>/                               PublicTenderDetailView        [Public]
GET    /api/v1/tenders/<pk>/documents/<doc_pk>/download/   TenderDocumentDownloadView    [Public]
POST   /api/v1/tenders/staff/                              StaffTenderCreateView         [Staff]
GET    /api/v1/tenders/staff/list/                         StaffTenderListView           [Staff]
GET    /api/v1/tenders/staff/<pk>/                         StaffTenderDetailView         [Staff]
PATCH  /api/v1/tenders/staff/<pk>/edit/                    StaffTenderUpdateView         [Staff]
PATCH  /api/v1/tenders/staff/<pk>/publish/                 PublishTenderView             [Staff]
PATCH  /api/v1/tenders/staff/<pk>/close/                   CloseTenderView               [Staff]
POST   /api/v1/tenders/staff/<pk>/documents/               UploadTenderDocumentView      [Staff]
POST   /api/v1/tenders/staff/<pk>/addenda/                 AddTenderAddendumView         [Staff]
POST   /api/v1/tenders/staff/<pk>/award/                   AwardTenderView               [Staff]
DELETE /api/v1/tenders/staff/<pk>/delete/                  DeleteTenderView              [Staff]
"""

import logging

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, serializers as drf_serializers, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiTypes

from apps.accounts.models import User
from apps.accounts.permissions import IsStaff
from core.utils import api_error, api_success
from .models import (
    Tender,
    TenderAddendum,
    TenderAward,
    TenderCategory,
    TenderDocument,
    TenderStatus,
)
from .serializers import (
    PublicTenderDetailSerializer,
    PublicTenderListSerializer,
    StaffTenderCreateSerializer,
    StaffTenderDetailSerializer,
    StaffTenderListSerializer,
    StaffTenderUpdateSerializer,
    TenderAddendumCreateSerializer,
    TenderAddendumSerializer,
    TenderAwardCreateSerializer,
    TenderDocumentUploadSerializer,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── CATEGORY LIST ────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Tenders — Public"],
    summary="List tender categories",
    responses={200: OpenApiTypes.OBJECT},
)
class TenderCategoriesView(APIView):
    """
    GET /api/v1/tenders/categories/

    Returns all available tender categories.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        categories = [
            {"value": c.value, "label": c.label}
            for c in TenderCategory
        ]
        return Response(
            api_success(categories, "Tender categories retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Public"], summary="List open / public tenders")
class PublicTenderListView(generics.ListAPIView):
    """
    GET /api/v1/tenders/

    Browse published tenders (OPEN, CLOSING_SOON, CLOSED, AWARDED).
    Supports search, filter, and ordering.
    Auth: Public
    """

    serializer_class = PublicTenderListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "status"]
    search_fields = ["title", "reference_number", "description"]
    ordering_fields = ["closing_date", "opening_date", "title", "created_at"]
    ordering = ["-closing_date"]

    PUBLIC_STATUSES = [
        TenderStatus.OPEN,
        TenderStatus.CLOSING_SOON,
        TenderStatus.CLOSED,
        TenderStatus.AWARDED,
    ]

    def get_queryset(self):
        return Tender.objects.filter(
            is_deleted=False, status__in=self.PUBLIC_STATUSES
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Tenders retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Public"], summary="Retrieve tender details")
class PublicTenderDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/tenders/<pk>/

    Full detail of a public tender, including documents, addenda, and award info.
    Auth: Public
    """

    serializer_class = PublicTenderDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "pk"

    PUBLIC_STATUSES = [
        TenderStatus.OPEN,
        TenderStatus.CLOSING_SOON,
        TenderStatus.CLOSED,
        TenderStatus.AWARDED,
    ]

    def get_queryset(self):
        return Tender.objects.filter(
            is_deleted=False, status__in=self.PUBLIC_STATUSES
        ).prefetch_related("documents", "addenda", "award")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Tender retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── DOCUMENT DOWNLOAD ───────────────────────────────────────────────────────

@extend_schema(
    tags=["Tenders — Public"],
    summary="Download a tender document",
    responses={200: OpenApiTypes.BINARY},
)
class TenderDocumentDownloadView(APIView):
    """
    GET /api/v1/tenders/<pk>/documents/<doc_pk>/download/

    Stream a tender document file.
    Auth: Public
    """

    permission_classes = [AllowAny]

    PUBLIC_STATUSES = [
        TenderStatus.OPEN,
        TenderStatus.CLOSING_SOON,
        TenderStatus.CLOSED,
        TenderStatus.AWARDED,
    ]

    def get(self, request, pk, doc_pk):
        tender = get_object_or_404(
            Tender, pk=pk, is_deleted=False, status__in=self.PUBLIC_STATUSES
        )
        doc = get_object_or_404(
            TenderDocument, pk=doc_pk, tender=tender, is_deleted=False
        )
        if not doc.file:
            return Response(
                api_error("No file available for this document."),
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(
            doc.file.open("rb"),
            as_attachment=True,
            filename=doc.file.name.split("/")[-1],
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── STAFF CREATE ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Staff"], summary="Create a new tender (draft)")
class StaffTenderCreateView(generics.CreateAPIView):
    """
    POST /api/v1/tenders/staff/

    Create a new tender in DRAFT status.
    Auth: Staff
    """

    serializer_class = StaffTenderCreateSerializer
    permission_classes = [IsStaff]

    def perform_create(self, serializer):
        instance = serializer.save()
        instance._current_user = self.request.user
        instance.created_by = self.request.user
        instance.modified_by = self.request.user
        instance.save(update_fields=["created_by", "modified_by"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            api_success(
                StaffTenderDetailSerializer(serializer.instance).data,
                "Tender created successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Staff"], summary="List all tenders (staff)")
class StaffTenderListView(generics.ListAPIView):
    """
    GET /api/v1/tenders/staff/list/

    List all tenders including drafts and cancelled.
    Auth: Staff
    """

    serializer_class = StaffTenderListSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "status"]
    search_fields = ["title", "reference_number", "description"]
    ordering_fields = ["closing_date", "opening_date", "title", "created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Tender.objects.filter(is_deleted=False)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Tenders retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Staff"], summary="Retrieve full tender detail (staff)")
class StaffTenderDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/tenders/staff/<pk>/

    Full detail including draft status and audit info.
    Auth: Staff
    """

    serializer_class = StaffTenderDetailSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return Tender.objects.filter(is_deleted=False).prefetch_related(
            "documents", "addenda", "award"
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Tender retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF UPDATE ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Staff"], summary="Update tender fields (staff)")
class StaffTenderUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/v1/tenders/staff/<pk>/edit/

    Update tender fields. Use dedicated endpoints for status transitions.
    Auth: Staff
    """

    serializer_class = StaffTenderUpdateSerializer
    permission_classes = [IsStaff]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Tender.objects.filter(is_deleted=False)

    def perform_update(self, serializer):
        instance = serializer.save()
        instance._current_user = self.request.user
        instance.modified_by = self.request.user
        instance.save(update_fields=["modified_by", "updated_at"])

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            api_success(
                StaffTenderDetailSerializer(instance).data,
                "Tender updated successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── PUBLISH ──────────────────────────────────────────────────────────────────

class PublishTenderView(generics.GenericAPIView):
    """
    PATCH /api/v1/tenders/staff/<pk>/publish/

    Transitions DRAFT → OPEN. Requires closing_date to be set.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Tenders — Staff"], summary="Publish a draft tender (DRAFT → OPEN)", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk, is_deleted=False)
        if tender.status != TenderStatus.DRAFT:
            return Response(
                api_error(f"Cannot publish a tender with status '{tender.get_status_display()}'."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not tender.closing_date:
            return Response(
                api_error("Cannot publish without a closing date."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        tender.status = TenderStatus.OPEN
        if not tender.opening_date:
            tender.opening_date = timezone.now()
        tender._current_user = request.user
        tender.modified_by = request.user
        tender.save()
        logger.info("Tender %s published by %s", tender.pk, request.user.email)
        return Response(
            api_success(
                StaffTenderDetailSerializer(tender).data,
                "Tender published successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── CLOSE ────────────────────────────────────────────────────────────────────

class CloseTenderView(generics.GenericAPIView):
    """
    PATCH /api/v1/tenders/staff/<pk>/close/

    Transitions OPEN or CLOSING_SOON → CLOSED.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Tenders — Staff"], summary="Close a tender (OPEN/CLOSING_SOON → CLOSED)", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk, is_deleted=False)
        if tender.status not in (TenderStatus.OPEN, TenderStatus.CLOSING_SOON):
            return Response(
                api_error(f"Cannot close a tender with status '{tender.get_status_display()}'."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        tender.status = TenderStatus.CLOSED
        tender._current_user = request.user
        tender.modified_by = request.user
        tender.save()
        logger.info("Tender %s closed by %s", tender.pk, request.user.email)
        return Response(
            api_success(
                StaffTenderDetailSerializer(tender).data,
                "Tender closed successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── UPLOAD DOCUMENT ──────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Staff"], summary="Upload a document to a tender")
class UploadTenderDocumentView(generics.CreateAPIView):
    """
    POST /api/v1/tenders/staff/<pk>/documents/

    Attach a document (RFP, ToR, etc.) to a tender.
    Auth: Staff
    """

    serializer_class = TenderDocumentUploadSerializer
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk, is_deleted=False)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = serializer.save(tender=tender, uploaded_by=request.user)
        return Response(
            api_success(
                {"id": str(doc.id), "title": doc.title, "file": doc.file.url},
                "Document uploaded successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── ADD ADDENDUM ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Tenders — Staff"], summary="Add a clarification/addendum to a tender")
class AddTenderAddendumView(generics.CreateAPIView):
    """
    POST /api/v1/tenders/staff/<pk>/addenda/

    Publish a clarification or amendment to a tender.
    Auth: Staff
    """

    serializer_class = TenderAddendumCreateSerializer
    permission_classes = [IsStaff]

    def create(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk, is_deleted=False)
        if tender.status not in (TenderStatus.OPEN, TenderStatus.CLOSING_SOON):
            return Response(
                api_error("Addenda can only be added to open tenders."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        addendum = serializer.save(tender=tender, author=request.user)
        return Response(
            api_success(
                TenderAddendumSerializer(addendum).data,
                "Addendum added successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── AWARD ────────────────────────────────────────────────────────────────────

class AwardTenderView(generics.GenericAPIView):
    """
    POST /api/v1/tenders/staff/<pk>/award/

    Award a closed tender. Creates the award record and sets status to AWARDED.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = TenderAwardCreateSerializer

    @extend_schema(tags=["Tenders — Staff"], summary="Announce tender award", responses={200: OpenApiTypes.OBJECT})
    def post(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk, is_deleted=False)
        if tender.status != TenderStatus.CLOSED:
            return Response(
                api_error("Only closed tenders can be awarded."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if hasattr(tender, "award") and tender.award:
            return Response(
                api_error("This tender has already been awarded."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TenderAwardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        award = serializer.save(tender=tender, awarded_by=request.user)
        tender.status = TenderStatus.AWARDED
        tender._current_user = request.user
        tender.modified_by = request.user
        tender.save()
        logger.info("Tender %s awarded to %s by %s", tender.pk, award.awardee_name, request.user.email)
        return Response(
            api_success(
                StaffTenderDetailSerializer(tender).data,
                "Tender awarded successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── DELETE (soft) ────────────────────────────────────────────────────────────

class DeleteTenderView(generics.GenericAPIView):
    """
    DELETE /api/v1/tenders/staff/<pk>/delete/

    Soft-deletes a tender.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Tenders — Staff"], summary="Soft-delete a tender", responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk, is_deleted=False)
        tender.soft_delete()
        logger.info("Tender %s deleted by %s", tender.pk, request.user.email)
        return Response(
            api_success(None, "Tender deleted successfully."),
            status=status.HTTP_200_OK,
        )

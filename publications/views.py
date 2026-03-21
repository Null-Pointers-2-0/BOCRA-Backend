"""
Publications API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
GET    /api/v1/publications/                        PublicPublicationListView     [Public]
GET    /api/v1/publications/categories/              PublicationCategoriesView     [Public]
GET    /api/v1/publications/<pk>/                    PublicPublicationDetailView   [Public]
GET    /api/v1/publications/<pk>/download/           PublicationDownloadView       [Public]
POST   /api/v1/publications/staff/                   StaffPublicationCreateView   [Staff]
GET    /api/v1/publications/staff/                   StaffPublicationListView     [Staff]
GET    /api/v1/publications/staff/<pk>/              StaffPublicationDetailView   [Staff]
PATCH  /api/v1/publications/staff/<pk>/              StaffPublicationUpdateView   [Staff]
PATCH  /api/v1/publications/staff/<pk>/publish/      PublishPublicationView       [Staff]
PATCH  /api/v1/publications/staff/<pk>/archive/      ArchivePublicationView       [Staff]
DELETE /api/v1/publications/staff/<pk>/              DeletePublicationView        [Staff]
"""

import logging

from django.db import models
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, serializers as drf_serializers, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiTypes

from accounts.permissions import IsStaff
from core.utils import api_error, api_success
from .models import Publication, PublicationCategory, PublicationStatus
from .serializers import (
    PublicPublicationDetailSerializer,
    PublicPublicationListSerializer,
    StaffPublicationCreateSerializer,
    StaffPublicationDetailSerializer,
    StaffPublicationListSerializer,
    StaffPublicationUpdateSerializer,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── CATEGORY LIST ────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Publications — Public"],
    summary="List publication categories",
    responses={200: OpenApiTypes.OBJECT},
)
class PublicationCategoriesView(APIView):
    """
    GET /api/v1/publications/categories/

    Returns all available publication categories.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        categories = [
            {"value": c.value, "label": c.label}
            for c in PublicationCategory
        ]
        return Response(
            api_success(categories, "Publication categories retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Publications — Public"], summary="List published publications")
class PublicPublicationListView(generics.ListAPIView):
    """
    GET /api/v1/publications/

    Browse published publications. Supports search, filter, and ordering.
    Auth: Public
    """

    serializer_class = PublicPublicationListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "year", "is_featured"]
    search_fields = ["title", "summary"]
    ordering_fields = ["published_date", "title", "download_count", "created_at"]
    ordering = ["-published_date"]

    def get_queryset(self):
        return Publication.objects.filter(
            is_deleted=False, status=PublicationStatus.PUBLISHED
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Publications retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

@extend_schema(tags=["Publications — Public"], summary="Retrieve a published publication")
class PublicPublicationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/publications/<pk>/

    Full detail of a published publication, including attachments.
    Auth: Public
    """

    serializer_class = PublicPublicationDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "pk"

    def get_queryset(self):
        return Publication.objects.filter(
            is_deleted=False, status=PublicationStatus.PUBLISHED
        ).prefetch_related("attachments")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Publication retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC DOWNLOAD ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["Publications — Public"],
    summary="Download publication file",
    responses={200: OpenApiTypes.BINARY},
)
class PublicationDownloadView(APIView):
    """
    GET /api/v1/publications/<pk>/download/

    Stream the primary file. Increments download counter.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request, pk):
        pub = get_object_or_404(
            Publication, pk=pk, is_deleted=False, status=PublicationStatus.PUBLISHED
        )
        if not pub.file:
            return Response(
                api_error("No file available for this publication."),
                status=status.HTTP_404_NOT_FOUND,
            )
        # Increment download count
        Publication.objects.filter(pk=pub.pk).update(
            download_count=models.F("download_count") + 1
        )
        return FileResponse(
            pub.file.open("rb"),
            as_attachment=True,
            filename=pub.file.name.split("/")[-1],
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── STAFF CREATE ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Publications — Staff"], summary="Create a new publication (draft)")
class StaffPublicationCreateView(generics.CreateAPIView):
    """
    POST /api/v1/publications/staff/

    Create a new publication in DRAFT status.
    Auth: Staff
    """

    serializer_class = StaffPublicationCreateSerializer
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
                StaffPublicationDetailSerializer(serializer.instance).data,
                "Publication created successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

@extend_schema(tags=["Publications — Staff"], summary="List all publications (staff)")
class StaffPublicationListView(generics.ListAPIView):
    """
    GET /api/v1/publications/staff/

    List all publications (including drafts and archived).
    Auth: Staff
    """

    serializer_class = StaffPublicationListSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "status", "year", "is_featured"]
    search_fields = ["title", "summary"]
    ordering_fields = ["published_date", "title", "created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Publication.objects.filter(is_deleted=False)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Publications retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Publications — Staff"], summary="Retrieve full publication detail (staff)")
class StaffPublicationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/publications/staff/<pk>/

    Full detail including draft status and audit info.
    Auth: Staff
    """

    serializer_class = StaffPublicationDetailSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return Publication.objects.filter(is_deleted=False).prefetch_related("attachments")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Publication retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF UPDATE ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Publications — Staff"], summary="Update a publication (staff)")
class StaffPublicationUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/v1/publications/staff/<pk>/

    Update publication fields. Cannot update a published pub's status directly
    — use the publish/archive endpoints.
    Auth: Staff
    """

    serializer_class = StaffPublicationUpdateSerializer
    permission_classes = [IsStaff]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Publication.objects.filter(is_deleted=False)

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
                StaffPublicationDetailSerializer(instance).data,
                "Publication updated successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── PUBLISH ──────────────────────────────────────────────────────────────────

class PublishPublicationView(generics.GenericAPIView):
    """
    PATCH /api/v1/publications/staff/<pk>/publish/

    Transitions DRAFT → PUBLISHED. Sets published_date if not already set.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Publications — Staff"], summary="Publish a draft publication", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        pub = get_object_or_404(Publication, pk=pk, is_deleted=False)
        if pub.status == PublicationStatus.PUBLISHED:
            return Response(
                api_error("Publication is already published."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if pub.status == PublicationStatus.ARCHIVED:
            return Response(
                api_error("Cannot publish an archived publication. Restore to draft first."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        pub.status = PublicationStatus.PUBLISHED
        if not pub.published_date:
            pub.published_date = timezone.now().date()
        if not pub.year:
            pub.year = pub.published_date.year
        pub._current_user = request.user
        pub.modified_by = request.user
        pub.save()
        logger.info("Publication %s published by %s", pub.pk, request.user.email)
        return Response(
            api_success(
                StaffPublicationDetailSerializer(pub).data,
                "Publication published successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── ARCHIVE ──────────────────────────────────────────────────────────────────

class ArchivePublicationView(generics.GenericAPIView):
    """
    PATCH /api/v1/publications/staff/<pk>/archive/

    Transitions PUBLISHED or DRAFT → ARCHIVED.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Publications — Staff"], summary="Archive a publication", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        pub = get_object_or_404(Publication, pk=pk, is_deleted=False)
        if pub.status == PublicationStatus.ARCHIVED:
            return Response(
                api_error("Publication is already archived."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        pub.status = PublicationStatus.ARCHIVED
        pub._current_user = request.user
        pub.modified_by = request.user
        pub.save()
        logger.info("Publication %s archived by %s", pub.pk, request.user.email)
        return Response(
            api_success(
                StaffPublicationDetailSerializer(pub).data,
                "Publication archived successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── DELETE (soft) ────────────────────────────────────────────────────────────

class DeletePublicationView(generics.GenericAPIView):
    """
    DELETE /api/v1/publications/staff/<pk>/

    Soft-deletes a publication.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Publications — Staff"], summary="Soft-delete a publication", responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk):
        pub = get_object_or_404(Publication, pk=pk, is_deleted=False)
        pub.soft_delete()
        logger.info("Publication %s deleted by %s", pub.pk, request.user.email)
        return Response(
            api_success(None, "Publication deleted successfully."),
            status=status.HTTP_200_OK,
        )

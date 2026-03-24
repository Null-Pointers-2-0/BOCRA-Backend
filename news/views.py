"""
News API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
GET    /api/v1/news/categories/                     NewsCategoriesView          [Public]
GET    /api/v1/news/                                PublicArticleListView       [Public]
GET    /api/v1/news/<pk>/                           PublicArticleDetailView     [Public]
POST   /api/v1/news/staff/                          StaffArticleCreateView      [Staff]
GET    /api/v1/news/staff/list/                     StaffArticleListView        [Staff]
GET    /api/v1/news/staff/<pk>/                     StaffArticleDetailView      [Staff]
PATCH  /api/v1/news/staff/<pk>/edit/                StaffArticleUpdateView      [Staff]
PATCH  /api/v1/news/staff/<pk>/publish/             PublishArticleView          [Staff]
PATCH  /api/v1/news/staff/<pk>/archive/             ArchiveArticleView          [Staff]
DELETE /api/v1/news/staff/<pk>/delete/              DeleteArticleView           [Staff]
"""

import logging

from django.db import models
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, serializers as drf_serializers, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiTypes

from apps.accounts.permissions import IsStaff
from core.utils import api_error, api_success
from apps.accounts.models import User
from .models import Article, ArticleStatus, NewsCategory
from .serializers import (
    PublicArticleDetailSerializer,
    PublicArticleListSerializer,
    StaffArticleCreateSerializer,
    StaffArticleDetailSerializer,
    StaffArticleListSerializer,
    StaffArticleUpdateSerializer,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── CATEGORY LIST ────────────────────────────────────────────────────────────

@extend_schema(
    tags=["News — Public"],
    summary="List news categories",
    responses={200: OpenApiTypes.OBJECT},
)
class NewsCategoriesView(APIView):
    """
    GET /api/v1/news/categories/

    Returns all available news categories.
    Auth: Public
    """

    permission_classes = [AllowAny]

    def get(self, request):
        categories = [
            {"value": c.value, "label": c.label}
            for c in NewsCategory
        ]
        return Response(
            api_success(categories, "News categories retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

@extend_schema(tags=["News — Public"], summary="List published articles")
class PublicArticleListView(generics.ListAPIView):
    """
    GET /api/v1/news/

    Browse published news articles. Supports search, filter, and ordering.
    Auth: Public
    """

    serializer_class = PublicArticleListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "is_featured"]
    search_fields = ["title", "excerpt"]
    ordering_fields = ["published_at", "title", "view_count", "created_at"]
    ordering = ["-published_at"]

    def get_queryset(self):
        return Article.objects.filter(
            is_deleted=False, status=ArticleStatus.PUBLISHED
        ).select_related("author")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Articles retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

@extend_schema(tags=["News — Public"], summary="Retrieve a published article")
class PublicArticleDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/news/<pk>/

    Full article detail. Increments view counter.
    Auth: Public
    """

    serializer_class = PublicArticleDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "pk"

    def get_queryset(self):
        return Article.objects.filter(
            is_deleted=False, status=ArticleStatus.PUBLISHED
        ).select_related("author")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count atomically
        Article.objects.filter(pk=instance.pk).update(
            view_count=models.F("view_count") + 1
        )
        instance.refresh_from_db(fields=["view_count"])
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Article retrieved."),
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── STAFF CREATE ─────────────────────────────────────────────────────────────

@extend_schema(tags=["News — Staff"], summary="Create a new article (draft)")
class StaffArticleCreateView(generics.CreateAPIView):
    """
    POST /api/v1/news/staff/

    Create a new article in DRAFT status.
    Auth: Staff
    """

    serializer_class = StaffArticleCreateSerializer
    permission_classes = [IsStaff]

    def perform_create(self, serializer):
        instance = serializer.save(author=self.request.user)
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
                StaffArticleDetailSerializer(serializer.instance).data,
                "Article created successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

@extend_schema(tags=["News — Staff"], summary="List all articles (staff)")
class StaffArticleListView(generics.ListAPIView):
    """
    GET /api/v1/news/staff/list/

    List all articles (including drafts and archived).
    Auth: Staff
    """

    serializer_class = StaffArticleListSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "status", "is_featured"]
    search_fields = ["title", "excerpt"]
    ordering_fields = ["published_at", "title", "created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Article.objects.filter(is_deleted=False).select_related("author")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Articles retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

@extend_schema(tags=["News — Staff"], summary="Retrieve full article detail (staff)")
class StaffArticleDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/news/staff/<pk>/

    Full detail including draft status and audit info.
    Auth: Staff
    """

    serializer_class = StaffArticleDetailSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return Article.objects.filter(is_deleted=False).select_related("author")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Article retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── STAFF UPDATE ─────────────────────────────────────────────────────────────

@extend_schema(tags=["News — Staff"], summary="Update an article (staff)")
class StaffArticleUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/v1/news/staff/<pk>/edit/

    Update article fields.
    Auth: Staff
    """

    serializer_class = StaffArticleUpdateSerializer
    permission_classes = [IsStaff]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Article.objects.filter(is_deleted=False)

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
                StaffArticleDetailSerializer(instance).data,
                "Article updated successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── PUBLISH ──────────────────────────────────────────────────────────────────

class PublishArticleView(generics.GenericAPIView):
    """
    PATCH /api/v1/news/staff/<pk>/publish/

    Transitions DRAFT → PUBLISHED. Sets published_at if not already set.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["News — Staff"], summary="Publish a draft article", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        from django.shortcuts import get_object_or_404

        article = get_object_or_404(Article, pk=pk, is_deleted=False)
        if article.status == ArticleStatus.PUBLISHED:
            return Response(
                api_error("Article is already published."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if article.status == ArticleStatus.ARCHIVED:
            return Response(
                api_error("Cannot publish an archived article. Restore to draft first."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        article.status = ArticleStatus.PUBLISHED
        if not article.published_at:
            article.published_at = timezone.now()
        article._current_user = request.user
        article.modified_by = request.user
        article.save()
        logger.info("Article %s published by %s", article.pk, request.user.email)
        return Response(
            api_success(
                StaffArticleDetailSerializer(article).data,
                "Article published successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── ARCHIVE ──────────────────────────────────────────────────────────────────

class ArchiveArticleView(generics.GenericAPIView):
    """
    PATCH /api/v1/news/staff/<pk>/archive/

    Transitions PUBLISHED or DRAFT → ARCHIVED.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["News — Staff"], summary="Archive an article", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        from django.shortcuts import get_object_or_404

        article = get_object_or_404(Article, pk=pk, is_deleted=False)
        if article.status == ArticleStatus.ARCHIVED:
            return Response(
                api_error("Article is already archived."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        article.status = ArticleStatus.ARCHIVED
        article._current_user = request.user
        article.modified_by = request.user
        article.save()
        logger.info("Article %s archived by %s", article.pk, request.user.email)
        return Response(
            api_success(
                StaffArticleDetailSerializer(article).data,
                "Article archived successfully.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── DELETE (soft) ────────────────────────────────────────────────────────────

class DeleteArticleView(generics.GenericAPIView):
    """
    DELETE /api/v1/news/staff/<pk>/delete/

    Soft-deletes an article.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["News — Staff"], summary="Soft-delete an article", responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk):
        from django.shortcuts import get_object_or_404

        article = get_object_or_404(Article, pk=pk, is_deleted=False)
        article.soft_delete()
        logger.info("Article %s deleted by %s", article.pk, request.user.email)
        return Response(
            api_success(None, "Article deleted successfully."),
            status=status.HTTP_200_OK,
        )

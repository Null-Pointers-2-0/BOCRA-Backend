"""
News serializers.
"""
from rest_framework import serializers

from .models import Article, NewsCategory


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

class PublicArticleListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "excerpt", "category", "category_display",
            "author_name", "featured_image", "published_at", "is_featured",
            "view_count",
        ]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        return obj.author.get_full_name() if obj.author else ""


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

class PublicArticleDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "excerpt", "content", "category",
            "category_display", "author_name", "featured_image",
            "published_at", "is_featured", "view_count", "created_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        return obj.author.get_full_name() if obj.author else ""


# ─── STAFF CREATE ─────────────────────────────────────────────────────────────

class StaffArticleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            "title", "excerpt", "content", "category", "featured_image",
            "is_featured",
        ]

    def validate_category(self, value):
        if value not in NewsCategory.values:
            raise serializers.ValidationError(f"Invalid category: {value}")
        return value


# ─── STAFF UPDATE ─────────────────────────────────────────────────────────────

class StaffArticleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            "title", "excerpt", "content", "category", "featured_image",
            "is_featured",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

class StaffArticleDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    author_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "excerpt", "content", "category",
            "category_display", "status", "status_display", "author_name",
            "featured_image", "published_at", "is_featured", "view_count",
            "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        return obj.author.get_full_name() if obj.author else ""

    def get_created_by_name(self, obj) -> str:
        return obj.created_by.get_full_name() if obj.created_by else ""


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

class StaffArticleListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "category", "category_display",
            "status", "status_display", "author_name", "published_at",
            "is_featured", "view_count", "created_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        return obj.author.get_full_name() if obj.author else ""

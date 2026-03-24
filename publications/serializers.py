"""
Publication serializers.
"""
from rest_framework import serializers

from .models import (
    Publication,
    PublicationAttachment,
    PublicationCategory,
    PublicationStatus,
)


# ─── ATTACHMENT ───────────────────────────────────────────────────────────────

class PublicationAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PublicationAttachment
        fields = [
            "id", "title", "file", "uploaded_by_name", "created_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj) -> str:
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else ""


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

class PublicPublicationListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id", "title", "slug", "summary", "category", "category_display",
            "published_date", "year", "version", "is_featured", "download_count",
        ]
        read_only_fields = fields


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

class PublicPublicationDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    attachments = PublicationAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id", "title", "slug", "summary", "category", "category_display",
            "file", "published_date", "year", "version", "is_featured",
            "download_count", "attachments", "created_at",
        ]
        read_only_fields = fields


# ─── STAFF CREATE / UPDATE ────────────────────────────────────────────────────

class StaffPublicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = [
            "title", "summary", "category", "file", "published_date",
            "version", "is_featured",
        ]
        extra_kwargs = {"file": {"required": False}}

    def validate_category(self, value):
        if value not in PublicationCategory.values:
            raise serializers.ValidationError(f"Invalid category: {value}")
        return value


class StaffPublicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = [
            "title", "summary", "category", "file", "published_date",
            "version", "is_featured",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

class StaffPublicationDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    attachments = PublicationAttachmentSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = [
            "id", "title", "slug", "summary", "category", "category_display",
            "status", "status_display", "file", "published_date", "year",
            "version", "is_featured", "download_count", "attachments",
            "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj) -> str:
        return obj.created_by.get_full_name() if obj.created_by else ""


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

class StaffPublicationListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id", "title", "slug", "category", "category_display",
            "status", "status_display", "published_date", "year",
            "is_featured", "download_count", "created_at",
        ]
        read_only_fields = fields

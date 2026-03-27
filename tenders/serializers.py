"""
Tender serializers.
"""
from rest_framework import serializers

from .models import (
    Tender,
    TenderAddendum,
    TenderApplication,
    TenderAward,
    TenderCategory,
    TenderDocument,
    TenderStatus,
)


# ─── TENDER DOCUMENT ─────────────────────────────────────────────────────────

class TenderDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TenderDocument
        fields = ["id", "title", "file", "uploaded_by_name", "created_at"]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj) -> str:
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else ""


# ─── TENDER ADDENDUM ─────────────────────────────────────────────────────────

class TenderAddendumSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TenderAddendum
        fields = ["id", "title", "content", "author_name", "created_at"]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        return obj.author.get_full_name() if obj.author else ""


class TenderAddendumCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderAddendum
        fields = ["title", "content"]


# ─── TENDER AWARD ─────────────────────────────────────────────────────────────

class TenderAwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderAward
        fields = ["id", "awardee_name", "award_date", "award_amount", "summary", "created_at"]
        read_only_fields = fields


class TenderAwardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderAward
        fields = ["awardee_name", "award_date", "award_amount", "summary"]


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

class PublicTenderListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_until_closing = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tender
        fields = [
            "id", "title", "slug", "reference_number", "category",
            "category_display", "status", "status_display",
            "opening_date", "closing_date", "days_until_closing",
            "budget_range",
        ]
        read_only_fields = fields


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

class PublicTenderDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_until_closing = serializers.IntegerField(read_only=True)
    documents = TenderDocumentSerializer(many=True, read_only=True)
    addenda = TenderAddendumSerializer(many=True, read_only=True)
    award = TenderAwardSerializer(read_only=True)

    class Meta:
        model = Tender
        fields = [
            "id", "title", "slug", "reference_number", "description",
            "category", "category_display", "status", "status_display",
            "opening_date", "closing_date", "days_until_closing",
            "budget_range", "contact_name", "contact_email", "contact_phone",
            "documents", "addenda", "award", "created_at",
        ]
        read_only_fields = fields


# ─── STAFF CREATE / UPDATE ────────────────────────────────────────────────────

class StaffTenderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tender
        fields = [
            "title", "reference_number", "description", "category",
            "opening_date", "closing_date", "budget_range",
            "contact_name", "contact_email", "contact_phone",
        ]

    def validate_category(self, value):
        if value not in TenderCategory.values:
            raise serializers.ValidationError(f"Invalid category: {value}")
        return value


class StaffTenderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tender
        fields = [
            "title", "reference_number", "description", "category",
            "opening_date", "closing_date", "budget_range",
            "contact_name", "contact_email", "contact_phone",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

class StaffTenderDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_until_closing = serializers.IntegerField(read_only=True)
    documents = TenderDocumentSerializer(many=True, read_only=True)
    addenda = TenderAddendumSerializer(many=True, read_only=True)
    award = TenderAwardSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Tender
        fields = [
            "id", "title", "slug", "reference_number", "description",
            "category", "category_display", "status", "status_display",
            "opening_date", "closing_date", "days_until_closing",
            "budget_range", "contact_name", "contact_email", "contact_phone",
            "documents", "addenda", "award",
            "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj) -> str:
        return obj.created_by.get_full_name() if obj.created_by else ""


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

class StaffTenderListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_until_closing = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tender
        fields = [
            "id", "title", "slug", "reference_number", "category",
            "category_display", "status", "status_display",
            "opening_date", "closing_date", "days_until_closing",
            "budget_range", "created_at",
        ]
        read_only_fields = fields


# ─── TENDER DOCUMENT UPLOAD ──────────────────────────────────────────────────

class TenderDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderDocument
        fields = ["title", "file"]


# ─── TENDER APPLICATION ──────────────────────────────────────────────────────

class TenderApplicationCreateSerializer(serializers.Serializer):
    """Serializer for creating a tender application; validated in view."""

    tender = serializers.UUIDField()
    company_name = serializers.CharField(max_length=300)
    company_registration = serializers.CharField(max_length=100, required=False, allow_blank=True)
    contact_person = serializers.CharField(max_length=200)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    proposal_summary = serializers.CharField()


class TenderApplicationListSerializer(serializers.ModelSerializer):
    tender_title = serializers.CharField(source="tender.title", read_only=True)
    tender_reference = serializers.CharField(source="tender.reference_number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TenderApplication
        fields = [
            "id", "reference_number", "tender", "tender_title",
            "tender_reference", "company_name", "status", "status_display",
            "created_at",
        ]
        read_only_fields = fields

"""
Licensing app serializers.

Public
──────
LicenceTypeListSerializer   — lightweight, for list view
LicenceTypeDetailSerializer — full detail including requirements

Applicant
─────────
ApplicationCreateSerializer   — submit a new application
ApplicationListSerializer     — my applications list (lightweight)
ApplicationDetailSerializer   — full detail + timeline + documents
DocumentUploadSerializer      — upload a supporting document
LicenceListSerializer         — my licences list
LicenceDetailSerializer       — full licence detail

Staff
─────
StaffApplicationListSerializer  — all apps queue with extra fields
StatusUpdateSerializer          — drive the state machine
"""
from datetime import date

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from core.utils import validate_botswana_phone_number, format_botswana_phone_number
from .models import (
    Application,
    ApplicationDocument,
    ApplicationStatus,
    ApplicationStatusLog,
    Licence,
    LicenceStatus,
    LicenceType,
)


# ─── LICENCE TYPE ─────────────────────────────────────────────────────────────

class LicenceTypeListSerializer(serializers.ModelSerializer):
    """Compact representation for list views."""

    class Meta:
        model = LicenceType
        fields = [
            "id",
            "name",
            "code",
            "description",
            "fee_amount",
            "fee_currency",
            "validity_period_months",
            "is_active",
        ]


class LicenceTypeDetailSerializer(serializers.ModelSerializer):
    """Full detail including requirements text."""

    class Meta:
        model = LicenceType
        fields = [
            "id",
            "name",
            "code",
            "description",
            "requirements",
            "fee_amount",
            "fee_currency",
            "validity_period_months",
            "is_active",
            "created_at",
            "updated_at",
        ]


# ─── APPLICATION DOCUMENT ─────────────────────────────────────────────────────

class ApplicationDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "name",
            "file",
            "file_type",
            "file_size",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "file_type", "file_size", "uploaded_by_name", "created_at"]

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.email
        return None


class DocumentUploadSerializer(serializers.Serializer):
    """Used to upload a supporting document to an application."""

    name = serializers.CharField(max_length=255)
    file = serializers.FileField()

    ALLOWED_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
    }
    MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    def validate_file(self, value):
        if hasattr(value, "content_type") and value.content_type not in self.ALLOWED_TYPES:
            raise serializers.ValidationError(
                "Unsupported file type. Allowed: PDF, DOC, DOCX, JPG, PNG."
            )
        if value.size > self.MAX_SIZE_BYTES:
            raise serializers.ValidationError("File must be under 50 MB.")
        return value


# ─── APPLICATION STATUS LOG ───────────────────────────────────────────────────

class ApplicationStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()
    from_status_display = serializers.CharField(
        source="get_from_status_display", read_only=True
    )
    to_status_display = serializers.CharField(
        source="get_to_status_display", read_only=True
    )

    class Meta:
        model = ApplicationStatusLog
        fields = [
            "id",
            "from_status",
            "from_status_display",
            "to_status",
            "to_status_display",
            "changed_by_name",
            "reason",
            "changed_at",
        ]

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.email
        return "System"


# ─── APPLICATION (Create / Submit) ────────────────────────────────────────────

class ApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Used when an authenticated user submits a new application.
    Supports both saving as DRAFT and direct submission.
    """

    submit = serializers.BooleanField(
        write_only=True,
        default=False,
        help_text="Set to true to submit immediately; false saves as draft.",
    )

    class Meta:
        model = Application
        fields = [
            "id",
            "reference_number",
            "licence_type",
            "organisation_name",
            "organisation_registration",
            "contact_person",
            "contact_email",
            "contact_phone",
            "description",
            "status",
            "submitted_at",
            "submit",
        ]
        read_only_fields = ["id", "reference_number", "status", "submitted_at"]

    def validate_contact_phone(self, value):
        if value and not validate_botswana_phone_number(value):
            raise serializers.ValidationError(
                "Enter a valid Botswana phone number (e.g. +26771234567 or 71234567)."
            )
        if value:
            return format_botswana_phone_number(value)
        return value

    def validate_licence_type(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "This licence type is not currently available for applications."
            )
        return value

    def create(self, validated_data):
        submit = validated_data.pop("submit", False)
        applicant = self.context["request"].user

        # Auto-generate a reference number
        from .utils import generate_licence_reference
        reference = generate_licence_reference()

        application = Application.objects.create(
            applicant=applicant,
            reference_number=reference,
            status=ApplicationStatus.DRAFT,
            **validated_data,
        )

        if submit:
            application.transition_status(
                ApplicationStatus.SUBMITTED,
                changed_by=applicant,
                reason="Application submitted by applicant.",
            )

        return application


# ─── APPLICATION (List — applicant view) ─────────────────────────────────────

class ApplicationListSerializer(serializers.ModelSerializer):
    licence_type_name = serializers.CharField(source="licence_type.name", read_only=True)
    licence_type_code = serializers.CharField(source="licence_type.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    has_licence = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "reference_number",
            "licence_type_name",
            "licence_type_code",
            "organisation_name",
            "status",
            "status_display",
            "submitted_at",
            "decision_date",
            "has_licence",
            "created_at",
            "updated_at",
        ]

    def get_has_licence(self, obj):
        return hasattr(obj, "licence")


# ─── APPLICATION (Detail — applicant view) ────────────────────────────────────

class ApplicationDetailSerializer(serializers.ModelSerializer):
    licence_type = LicenceTypeListSerializer(read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    status_timeline = ApplicationStatusLogSerializer(
        source="status_logs", many=True, read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    has_licence = serializers.SerializerMethodField()
    licence_id = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "reference_number",
            "licence_type",
            "organisation_name",
            "organisation_registration",
            "contact_person",
            "contact_email",
            "contact_phone",
            "description",
            "status",
            "status_display",
            "submitted_at",
            "decision_date",
            "decision_reason",
            "info_request_message",
            "can_cancel",
            "has_licence",
            "licence_id",
            "documents",
            "status_timeline",
            "created_at",
            "updated_at",
        ]

    def get_can_cancel(self, obj):
        return obj.can_transition_to(ApplicationStatus.CANCELLED)

    def get_has_licence(self, obj):
        return hasattr(obj, "licence")

    def get_licence_id(self, obj):
        if hasattr(obj, "licence"):
            return str(obj.licence.id)
        return None


# ─── APPLICATION (Staff view — includes internal fields) ─────────────────────

class StaffApplicationDetailSerializer(ApplicationDetailSerializer):
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta(ApplicationDetailSerializer.Meta):
        fields = ApplicationDetailSerializer.Meta.fields + [
            "notes",
            "reviewed_by_name",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.email
        return None


class StaffApplicationListSerializer(ApplicationListSerializer):
    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.SerializerMethodField()

    class Meta(ApplicationListSerializer.Meta):
        fields = ApplicationListSerializer.Meta.fields + [
            "applicant_name",
            "applicant_email",
        ]

    def get_applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.email

    def get_applicant_email(self, obj):
        return obj.applicant.email


# ─── STATUS UPDATE (Staff) ────────────────────────────────────────────────────

class StatusUpdateSerializer(serializers.Serializer):
    """Staff endpoint — drive the application state machine."""

    status = serializers.ChoiceField(choices=ApplicationStatus.choices)
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Reason for the status change (required when rejecting).",
    )
    info_request_message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Message to applicant when requesting more information.",
    )
    internal_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Internal staff notes (not visible to applicant).",
    )

    def validate(self, data):
        application = self.context.get("application")
        new_status = data["status"]

        if not application.can_transition_to(new_status):
            raise serializers.ValidationError(
                {
                    "status": (
                        f"Cannot transition from '{application.get_status_display()}' "
                        f"to '{dict(ApplicationStatus.choices)[new_status]}'."
                    )
                }
            )

        if new_status == ApplicationStatus.REJECTED and not data.get("reason"):
            raise serializers.ValidationError(
                {"reason": "A reason is required when rejecting an application."}
            )

        if new_status == ApplicationStatus.INFO_REQUESTED and not data.get("info_request_message"):
            raise serializers.ValidationError(
                {"info_request_message": "A message is required when requesting more information."}
            )

        return data


# ─── LICENCE ──────────────────────────────────────────────────────────────────

class LicenceListSerializer(serializers.ModelSerializer):
    licence_type_name = serializers.CharField(source="licence_type.name", read_only=True)
    licence_type_code = serializers.CharField(source="licence_type.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Licence
        fields = [
            "id",
            "licence_number",
            "licence_type_name",
            "licence_type_code",
            "organisation_name",
            "issued_date",
            "expiry_date",
            "status",
            "status_display",
            "is_expired",
            "days_until_expiry",
        ]


class LicenceDetailSerializer(serializers.ModelSerializer):
    licence_type = LicenceTypeListSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    has_certificate = serializers.SerializerMethodField()
    application_reference = serializers.CharField(
        source="application.reference_number", read_only=True
    )

    class Meta:
        model = Licence
        fields = [
            "id",
            "licence_number",
            "licence_type",
            "organisation_name",
            "holder",
            "issued_date",
            "expiry_date",
            "status",
            "status_display",
            "conditions",
            "is_expired",
            "days_until_expiry",
            "has_certificate",
            "application_reference",
            "created_at",
            "updated_at",
        ]

    def get_has_certificate(self, obj):
        return bool(obj.certificate_file)


class LicenceVerifySerializer(serializers.ModelSerializer):
    """Public verification — minimal safe information only."""

    licence_type_name = serializers.CharField(source="licence_type.name", read_only=True)
    licence_type_code = serializers.CharField(source="licence_type.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Licence
        fields = [
            "licence_number",
            "licence_type_name",
            "licence_type_code",
            "organisation_name",
            "issued_date",
            "expiry_date",
            "status",
            "status_display",
            "is_expired",
        ]

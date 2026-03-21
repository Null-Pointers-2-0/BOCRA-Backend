"""
Complaints app serializers.

Public
──────
ComplaintCreateSerializer         — submit a complaint (anon or authenticated)
ComplaintTrackSerializer          — public tracking by reference number
ComplaintCategorySerializer       — list available categories

Complainant
───────────
ComplaintListSerializer           — my complaints list
ComplaintDetailSerializer         — full detail + timeline + documents + notes

Staff
─────
StaffComplaintListSerializer      — all complaints queue with extra fields
StaffComplaintDetailSerializer    — full detail including internal notes
StatusUpdateSerializer            — drive the complaint state machine
AssignSerializer                  — assign a case handler
ResolveSerializer                 — submit formal resolution
CaseNoteCreateSerializer          — add internal case note
"""
from rest_framework import serializers

from core.utils import validate_botswana_phone_number, format_botswana_phone_number
from .models import (
    CaseNote,
    Complaint,
    ComplaintCategory,
    ComplaintDocument,
    ComplaintPriority,
    ComplaintStatus,
    ComplaintStatusLog,
    SLA_DAYS_BY_PRIORITY,
)


# ─── COMPLAINT DOCUMENT ───────────────────────────────────────────────────────

class ComplaintDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ComplaintDocument
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
    """Upload evidence to a complaint."""

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


# ─── COMPLAINT STATUS LOG ─────────────────────────────────────────────────────

class ComplaintStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()
    from_status_display = serializers.CharField(
        source="get_from_status_display", read_only=True
    )
    to_status_display = serializers.CharField(
        source="get_to_status_display", read_only=True
    )

    class Meta:
        model = ComplaintStatusLog
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


# ─── CASE NOTE ─────────────────────────────────────────────────────────────────

class CaseNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = CaseNote
        fields = [
            "id",
            "content",
            "is_internal",
            "author_name",
            "created_at",
        ]
        read_only_fields = ["id", "author_name", "created_at"]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.email
        return None


class CaseNoteCreateSerializer(serializers.Serializer):
    """Staff adds a case note to a complaint."""

    content = serializers.CharField()
    is_internal = serializers.BooleanField(default=True)


# ─── CATEGORY LIST ─────────────────────────────────────────────────────────────

class ComplaintCategorySerializer(serializers.Serializer):
    """Simple value/label representation of complaint categories."""

    value = serializers.CharField()
    label = serializers.CharField()


# ─── COMPLAINT CREATE (Public — anon or authenticated) ─────────────────────────

class ComplaintCreateSerializer(serializers.ModelSerializer):
    """
    Submit a new complaint. Works for both anonymous and logged-in users.
    If the user is authenticated, complainant_name and complainant_email
    are auto-populated from their account.
    """

    class Meta:
        model = Complaint
        fields = [
            "id",
            "reference_number",
            "complainant_name",
            "complainant_email",
            "complainant_phone",
            "against_operator_name",
            "against_licensee",
            "category",
            "subject",
            "description",
            "priority",
            "status",
            "sla_deadline",
            "created_at",
        ]
        read_only_fields = [
            "id", "reference_number", "status", "sla_deadline", "created_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            self.fields["complainant_name"].required = False
            self.fields["complainant_name"].allow_blank = True
            self.fields["complainant_email"].required = False
            self.fields["complainant_email"].allow_blank = True

    def validate_complainant_phone(self, value):
        if value and not validate_botswana_phone_number(value):
            raise serializers.ValidationError(
                "Enter a valid Botswana phone number (e.g. +26771234567 or 71234567)."
            )
        if value:
            return format_botswana_phone_number(value)
        return value

    def create(self, validated_data):
        from datetime import timedelta
        from django.utils import timezone
        from .utils import generate_complaint_reference

        request = self.context.get("request")

        # Auto-link authenticated user
        if request and request.user and request.user.is_authenticated:
            validated_data["complainant"] = request.user
            if not validated_data.get("complainant_name"):
                validated_data["complainant_name"] = (
                    request.user.get_full_name() or request.user.email
                )
            if not validated_data.get("complainant_email"):
                validated_data["complainant_email"] = request.user.email

        # Generate reference number
        validated_data["reference_number"] = generate_complaint_reference()

        # Auto-calculate SLA deadline
        priority = validated_data.get("priority", ComplaintPriority.MEDIUM)
        sla_days = SLA_DAYS_BY_PRIORITY.get(priority, 14)
        validated_data["sla_deadline"] = timezone.now() + timedelta(days=sla_days)

        return Complaint.objects.create(**validated_data)


# ─── COMPLAINT TRACK (Public — by reference number) ───────────────────────────

class ComplaintTrackSerializer(serializers.ModelSerializer):
    """Public-safe minimal representation for tracking by reference number."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Complaint
        fields = [
            "reference_number",
            "subject",
            "category",
            "category_display",
            "against_operator_name",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "is_overdue",
            "sla_deadline",
            "created_at",
            "resolved_at",
        ]


# ─── COMPLAINT LIST (Authenticated complainant) ───────────────────────────────

class ComplaintListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Complaint
        fields = [
            "id",
            "reference_number",
            "subject",
            "category",
            "category_display",
            "against_operator_name",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "is_overdue",
            "sla_deadline",
            "created_at",
            "resolved_at",
        ]


# ─── COMPLAINT DETAIL (Owner view) ────────────────────────────────────────────

class ComplaintDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    is_overdue = serializers.ReadOnlyField()
    days_until_sla = serializers.ReadOnlyField()
    documents = ComplaintDocumentSerializer(many=True, read_only=True)
    status_timeline = ComplaintStatusLogSerializer(
        source="status_logs", many=True, read_only=True
    )
    # Only non-internal notes for the complainant
    case_notes = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            "id",
            "reference_number",
            "complainant_name",
            "complainant_email",
            "complainant_phone",
            "against_operator_name",
            "against_licensee",
            "category",
            "category_display",
            "subject",
            "description",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "assigned_to_name",
            "resolution",
            "resolved_at",
            "is_overdue",
            "days_until_sla",
            "sla_deadline",
            "documents",
            "status_timeline",
            "case_notes",
            "created_at",
            "updated_at",
        ]

    def get_case_notes(self, obj):
        # Complainant only sees non-internal notes
        notes = obj.notes.filter(is_internal=False, is_deleted=False)
        return CaseNoteSerializer(notes, many=True).data

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.email
        return None


# ─── STAFF VIEWS ───────────────────────────────────────────────────────────────

class StaffComplaintDetailSerializer(ComplaintDetailSerializer):
    """Staff sees all notes including internal ones."""

    class Meta(ComplaintDetailSerializer.Meta):
        pass

    def get_case_notes(self, obj):
        notes = obj.notes.filter(is_deleted=False)
        return CaseNoteSerializer(notes, many=True).data


class StaffComplaintListSerializer(ComplaintListSerializer):
    complainant_name_display = serializers.CharField(
        source="complainant_name", read_only=True
    )
    complainant_email_display = serializers.CharField(
        source="complainant_email", read_only=True
    )
    assigned_to_name = serializers.SerializerMethodField()
    days_until_sla = serializers.ReadOnlyField()

    class Meta(ComplaintListSerializer.Meta):
        fields = ComplaintListSerializer.Meta.fields + [
            "complainant_name_display",
            "complainant_email_display",
            "assigned_to_name",
            "days_until_sla",
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.email
        return None


# ─── STATUS UPDATE (Staff) ────────────────────────────────────────────────────

class StatusUpdateSerializer(serializers.Serializer):
    """Staff endpoint — drive the complaint state machine."""

    status = serializers.ChoiceField(choices=ComplaintStatus.choices)
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Reason for the status change.",
    )

    def validate(self, data):
        complaint = self.context.get("complaint")
        new_status = data["status"]

        if not complaint.can_transition_to(new_status):
            raise serializers.ValidationError(
                {
                    "status": (
                        f"Cannot transition from '{complaint.get_status_display()}' "
                        f"to '{dict(ComplaintStatus.choices)[new_status]}'."
                    )
                }
            )
        return data


# ─── ASSIGN (Staff) ───────────────────────────────────────────────────────────

class AssignSerializer(serializers.Serializer):
    """Assign a staff member as case handler."""

    assigned_to = serializers.UUIDField(help_text="UUID of the staff user to assign.")

    def validate_assigned_to(self, value):
        from accounts.models import User, UserRole
        try:
            user = User.objects.get(id=value, is_deleted=False)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        if user.role not in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            raise serializers.ValidationError("Assigned user must be a staff member.")
        return value


# ─── RESOLVE (Staff) ──────────────────────────────────────────────────────────

class ResolveSerializer(serializers.Serializer):
    """Staff submits a formal resolution for the complaint."""

    resolution = serializers.CharField(help_text="Formal resolution text sent to complainant.")

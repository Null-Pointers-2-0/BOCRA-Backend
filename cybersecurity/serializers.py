"""
Cybersecurity app serializers.
"""
from rest_framework import serializers

from .models import AuditRequest, AuditType


class AuditRequestCreateSerializer(serializers.Serializer):
    """Validates a new audit request submission (anonymous or authenticated)."""

    requester_name = serializers.CharField(max_length=200)
    requester_email = serializers.EmailField()
    requester_phone = serializers.CharField(max_length=20, required=False, default="")
    organization = serializers.CharField(max_length=255)
    audit_type = serializers.ChoiceField(choices=AuditType.choices)
    description = serializers.CharField()
    preferred_date = serializers.DateField(required=False, allow_null=True)


class AuditRequestListSerializer(serializers.ModelSerializer):
    """Compact representation for list views."""

    audit_type_display = serializers.CharField(source="get_audit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AuditRequest
        fields = [
            "id",
            "reference_number",
            "requester_name",
            "requester_email",
            "organization",
            "audit_type",
            "audit_type_display",
            "status",
            "status_display",
            "preferred_date",
            "created_at",
            "updated_at",
        ]


class AuditRequestDetailSerializer(serializers.ModelSerializer):
    """Full audit request detail including staff fields."""

    audit_type_display = serializers.CharField(source="get_audit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditRequest
        fields = [
            "id",
            "reference_number",
            "requester_name",
            "requester_email",
            "requester_phone",
            "organization",
            "audit_type",
            "audit_type_display",
            "description",
            "preferred_date",
            "status",
            "status_display",
            "assigned_to",
            "assigned_to_name",
            "staff_notes",
            "resolution",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.email
        return None


class AuditRequestStatusUpdateSerializer(serializers.Serializer):
    """Validates staff status transitions."""

    status = serializers.ChoiceField(choices=[
        ("UNDER_REVIEW", "Under Review"),
        ("SCHEDULED", "Scheduled"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("REJECTED", "Rejected"),
    ])
    staff_notes = serializers.CharField(required=False, default="")
    resolution = serializers.CharField(required=False, default="")


class AuditRequestAssignSerializer(serializers.Serializer):
    """Validates staff assignment."""

    assigned_to = serializers.UUIDField()

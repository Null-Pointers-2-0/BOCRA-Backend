"""
Domains app serializers.

Public
──────
DomainZoneListSerializer          — zones list for public/applicant views
DomainZoneDetailSerializer        — full zone detail for staff
DomainAvailabilitySerializer      — domain availability check result
DomainWhoisSerializer             — public WHOIS-style lookup

Applicant
─────────
DomainApplicationCreateSerializer — submit a domain application
DomainApplicationListSerializer   — my applications list
DomainApplicationDetailSerializer — full detail + timeline + documents
DomainApplicationDocumentSerializer — uploaded documents
DomainListSerializer              — my domains list
DomainDetailSerializer            — full domain detail

Staff
─────
StaffApplicationListSerializer    — all apps queue with extra fields
StaffApplicationDetailSerializer  — full app detail with internal fields
StaffDomainListSerializer         — all domains in registry
StaffDomainDetailSerializer       — full domain detail with events
DomainStatusUpdateSerializer      — drive the application state machine
StaffDomainUpdateSerializer       — update NS/contacts
StaffDomainReassignSerializer     — transfer ownership
StaffZoneCreateSerializer         — create/update zones
"""
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Domain,
    DomainApplication,
    DomainApplicationDocument,
    DomainApplicationStatus,
    DomainApplicationStatusLog,
    DomainApplicationType,
    DomainEvent,
    DomainStatus,
    DomainZone,
)


# ─── DOMAIN ZONE ──────────────────────────────────────────────────────────────

class DomainZoneListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainZone
        fields = [
            "id",
            "name",
            "code",
            "description",
            "registration_fee",
            "renewal_fee",
            "fee_currency",
            "min_registration_years",
            "max_registration_years",
            "is_restricted",
            "eligibility_criteria",
            "is_active",
        ]


class DomainZoneDetailSerializer(serializers.ModelSerializer):
    domain_count = serializers.SerializerMethodField()

    class Meta:
        model = DomainZone
        fields = [
            "id",
            "name",
            "code",
            "description",
            "registration_fee",
            "renewal_fee",
            "fee_currency",
            "min_registration_years",
            "max_registration_years",
            "is_restricted",
            "eligibility_criteria",
            "is_active",
            "domain_count",
            "created_at",
            "updated_at",
        ]

    def get_domain_count(self, obj):
        return obj.domains.filter(is_deleted=False).count()


class StaffZoneCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainZone
        fields = [
            "name",
            "code",
            "description",
            "registration_fee",
            "renewal_fee",
            "fee_currency",
            "min_registration_years",
            "max_registration_years",
            "is_restricted",
            "eligibility_criteria",
            "is_active",
        ]


# ─── DOMAIN AVAILABILITY ──────────────────────────────────────────────────────

class DomainAvailabilitySerializer(serializers.Serializer):
    """Response serializer for domain availability check."""
    domain_name = serializers.CharField()
    available = serializers.BooleanField()
    zone = DomainZoneListSerializer(allow_null=True)
    message = serializers.CharField()


# ─── DOMAIN WHOIS ─────────────────────────────────────────────────────────────

class DomainWhoisSerializer(serializers.ModelSerializer):
    """Public WHOIS — limited registrant info for active domains."""
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Domain
        fields = [
            "domain_name",
            "zone_name",
            "status",
            "status_display",
            "registrant_name",
            "organisation_name",
            "registered_at",
            "expires_at",
            "nameserver_1",
            "nameserver_2",
        ]


# ─── APPLICATION DOCUMENT ─────────────────────────────────────────────────────

class DomainApplicationDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DomainApplicationDocument
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
    name = serializers.CharField(max_length=200)
    file = serializers.FileField()

    ALLOWED_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
    }
    MAX_SIZE_BYTES = 50 * 1024 * 1024

    def validate_file(self, value):
        if hasattr(value, "content_type") and value.content_type not in self.ALLOWED_TYPES:
            raise serializers.ValidationError(
                "Unsupported file type. Allowed: PDF, DOC, DOCX, JPG, PNG."
            )
        if value.size > self.MAX_SIZE_BYTES:
            raise serializers.ValidationError("File must be under 50 MB.")
        return value


# ─── APPLICATION STATUS LOG ───────────────────────────────────────────────────

class DomainApplicationStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()
    from_status_display = serializers.CharField(source="get_from_status_display", read_only=True)
    to_status_display = serializers.CharField(source="get_to_status_display", read_only=True)

    class Meta:
        model = DomainApplicationStatusLog
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


# ─── APPLICATION CREATE ───────────────────────────────────────────────────────

class DomainApplicationCreateSerializer(serializers.ModelSerializer):
    submit = serializers.BooleanField(
        write_only=True,
        default=False,
        help_text="Set to true to submit immediately; false saves as draft.",
    )

    class Meta:
        model = DomainApplication
        fields = [
            "id",
            "reference_number",
            "application_type",
            "domain_name",
            "zone",
            "registration_period_years",
            "organisation_name",
            "organisation_registration_number",
            "registrant_name",
            "registrant_email",
            "registrant_phone",
            "registrant_address",
            "nameserver_1",
            "nameserver_2",
            "nameserver_3",
            "nameserver_4",
            "tech_contact_name",
            "tech_contact_email",
            "transfer_from_registrant",
            "transfer_auth_code",
            "justification",
            "status",
            "submitted_at",
            "submit",
        ]
        read_only_fields = ["id", "reference_number", "status", "submitted_at"]

    def validate_zone(self, value):
        if not value.is_active:
            raise serializers.ValidationError("This zone is not currently available for registrations.")
        return value

    def validate_domain_name(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Domain name is required.")
        return value

    def validate(self, data):
        zone = data.get("zone")
        domain_name = data.get("domain_name", "")
        app_type = data.get("application_type", DomainApplicationType.REGISTRATION)

        # Ensure domain name ends with the zone suffix
        if zone and domain_name and not domain_name.endswith(zone.name):
            raise serializers.ValidationError(
                {"domain_name": f"Domain name must end with {zone.name}"}
            )

        # For REGISTRATION, check the domain isn't already taken or pending
        if app_type == DomainApplicationType.REGISTRATION:
            if Domain.objects.filter(
                domain_name=domain_name,
                status__in=[DomainStatus.ACTIVE, DomainStatus.SUSPENDED],
                is_deleted=False,
            ).exists():
                raise serializers.ValidationError(
                    {"domain_name": "This domain is already registered."}
                )
            if DomainApplication.objects.filter(
                domain_name=domain_name,
                status__in=[
                    DomainApplicationStatus.DRAFT,
                    DomainApplicationStatus.SUBMITTED,
                    DomainApplicationStatus.UNDER_REVIEW,
                    DomainApplicationStatus.INFO_REQUESTED,
                ],
                is_deleted=False,
            ).exists():
                raise serializers.ValidationError(
                    {"domain_name": "There is already a pending application for this domain."}
                )

        # For TRANSFER, require auth code
        if app_type == DomainApplicationType.TRANSFER:
            if not data.get("transfer_auth_code"):
                raise serializers.ValidationError(
                    {"transfer_auth_code": "Authorization code is required for transfers."}
                )
            if not data.get("transfer_from_registrant"):
                raise serializers.ValidationError(
                    {"transfer_from_registrant": "Current registrant name is required for transfers."}
                )

        return data

    def create(self, validated_data):
        submit = validated_data.pop("submit", False)
        applicant = self.context["request"].user

        from .utils import generate_domain_reference
        reference = generate_domain_reference()

        application = DomainApplication.objects.create(
            applicant=applicant,
            reference_number=reference,
            status=DomainApplicationStatus.DRAFT,
            created_by=applicant,
            **validated_data,
        )

        if submit:
            application.transition_status(
                DomainApplicationStatus.SUBMITTED,
                changed_by=applicant,
                reason="Application submitted by applicant.",
            )

        return application


# ─── APPLICATION LIST (Applicant) ─────────────────────────────────────────────

class DomainApplicationListSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    application_type_display = serializers.CharField(source="get_application_type_display", read_only=True)

    class Meta:
        model = DomainApplication
        fields = [
            "id",
            "reference_number",
            "application_type",
            "application_type_display",
            "domain_name",
            "zone",
            "zone_name",
            "organisation_name",
            "status",
            "status_display",
            "submitted_at",
            "decision_date",
            "created_at",
            "updated_at",
        ]


# ─── APPLICATION DETAIL (Applicant) ───────────────────────────────────────────

class DomainApplicationDetailSerializer(serializers.ModelSerializer):
    zone = DomainZoneListSerializer(read_only=True)
    documents = DomainApplicationDocumentSerializer(many=True, read_only=True)
    status_timeline = DomainApplicationStatusLogSerializer(
        source="status_logs", many=True, read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    application_type_display = serializers.CharField(source="get_application_type_display", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    has_domain = serializers.SerializerMethodField()
    domain_id = serializers.SerializerMethodField()

    class Meta:
        model = DomainApplication
        fields = [
            "id",
            "reference_number",
            "application_type",
            "application_type_display",
            "domain_name",
            "zone",
            "status",
            "status_display",
            "registration_period_years",
            "organisation_name",
            "organisation_registration_number",
            "registrant_name",
            "registrant_email",
            "registrant_phone",
            "registrant_address",
            "nameserver_1",
            "nameserver_2",
            "nameserver_3",
            "nameserver_4",
            "tech_contact_name",
            "tech_contact_email",
            "transfer_from_registrant",
            "transfer_auth_code",
            "justification",
            "submitted_at",
            "decision_date",
            "decision_reason",
            "info_request_message",
            "can_cancel",
            "has_domain",
            "domain_id",
            "documents",
            "status_timeline",
            "created_at",
            "updated_at",
        ]

    def get_can_cancel(self, obj):
        return obj.can_transition_to(DomainApplicationStatus.CANCELLED)

    def get_has_domain(self, obj):
        return hasattr(obj, "domain") and obj.domain is not None

    def get_domain_id(self, obj):
        if hasattr(obj, "domain") and obj.domain:
            return str(obj.domain.id)
        return None


# ─── APPLICATION UPDATE (Applicant — draft only) ──────────────────────────────

class DomainApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainApplication
        fields = [
            "domain_name",
            "zone",
            "registration_period_years",
            "organisation_name",
            "organisation_registration_number",
            "registrant_name",
            "registrant_email",
            "registrant_phone",
            "registrant_address",
            "nameserver_1",
            "nameserver_2",
            "nameserver_3",
            "nameserver_4",
            "tech_contact_name",
            "tech_contact_email",
            "transfer_from_registrant",
            "transfer_auth_code",
            "justification",
        ]


# ─── STAFF APPLICATION (includes internal fields) ─────────────────────────────

class StaffApplicationDetailSerializer(DomainApplicationDetailSerializer):
    reviewed_by_name = serializers.SerializerMethodField()
    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.SerializerMethodField()

    class Meta(DomainApplicationDetailSerializer.Meta):
        fields = DomainApplicationDetailSerializer.Meta.fields + [
            "reviewed_by_name",
            "applicant_name",
            "applicant_email",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.email
        return None

    def get_applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.email

    def get_applicant_email(self, obj):
        return obj.applicant.email


class StaffApplicationListSerializer(DomainApplicationListSerializer):
    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.SerializerMethodField()

    class Meta(DomainApplicationListSerializer.Meta):
        fields = DomainApplicationListSerializer.Meta.fields + [
            "applicant_name",
            "applicant_email",
        ]

    def get_applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.email

    def get_applicant_email(self, obj):
        return obj.applicant.email


# ─── STATUS UPDATE (Staff) ────────────────────────────────────────────────────

class DomainStatusUpdateSerializer(serializers.Serializer):
    """Staff endpoint — drive the application state machine."""
    status = serializers.ChoiceField(choices=DomainApplicationStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    info_request_message = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        application = self.context.get("application")
        new_status = data["status"]

        if not application.can_transition_to(new_status):
            raise serializers.ValidationError(
                {
                    "status": (
                        f"Cannot transition from '{application.get_status_display()}' "
                        f"to '{dict(DomainApplicationStatus.choices)[new_status]}'."
                    )
                }
            )

        if new_status == DomainApplicationStatus.REJECTED and not data.get("reason"):
            raise serializers.ValidationError(
                {"reason": "A reason is required when rejecting an application."}
            )

        if new_status == DomainApplicationStatus.INFO_REQUESTED and not data.get("info_request_message"):
            raise serializers.ValidationError(
                {"info_request_message": "A message is required when requesting more information."}
            )

        return data


# ─── DOMAIN (Applicant) ───────────────────────────────────────────────────────

class DomainListSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Domain
        fields = [
            "id",
            "domain_name",
            "zone",
            "zone_name",
            "status",
            "status_display",
            "organisation_name",
            "registered_at",
            "expires_at",
            "is_expired",
            "days_until_expiry",
        ]


class DomainDetailSerializer(serializers.ModelSerializer):
    zone = DomainZoneListSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Domain
        fields = [
            "id",
            "domain_name",
            "zone",
            "status",
            "status_display",
            "registrant_name",
            "registrant_email",
            "registrant_phone",
            "registrant_address",
            "organisation_name",
            "nameserver_1",
            "nameserver_2",
            "nameserver_3",
            "nameserver_4",
            "tech_contact_name",
            "tech_contact_email",
            "registered_at",
            "expires_at",
            "last_renewed_at",
            "is_expired",
            "days_until_expiry",
            "created_at",
            "updated_at",
        ]


# ─── DOMAIN EVENT ─────────────────────────────────────────────────────────────

class DomainEventSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = DomainEvent
        fields = [
            "id",
            "event_type",
            "event_type_display",
            "description",
            "performed_by_name",
            "metadata",
            "created_at",
        ]

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.get_full_name() or obj.performed_by.email
        return "System"


# ─── STAFF DOMAIN ─────────────────────────────────────────────────────────────

class StaffDomainListSerializer(DomainListSerializer):
    registrant_name = serializers.CharField(read_only=True)
    registrant_email = serializers.CharField(read_only=True)
    is_seeded = serializers.BooleanField(read_only=True)

    class Meta(DomainListSerializer.Meta):
        fields = DomainListSerializer.Meta.fields + [
            "registrant_name",
            "registrant_email",
            "is_seeded",
        ]


class StaffDomainDetailSerializer(DomainDetailSerializer):
    events = DomainEventSerializer(many=True, read_only=True)
    is_seeded = serializers.BooleanField(read_only=True)
    created_from_application_ref = serializers.SerializerMethodField()

    class Meta(DomainDetailSerializer.Meta):
        fields = DomainDetailSerializer.Meta.fields + [
            "is_seeded",
            "created_from_application_ref",
            "events",
        ]

    def get_created_from_application_ref(self, obj):
        if obj.created_from_application:
            return obj.created_from_application.reference_number
        return None


class StaffDomainUpdateSerializer(serializers.Serializer):
    """Update nameservers and contacts on an active domain."""
    nameserver_1 = serializers.CharField(max_length=253, required=False)
    nameserver_2 = serializers.CharField(max_length=253, required=False)
    nameserver_3 = serializers.CharField(max_length=253, required=False, allow_blank=True)
    nameserver_4 = serializers.CharField(max_length=253, required=False, allow_blank=True)
    tech_contact_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    tech_contact_email = serializers.EmailField(required=False, allow_blank=True)
    registrant_name = serializers.CharField(max_length=200, required=False)
    registrant_email = serializers.EmailField(required=False)
    registrant_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    registrant_address = serializers.CharField(required=False, allow_blank=True)
    organisation_name = serializers.CharField(max_length=300, required=False, allow_blank=True)


class StaffDomainReassignSerializer(serializers.Serializer):
    """Transfer domain ownership to another user."""
    new_owner_id = serializers.UUIDField()
    reason = serializers.CharField()

    def validate_new_owner_id(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("User not found or inactive.")
        return value

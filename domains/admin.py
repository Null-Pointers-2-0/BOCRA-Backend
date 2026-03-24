"""
Django Admin configuration for the domains app.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Domain,
    DomainApplication,
    DomainApplicationDocument,
    DomainApplicationStatus,
    DomainApplicationStatusLog,
    DomainEvent,
    DomainStatus,
    DomainZone,
)


# ─── DOMAIN ZONE ──────────────────────────────────────────────────────────────

@admin.register(DomainZone)
class DomainZoneAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "registration_fee", "renewal_fee", "is_restricted", "is_active"]
    list_filter = ["is_active", "is_restricted"]
    search_fields = ["name", "code"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]


# ─── APPLICATION DOCUMENT (inline) ────────────────────────────────────────────

class DomainApplicationDocumentInline(admin.TabularInline):
    model = DomainApplicationDocument
    extra = 0
    readonly_fields = ["file_type", "file_size", "uploaded_by", "created_at"]
    fields = ["name", "file", "file_type", "file_size", "uploaded_by", "created_at"]


# ─── APPLICATION STATUS LOG (inline) ──────────────────────────────────────────

class DomainApplicationStatusLogInline(admin.TabularInline):
    model = DomainApplicationStatusLog
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "reason", "changed_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ─── DOMAIN APPLICATION ───────────────────────────────────────────────────────

@admin.register(DomainApplication)
class DomainApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "reference_number",
        "domain_name",
        "application_type",
        "organisation_name",
        "zone",
        "status_badge",
        "submitted_at",
    ]
    list_filter = ["status", "application_type", "zone", "submitted_at"]
    search_fields = [
        "reference_number", "domain_name", "organisation_name",
        "applicant__email", "applicant__first_name", "applicant__last_name",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["reference_number", "submitted_at", "decision_date", "created_at", "updated_at"]
    inlines = [DomainApplicationDocumentInline, DomainApplicationStatusLogInline]
    fieldsets = [
        ("Application", {
            "fields": [
                "reference_number", "application_type", "applicant",
                "domain_name", "zone", "status", "registration_period_years",
            ],
        }),
        ("Registrant Details", {
            "fields": [
                "organisation_name", "organisation_registration_number",
                "registrant_name", "registrant_email", "registrant_phone", "registrant_address",
            ],
        }),
        ("Technical Details", {
            "fields": [
                "nameserver_1", "nameserver_2", "nameserver_3", "nameserver_4",
                "tech_contact_name", "tech_contact_email",
            ],
        }),
        ("Transfer Details", {
            "fields": ["transfer_from_registrant", "transfer_auth_code"],
            "classes": ["collapse"],
        }),
        ("Review", {
            "fields": [
                "justification", "reviewed_by", "decision_date",
                "decision_reason", "info_request_message",
            ],
        }),
        ("Timestamps", {
            "fields": ["submitted_at", "created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def status_badge(self, obj):
        colour_map = {
            DomainApplicationStatus.DRAFT:          "#6c757d",
            DomainApplicationStatus.SUBMITTED:      "#0d6efd",
            DomainApplicationStatus.UNDER_REVIEW:   "#fd7e14",
            DomainApplicationStatus.INFO_REQUESTED: "#ffc107",
            DomainApplicationStatus.APPROVED:       "#198754",
            DomainApplicationStatus.REJECTED:       "#dc3545",
            DomainApplicationStatus.CANCELLED:      "#adb5bd",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"


# ─── DOMAIN EVENT (inline) ────────────────────────────────────────────────────

class DomainEventInline(admin.TabularInline):
    model = DomainEvent
    extra = 0
    readonly_fields = ["event_type", "description", "performed_by", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ─── DOMAIN ───────────────────────────────────────────────────────────────────

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = [
        "domain_name",
        "zone",
        "organisation_name",
        "status_badge",
        "registered_at",
        "expires_at",
        "is_seeded",
    ]
    list_filter = ["status", "zone", "is_seeded"]
    search_fields = ["domain_name", "organisation_name", "registrant_name", "registrant_email"]
    ordering = ["domain_name"]
    readonly_fields = ["created_at", "updated_at", "registered_at"]
    inlines = [DomainEventInline]
    fieldsets = [
        ("Domain", {
            "fields": ["domain_name", "zone", "status", "is_seeded", "created_from_application"],
        }),
        ("Registrant", {
            "fields": [
                "registrant", "registrant_name", "registrant_email",
                "registrant_phone", "registrant_address", "organisation_name",
            ],
        }),
        ("Technical", {
            "fields": [
                "nameserver_1", "nameserver_2", "nameserver_3", "nameserver_4",
                "tech_contact_name", "tech_contact_email",
            ],
        }),
        ("Dates", {
            "fields": ["registered_at", "expires_at", "last_renewed_at"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def status_badge(self, obj):
        colour_map = {
            DomainStatus.ACTIVE:         "#198754",
            DomainStatus.EXPIRED:        "#dc3545",
            DomainStatus.SUSPENDED:      "#ffc107",
            DomainStatus.PENDING_DELETE: "#fd7e14",
            DomainStatus.DELETED:        "#6c757d",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"


# ─── DOMAIN EVENT ─────────────────────────────────────────────────────────────

@admin.register(DomainEvent)
class DomainEventAdmin(admin.ModelAdmin):
    list_display = ["domain", "event_type", "performed_by", "created_at"]
    list_filter = ["event_type"]
    search_fields = ["domain__domain_name", "description"]
    readonly_fields = ["domain", "event_type", "description", "performed_by", "metadata", "created_at"]

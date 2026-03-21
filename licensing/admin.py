"""
Django Admin configuration for the licensing app.
"""
from django.contrib import admin
from django.utils.html import format_html

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

@admin.register(LicenceType)
class LicenceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "fee_amount", "validity_period_months", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]


# ─── APPLICATION DOCUMENT (inline) ────────────────────────────────────────────

class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    readonly_fields = ["file_type", "file_size", "uploaded_by", "created_at"]
    fields = ["name", "file", "file_type", "file_size", "uploaded_by", "created_at"]


# ─── APPLICATION STATUS LOG (inline) ──────────────────────────────────────────

class ApplicationStatusLogInline(admin.TabularInline):
    model = ApplicationStatusLog
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "reason", "changed_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ─── APPLICATION ──────────────────────────────────────────────────────────────

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "reference_number",
        "organisation_name",
        "licence_type",
        "applicant_email",
        "status_badge",
        "submitted_at",
        "reviewed_by",
    ]
    list_filter = ["status", "licence_type", "submitted_at"]
    search_fields = [
        "reference_number", "organisation_name",
        "applicant__email", "applicant__first_name", "applicant__last_name",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "reference_number", "submitted_at", "decision_date",
        "created_at", "updated_at",
    ]
    inlines = [ApplicationDocumentInline, ApplicationStatusLogInline]
    fieldsets = [
        ("Application", {
            "fields": ["reference_number", "applicant", "licence_type", "renewal_of", "status"],
        }),
        ("Organisation Details", {
            "fields": [
                "organisation_name", "organisation_registration",
                "contact_person", "contact_email", "contact_phone", "description",
            ],
        }),
        ("Review", {
            "fields": [
                "reviewed_by", "notes", "decision_date",
                "decision_reason", "info_request_message",
            ],
        }),
        ("Timestamps", {
            "fields": ["submitted_at", "created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def applicant_email(self, obj):
        return obj.applicant.email
    applicant_email.short_description = "Applicant"

    def status_badge(self, obj):
        colour_map = {
            ApplicationStatus.DRAFT:          "#6c757d",
            ApplicationStatus.SUBMITTED:      "#0d6efd",
            ApplicationStatus.UNDER_REVIEW:   "#fd7e14",
            ApplicationStatus.INFO_REQUESTED: "#ffc107",
            ApplicationStatus.APPROVED:       "#198754",
            ApplicationStatus.REJECTED:       "#dc3545",
            ApplicationStatus.CANCELLED:      "#adb5bd",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    # ── Bulk actions ──────────────────────────────────────────────────────────

    @admin.action(description="Mark selected as Under Review")
    def mark_under_review(self, request, queryset):
        count = 0
        for app in queryset.filter(status=ApplicationStatus.SUBMITTED):
            try:
                app.transition_status(ApplicationStatus.UNDER_REVIEW, changed_by=request.user)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"{count} application(s) moved to Under Review.")

    actions = ["mark_under_review"]


# ─── LICENCE ──────────────────────────────────────────────────────────────────

@admin.register(Licence)
class LicenceAdmin(admin.ModelAdmin):
    list_display = [
        "licence_number",
        "organisation_name",
        "licence_type",
        "holder_email",
        "issued_date",
        "expiry_date",
        "status_badge",
        "days_until_expiry",
    ]
    list_filter = ["status", "licence_type", "issued_date"]
    search_fields = [
        "licence_number", "organisation_name",
        "holder__email",
    ]
    ordering = ["-issued_date"]
    readonly_fields = [
        "licence_number", "issued_date", "expiry_date",
        "created_at", "updated_at", "is_expired", "days_until_expiry",
    ]
    fieldsets = [
        ("Licence", {
            "fields": [
                "licence_number", "licence_type", "application",
                "holder", "organisation_name", "status",
            ],
        }),
        ("Validity", {
            "fields": ["issued_date", "expiry_date", "is_expired", "days_until_expiry"],
        }),
        ("Conditions & Certificate", {
            "fields": ["conditions", "certificate_file"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def holder_email(self, obj):
        return obj.holder.email
    holder_email.short_description = "Holder"

    def status_badge(self, obj):
        colour_map = {
            LicenceStatus.ACTIVE:    "#198754",
            LicenceStatus.SUSPENDED: "#ffc107",
            LicenceStatus.EXPIRED:   "#dc3545",
            LicenceStatus.REVOKED:   "#6c757d",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def days_until_expiry(self, obj):
        days = obj.days_until_expiry
        if days < 0:
            return format_html('<span style="color:red;">Expired {} days ago</span>', abs(days))
        if days <= 90:
            return format_html('<span style="color:orange;">{} days</span>', days)
        return f"{days} days"
    days_until_expiry.short_description = "Expiry"

    # ── Bulk actions ──────────────────────────────────────────────────────────

    @admin.action(description="Suspend selected licences")
    def suspend_licences(self, request, queryset):
        updated = queryset.filter(status=LicenceStatus.ACTIVE).update(status=LicenceStatus.SUSPENDED)
        self.message_user(request, f"{updated} licence(s) suspended.")

    @admin.action(description="Reinstate selected licences (Active)")
    def reinstate_licences(self, request, queryset):
        updated = queryset.filter(status=LicenceStatus.SUSPENDED).update(status=LicenceStatus.ACTIVE)
        self.message_user(request, f"{updated} licence(s) reinstated.")

    actions = ["suspend_licences", "reinstate_licences"]

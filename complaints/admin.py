"""
Django Admin configuration for the complaints app.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CaseNote,
    Complaint,
    ComplaintDocument,
    ComplaintStatus,
    ComplaintStatusLog,
)


# ─── COMPLAINT DOCUMENT (inline) ──────────────────────────────────────────────

class ComplaintDocumentInline(admin.TabularInline):
    model = ComplaintDocument
    extra = 0
    readonly_fields = ["file_type", "file_size", "uploaded_by", "created_at"]
    fields = ["name", "file", "file_type", "file_size", "uploaded_by", "created_at"]


# ─── COMPLAINT STATUS LOG (inline) ────────────────────────────────────────────

class ComplaintStatusLogInline(admin.TabularInline):
    model = ComplaintStatusLog
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "reason", "changed_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ─── CASE NOTES (inline) ──────────────────────────────────────────────────────

class CaseNoteInline(admin.TabularInline):
    model = CaseNote
    extra = 0
    readonly_fields = ["author", "is_internal", "created_at"]
    fields = ["content", "is_internal", "author", "created_at"]


# ─── COMPLAINT ─────────────────────────────────────────────────────────────────

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = [
        "reference_number",
        "subject",
        "category",
        "against_operator_name",
        "complainant_name",
        "status_badge",
        "priority_badge",
        "assigned_to_name",
        "sla_status",
        "created_at",
    ]
    list_filter = ["status", "category", "priority", "created_at"]
    search_fields = [
        "reference_number", "subject", "against_operator_name",
        "complainant_name", "complainant_email",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "reference_number", "sla_deadline", "resolved_at",
        "created_at", "updated_at",
    ]
    inlines = [ComplaintDocumentInline, CaseNoteInline, ComplaintStatusLogInline]
    fieldsets = [
        ("Complaint", {
            "fields": [
                "reference_number", "category", "subject", "description",
                "priority", "status",
            ],
        }),
        ("Complainant", {
            "fields": [
                "complainant", "complainant_name",
                "complainant_email", "complainant_phone",
            ],
        }),
        ("Against", {
            "fields": ["against_operator_name", "against_licensee"],
        }),
        ("Case Management", {
            "fields": ["assigned_to", "resolution", "resolved_at", "sla_deadline"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def complainant_display(self, obj):
        return obj.complainant_name or "Anonymous"
    complainant_display.short_description = "Complainant"

    def assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.email
        return "—"
    assigned_to_name.short_description = "Handler"

    def status_badge(self, obj):
        colour_map = {
            ComplaintStatus.SUBMITTED:         "#0d6efd",
            ComplaintStatus.ASSIGNED:          "#6f42c1",
            ComplaintStatus.INVESTIGATING:     "#fd7e14",
            ComplaintStatus.AWAITING_RESPONSE: "#ffc107",
            ComplaintStatus.RESOLVED:          "#198754",
            ComplaintStatus.CLOSED:            "#adb5bd",
            ComplaintStatus.REOPENED:          "#dc3545",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def priority_badge(self, obj):
        colour_map = {
            "LOW":    "#198754",
            "MEDIUM": "#ffc107",
            "HIGH":   "#fd7e14",
            "URGENT": "#dc3545",
        }
        colour = colour_map.get(obj.priority, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_priority_display(),
        )
    priority_badge.short_description = "Priority"

    def sla_status(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="background:#dc3545;color:#fff;padding:2px 8px;border-radius:4px;">OVERDUE</span>'
            )
        if obj.days_until_sla is not None and obj.days_until_sla <= 3:
            return format_html(
                '<span style="background:#ffc107;color:#000;padding:2px 8px;border-radius:4px;">{} days</span>',
                obj.days_until_sla,
            )
        if obj.days_until_sla is not None:
            return f"{obj.days_until_sla} days"
        return "—"
    sla_status.short_description = "SLA"

    # ── Bulk actions ──────────────────────────────────────────────────────────

    @admin.action(description="Mark selected as Assigned (to me)")
    def assign_to_me(self, request, queryset):
        count = 0
        for complaint in queryset.filter(status=ComplaintStatus.SUBMITTED):
            try:
                complaint.assigned_to = request.user
                complaint.save(update_fields=["assigned_to", "updated_at"])
                complaint.transition_status(
                    ComplaintStatus.ASSIGNED,
                    changed_by=request.user,
                    reason=f"Assigned to {request.user.get_full_name() or request.user.email} via admin.",
                )
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"{count} complaint(s) assigned to you.")

    actions = ["assign_to_me"]

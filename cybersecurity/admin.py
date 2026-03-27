from django.contrib import admin

from .models import AuditRequest


@admin.register(AuditRequest)
class AuditRequestAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "organization",
        "audit_type",
        "status",
        "requester_name",
        "requester_email",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "audit_type", "created_at")
    search_fields = ("reference_number", "organization", "requester_name", "requester_email")
    readonly_fields = ("reference_number", "created_at", "updated_at", "completed_at")
    ordering = ("-created_at",)

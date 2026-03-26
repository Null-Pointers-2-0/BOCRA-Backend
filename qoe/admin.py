from django.contrib import admin

from .models import QoEReport


@admin.register(QoEReport)
class QoEReportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "operator",
        "service_type",
        "connection_type",
        "rating",
        "download_speed",
        "district",
        "submitted_at",
        "is_verified",
        "is_flagged",
    ]
    list_filter = [
        "connection_type",
        "service_type",
        "rating",
        "is_verified",
        "is_flagged",
        "operator",
    ]
    search_fields = ["description", "operator__name", "district__name"]
    ordering = ["-submitted_at"]
    raw_id_fields = ["operator", "district", "submitted_by"]
    readonly_fields = ["ip_hash", "submitted_at", "created_at", "updated_at"]

"""
Django Admin configuration for the analytics app.
"""
from django.contrib import admin

from .models import NetworkOperator, QoSRecord, TelecomsStat


@admin.register(NetworkOperator)
class NetworkOperatorAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    ordering = ["name"]


@admin.register(TelecomsStat)
class TelecomsStatAdmin(admin.ModelAdmin):
    list_display = [
        "operator", "period", "technology",
        "subscriber_count", "market_share_percent", "revenue",
    ]
    list_filter = ["operator", "technology", "period"]
    ordering = ["-period", "operator__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(QoSRecord)
class QoSRecordAdmin(admin.ModelAdmin):
    list_display = [
        "operator", "period", "metric_type",
        "value", "unit", "benchmark", "meets_benchmark",
    ]
    list_filter = ["operator", "metric_type", "period"]
    ordering = ["-period", "operator__name"]
    readonly_fields = ["created_at", "updated_at"]

from django.contrib import admin

from .models import ManualMetricEntry, OperatorScore, ScorecardWeightConfig


@admin.register(ScorecardWeightConfig)
class ScorecardWeightConfigAdmin(admin.ModelAdmin):
    list_display = ["dimension", "weight", "description", "updated_at"]
    list_editable = ["weight"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(OperatorScore)
class OperatorScoreAdmin(admin.ModelAdmin):
    list_display = [
        "operator", "period", "composite_score", "rank",
        "coverage_score", "qoe_score", "complaints_score", "qos_score",
    ]
    list_filter = ["period", "operator", "rank"]
    search_fields = ["operator__name", "operator__code"]
    raw_id_fields = ["operator"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-period", "rank"]


@admin.register(ManualMetricEntry)
class ManualMetricEntryAdmin(admin.ModelAdmin):
    list_display = ["operator", "period", "metric_name", "value", "unit", "entered_by"]
    list_filter = ["period", "operator", "metric_name"]
    search_fields = ["operator__name", "operator__code", "metric_name"]
    raw_id_fields = ["operator", "entered_by"]
    readonly_fields = ["id", "created_at", "updated_at"]

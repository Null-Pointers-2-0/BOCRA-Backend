from django.contrib import admin

from .models import CoverageArea, CoverageUpload, District


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "region", "population", "is_active"]
    list_filter = ["region", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["name"]


@admin.register(CoverageArea)
class CoverageAreaAdmin(admin.ModelAdmin):
    list_display = [
        "operator",
        "district",
        "technology",
        "coverage_level",
        "coverage_percentage",
        "period",
        "source",
    ]
    list_filter = ["technology", "coverage_level", "source", "period", "operator"]
    search_fields = ["district__name", "operator__name"]
    ordering = ["-period", "operator__name"]
    raw_id_fields = ["operator", "district"]


@admin.register(CoverageUpload)
class CoverageUploadAdmin(admin.ModelAdmin):
    list_display = [
        "operator",
        "technology",
        "period",
        "status",
        "records_created",
        "created_at",
    ]
    list_filter = ["status", "technology", "operator"]
    ordering = ["-created_at"]
    raw_id_fields = ["operator", "created_by", "modified_by"]

"""
URL configuration for the coverages app.

All routes are mounted under /api/v1/coverages/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    CoverageAreaGeoJSONView,
    CoverageAreaListView,
    CoverageCompareView,
    CoverageOperatorListView,
    CoverageStatsView,
    CoverageSummaryView,
    CoverageUploadCreateView,
    CoverageUploadListView,
    DistrictCoverageSummaryView,
    DistrictDetailView,
    DistrictGeoJSONView,
    DistrictListView,
)

app_name = "coverages"

urlpatterns = [
    # -- Districts -------------------------------------------------------------
    path("districts/", DistrictListView.as_view(), name="district-list"),
    path("districts/geojson/", DistrictGeoJSONView.as_view(), name="district-geojson"),
    path("districts/<uuid:pk>/", DistrictDetailView.as_view(), name="district-detail"),

    # -- Operators -------------------------------------------------------------
    path("operators/", CoverageOperatorListView.as_view(), name="coverage-operators"),

    # -- Coverage areas --------------------------------------------------------
    path("areas/", CoverageAreaListView.as_view(), name="coverage-area-list"),
    path("areas/geojson/", CoverageAreaGeoJSONView.as_view(), name="coverage-area-geojson"),

    # -- Summaries -------------------------------------------------------------
    path("summary/", CoverageSummaryView.as_view(), name="coverage-summary"),
    path("summary/<uuid:district_id>/", DistrictCoverageSummaryView.as_view(), name="district-coverage-summary"),

    # -- Comparison ------------------------------------------------------------
    path("compare/", CoverageCompareView.as_view(), name="coverage-compare"),

    # -- Uploads (Staff/Admin) -------------------------------------------------
    path("upload/", CoverageUploadCreateView.as_view(), name="coverage-upload-create"),
    path("uploads/", CoverageUploadListView.as_view(), name="coverage-upload-list"),

    # -- Stats (Staff) ---------------------------------------------------------
    path("stats/", CoverageStatsView.as_view(), name="coverage-stats"),
]

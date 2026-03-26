"""
URL configuration for the qoe app.

All routes are mounted under /api/v1/qoe/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    PingView,
    QoEAnalyticsView,
    QoEDistrictsView,
    QoEHeatmapView,
    QoEReportCreateView,
    QoEReportDetailView,
    QoEReportListView,
    QoESpeedDistributionView,
    QoESummaryView,
    QoETrendsView,
    QoEVsQoSCompareView,
    SpeedTestFileView,
    SpeedTestUploadView,
)

app_name = "qoe"

urlpatterns = [
    # -- Reports ---------------------------------------------------------------
    path("reports/", QoEReportCreateView.as_view(), name="report-create"),
    path("reports/list/", QoEReportListView.as_view(), name="report-list"),
    path("reports/<uuid:pk>/", QoEReportDetailView.as_view(), name="report-detail"),

    # -- Speed test ------------------------------------------------------------
    path("speedtest-file/", SpeedTestFileView.as_view(), name="speedtest-file"),
    path("speedtest-upload/", SpeedTestUploadView.as_view(), name="speedtest-upload"),
    path("ping/", PingView.as_view(), name="ping"),

    # -- Public aggregation ----------------------------------------------------
    path("heatmap/", QoEHeatmapView.as_view(), name="heatmap"),
    path("summary/", QoESummaryView.as_view(), name="summary"),
    path("trends/", QoETrendsView.as_view(), name="trends"),
    path("speeds/", QoESpeedDistributionView.as_view(), name="speeds"),
    path("districts/", QoEDistrictsView.as_view(), name="districts"),

    # -- Staff analytics -------------------------------------------------------
    path("analytics/", QoEAnalyticsView.as_view(), name="analytics"),
    path("compare/", QoEVsQoSCompareView.as_view(), name="compare"),
]

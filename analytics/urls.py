"""
URL configuration for the analytics app.

All routes are mounted under /api/v1/analytics/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    ComplaintsSummaryView,
    LicensingSummaryView,
    OperatorListView,
    PublicDashboardView,
    QoSByOperatorView,
    QoSListView,
    StaffDashboardView,
    TelecomsOverviewView,
)

app_name = "analytics"

urlpatterns = [
    # ── Dashboard ─────────────────────────────────────────────────────────────
    path("dashboard/public/",  PublicDashboardView.as_view(),  name="dashboard-public"),
    path("dashboard/staff/",   StaffDashboardView.as_view(),   name="dashboard-staff"),

    # ── Telecoms (Public) ─────────────────────────────────────────────────────
    path("telecoms/overview/",  TelecomsOverviewView.as_view(),  name="telecoms-overview"),
    path("telecoms/operators/", OperatorListView.as_view(),      name="telecoms-operators"),

    # ── QoS ───────────────────────────────────────────────────────────────────
    path("qos/",              QoSListView.as_view(),       name="qos-list"),
    path("qos/by-operator/",  QoSByOperatorView.as_view(), name="qos-by-operator"),

    # ── Cross-module summaries (Staff) ────────────────────────────────────────
    path("complaints/summary/",  ComplaintsSummaryView.as_view(),  name="complaints-summary"),
    path("licensing/summary/",   LicensingSummaryView.as_view(),   name="licensing-summary"),
]

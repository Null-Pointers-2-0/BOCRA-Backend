"""
URL configuration for the analytics app.

All routes are mounted under /api/v1/analytics/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    ApplicationsTrendView,
    ComplaintsSummaryView,
    ComplaintsTrendView,
    ContentOverviewView,
    LicensingSummaryView,
    NewsSummaryView,
    OperatorListView,
    PublicDashboardView,
    PublicationsSummaryView,
    QoSByOperatorView,
    QoSListView,
    StaffDashboardView,
    TelecomsOverviewView,
    TendersSummaryView,
    UsersSummaryView,
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
    path("users/summary/",          UsersSummaryView.as_view(),         name="users-summary"),
    path("complaints/summary/",     ComplaintsSummaryView.as_view(),    name="complaints-summary"),
    path("complaints/trend/",       ComplaintsTrendView.as_view(),      name="complaints-trend"),
    path("licensing/summary/",      LicensingSummaryView.as_view(),     name="licensing-summary"),
    path("applications/trend/",     ApplicationsTrendView.as_view(),    name="applications-trend"),
    path("publications/summary/",   PublicationsSummaryView.as_view(),  name="publications-summary"),
    path("tenders/summary/",        TendersSummaryView.as_view(),       name="tenders-summary"),
    path("news/summary/",           NewsSummaryView.as_view(),          name="news-summary"),
    path("content/overview/",       ContentOverviewView.as_view(),      name="content-overview"),
]

"""
URL configuration for the cybersecurity app.

All routes are mounted under /api/v1/cybersecurity/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    AssignAuditRequestView,
    AuditRequestCountView,
    MyAuditRequestDetailView,
    MyAuditRequestsView,
    RequestAuditView,
    StaffAuditRequestDetailView,
    StaffAuditRequestListView,
    UpdateAuditStatusView,
)

app_name = "cybersecurity"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path("request-audit/", RequestAuditView.as_view(), name="request-audit"),

    # ── Authenticated user ────────────────────────────────────────────────────
    path("my-requests/",        MyAuditRequestsView.as_view(),       name="my-requests"),
    path("my-requests/<uuid:pk>/", MyAuditRequestDetailView.as_view(), name="my-request-detail"),

    # ── Staff ─────────────────────────────────────────────────────────────────
    path("staff/",                StaffAuditRequestListView.as_view(),   name="staff-list"),
    path("staff/counts/",         AuditRequestCountView.as_view(),       name="staff-counts"),
    path("staff/<uuid:pk>/",      StaffAuditRequestDetailView.as_view(), name="staff-detail"),
    path("staff/<uuid:pk>/status/", UpdateAuditStatusView.as_view(),     name="update-status"),
    path("staff/<uuid:pk>/assign/", AssignAuditRequestView.as_view(),    name="assign"),
]

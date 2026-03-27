"""
BOCRA Backend — root URL configuration.

All application routes are versioned under /api/v1/.

API Documentation (auto-generated from code via drf-spectacular):
  /api/schema/    — raw OpenAPI 3.0 JSON/YAML schema
  /api/swagger/   — Swagger UI (interactive browser)
  /api/redoc/     — ReDoc UI (clean read-only reference)

The docs/ folder contains the design spec and conventions (human-written).
The Swagger/ReDoc UI is the live implementation reference (auto-generated).
Both are intentional — they serve different audiences.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # ── Django admin ──────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── API v1 ────────────────────────────────────────────────────────────────
    path("api/v1/", include("core.urls")),
    path("api/v1/accounts/", include("accounts.urls", namespace="accounts")),
    path("api/v1/licensing/", include("licensing.urls", namespace="licensing")),
    path("api/v1/complaints/", include("complaints.urls", namespace="complaints")),
    path("api/v1/publications/", include("publications.urls", namespace="publications")),
    path("api/v1/tenders/", include("tenders.urls", namespace="tenders")),
    path("api/v1/news/", include("news.urls", namespace="news")),
    path("api/v1/analytics/", include("analytics.urls", namespace="analytics")),
    path("api/v1/notifications/", include("notifications.urls", namespace="notifications")),
    path("api/v1/domains/", include("domains.urls", namespace="domains")),
    path("api/v1/coverages/", include("coverages.urls", namespace="coverages")),
    path("api/v1/qoe/", include("qoe.urls", namespace="qoe")),
    path("api/v1/scorecard/", include("scorecard.urls", namespace="scorecard")),
    path("api/v1/alerts/", include("alerts.urls", namespace="alerts")),
    path("api/v1/cybersecurity/", include("cybersecurity.urls", namespace="cybersecurity")),

    # ── API docs (drf-spectacular) ───────────────────────────────────────────
    # Raw OpenAPI 3.0 schema (JSON/YAML) — used by code generators and CI tools
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI — interactive browser for testing endpoints
    path("api/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # ReDoc — clean, readable API reference for frontend devs
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]



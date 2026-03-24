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
from django.http import JsonResponse
from apps.core.views import api_documentation

def api_root(request):
    """API root endpoint with available endpoints."""
    return JsonResponse({
        'message': 'BOCRA Digital Platform API',
        'version': '1.0.0',
        'endpoints': {
            'admin': '/admin/',
            'api_docs': '/api/docs/',
            'api_redoc': '/api/redoc/',
            'auth': '/api/v1/auth/',
            'schema': '/api/schema/'
        },
        'authentication': {
            'register': '/api/v1/auth/register/',
            'login': '/api/v1/auth/login/',
            'profile': '/api/v1/auth/profile/',
            'logout': '/api/v1/auth/logout/',
            'refresh': '/api/v1/auth/refresh/'
        }
    })

urlpatterns = [
    # API Root
    path('', api_root, name='api_root'),
    
    # Django admin
    path("admin/", admin.site.urls),

    # API v1 - Core and Authentication
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    
    # API v1 - All Modules
    path("api/v1/licensing/", include("licensing.urls", namespace="licensing")),
    path("api/v1/complaints/", include("complaints.urls", namespace="complaints")),
    path("api/v1/publications/", include("publications.urls", namespace="publications")),
    path("api/v1/tenders/", include("tenders.urls", namespace="tenders")),
    path("api/v1/news/", include("news.urls", namespace="news")),
    path("api/v1/analytics/", include("analytics.urls", namespace="analytics")),
    path("api/v1/notifications/", include("notifications.urls", namespace="notifications")),

    # API Documentation
    path('api/docs/', api_documentation, name='api_docs'),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

"""
Core views — API root and health check.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from core.utils import api_success


@extend_schema(tags=["Core"], summary="API root — lists all modules and documentation links")
@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    """
    GET /api/v1/

    Returns the API index — lists all available module endpoints.
    Useful for service discovery and as a health check.
    """
    return Response(
        api_success(
            {
                "version": "v1",
                "documentation": {
                    "swagger": request.build_absolute_uri("/api/swagger/"),
                    "redoc": request.build_absolute_uri("/api/redoc/"),
                    "schema": request.build_absolute_uri("/api/schema/"),
                },
                "modules": {
                    "accounts": request.build_absolute_uri("/api/v1/accounts/"),
                    "licensing": request.build_absolute_uri("/api/v1/licensing/"),
                    "complaints": request.build_absolute_uri("/api/v1/complaints/"),
                    "publications": request.build_absolute_uri("/api/v1/publications/"),
                    "tenders": request.build_absolute_uri("/api/v1/tenders/"),
                    "news": request.build_absolute_uri("/api/v1/news/"),
                    "analytics": request.build_absolute_uri("/api/v1/analytics/"),
                    "notifications": request.build_absolute_uri("/api/v1/notifications/"),
                },
                "platform": "BOCRA Digital Platform",
                "authority": "Botswana Communications Regulatory Authority",
            },
            "BOCRA Digital Platform API",
        )
    )


@extend_schema(tags=["Core"], summary="Health check — returns 200 if the service is running")
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /api/v1/health/

    Returns 200 if the service is running. Used by load balancers and uptime monitors.
    """
    return Response(api_success({"status": "ok"}, "Service is running."))


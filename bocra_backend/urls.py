"""
Main URL configuration for the BOCRA Digital Platform.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
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
    
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/auth/', include('apps.accounts.urls')),
    
    # API Documentation
path('api/docs/', api_documentation, name='api_docs'),
path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

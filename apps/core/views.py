"""
Simple API documentation view
"""
from django.http import JsonResponse
from rest_framework.decorators import api_view


@api_view(['GET'])
def api_documentation(request):
    """
    Simple API documentation endpoint
    """
    return JsonResponse({
        "title": "BOCRA Digital Platform API",
        "version": "1.0.0",
        "description": "Botswana Communications Regulatory Authority - Digital Services Platform",
        "base_url": "http://127.0.0.1:8000",
        "endpoints": {
            "authentication": {
                "register": {
                    "method": "POST",
                    "url": "/api/v1/auth/register/",
                    "description": "Register a new user account",
                    "fields": {
                        "email": "string (required)",
                        "username": "string (required)",
                        "password": "string (required)",
                        "password_confirm": "string (required)",
                        "first_name": "string (required)",
                        "last_name": "string (required)",
                        "role": "string (CITIZEN|STAFF|ADMIN)",
                        "phone_number": "string (+267 format)"
                    }
                },
                "login": {
                    "method": "POST",
                    "url": "/api/v1/auth/login/",
                    "description": "User login with JWT tokens",
                    "fields": {
                        "email": "string (required)",
                        "password": "string (required)"
                    },
                    "response": {
                        "access": "JWT access token",
                        "refresh": "JWT refresh token",
                        "user": "User object"
                    }
                },
                "profile": {
                    "method": "GET",
                    "url": "/api/v1/auth/profile/",
                    "description": "Get current user profile",
                    "headers": {
                        "Authorization": "Bearer JWT access token"
                    }
                },
                "profile_update": {
                    "method": "PATCH",
                    "url": "/api/v1/auth/profile/",
                    "description": "Update user profile",
                    "headers": {
                        "Authorization": "Bearer JWT access token"
                    },
                    "fields": {
                        "first_name": "string (optional)",
                        "last_name": "string (optional)",
                        "phone_number": "string (optional)",
                        "bio": "string (optional)"
                    }
                },
                "logout": {
                    "method": "POST",
                    "url": "/api/v1/auth/logout/",
                    "description": "User logout",
                    "fields": {
                        "refresh": "JWT refresh token"
                    }
                },
                "refresh": {
                    "method": "POST",
                    "url": "/api/v1/auth/refresh/",
                    "description": "Refresh JWT access token",
                    "fields": {
                        "refresh": "JWT refresh token"
                    }
                },
                "password_reset": {
                    "method": "POST",
                    "url": "/api/v1/auth/password-reset/",
                    "description": "Request password reset",
                    "fields": {
                        "email": "string (required)"
                    }
                }
            }
        },
        "authentication": {
            "type": "JWT Bearer Token",
            "header": "Authorization: Bearer <access_token>",
            "token_lifetime": {
                "access": "15 minutes",
                "refresh": "7 days"
            }
        },
        "status_codes": {
            "200": "Success",
            "201": "Created",
            "400": "Bad Request",
            "401": "Unauthorized",
            "403": "Forbidden",
            "404": "Not Found",
            "500": "Internal Server Error"
        }
    })

"""
Accounts URL configuration.

Base: /api/v1/accounts/
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    EmailVerificationView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RegisterView,
    ResendVerificationView,
    UserDetailView,
    UserListView,
)

app_name = "accounts"

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # ── Password ──────────────────────────────────────────────────────────────
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("change-password/", PasswordChangeView.as_view(), name="change-password"),
    # ── Profile ───────────────────────────────────────────────────────────────
    path("profile/", ProfileView.as_view(), name="profile"),
    # ── Admin: user management ────────────────────────────────────────────────
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
]

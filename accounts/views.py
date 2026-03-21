"""
Accounts API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
POST   /api/v1/accounts/register/                 RegisterView
GET    /api/v1/accounts/verify-email/?token=      EmailVerificationView
POST   /api/v1/accounts/resend-verification/      ResendVerificationView
POST   /api/v1/accounts/login/                    LoginView
POST   /api/v1/accounts/logout/                   LogoutView
POST   /api/v1/accounts/token/refresh/            TokenRefreshView (simplejwt)
GET    /api/v1/accounts/profile/                  ProfileView
PATCH  /api/v1/accounts/profile/                  ProfileView
POST   /api/v1/accounts/password-reset/           PasswordResetRequestView
POST   /api/v1/accounts/password-reset/confirm/   PasswordResetConfirmView
POST   /api/v1/accounts/change-password/          PasswordChangeView
GET    /api/v1/accounts/users/                    UserListView          [Admin]
GET    /api/v1/accounts/users/<uuid>/             UserDetailView        [Admin]
PATCH  /api/v1/accounts/users/<uuid>/             UserDetailView        [Admin]
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from core.utils import api_error, api_success
from .models import Profile, UserRole
from .permissions import IsAdmin, IsNotLocked, IsVerifiedUser
from .serializers import (
    AdminUserUpdateSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    ResendVerificationSerializer,
    TokenRefreshSerializer,
    UserListSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .tasks import (
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ─── REGISTRATION ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Auth"], summary="Register a new user account")
class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/accounts/register/

    Register a new user account.
    - Creates User + Profile in a single transaction.
    - Sends a verification email asynchronously via Celery.
    - Returns the user object (no token — require email verification first).

    Auth: Public
    """

    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Registration failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()

        # Generate a short-lived JWT for email verification (24 h)
        token = RefreshToken.for_user(user)
        token["purpose"] = "email_verification"
        token.set_exp(lifetime=timezone.timedelta(hours=24))
        verification_token = str(token.access_token)

        try:
            send_verification_email.delay(str(user.id), verification_token)
        except Exception:
            logger.warning("Celery unavailable — sending verification email synchronously.")
            send_verification_email(str(user.id), verification_token)

        return Response(
            api_success(
                UserSerializer(user).data,
                "Account created. Please check your email to verify your account.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── EMAIL VERIFICATION ───────────────────────────────────────────────────────

@extend_schema(tags=["Auth"], summary="Verify email address via token link")
class EmailVerificationView(APIView):
    """
    GET /api/v1/accounts/verify-email/?token=<jwt>

    Verify an email address using the token sent during registration.

    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer

    @extend_schema(
        parameters=[OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY)]
    )
    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response(
                api_error("Verification token is required.", status=400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            decoded = UntypedToken(token)
            user_id = decoded.get("user_id")
            purpose = decoded.get("purpose")
            if purpose != "email_verification":
                raise TokenError("Invalid token purpose.")
            user = User.objects.get(id=user_id)
        except (TokenError, User.DoesNotExist):
            return Response(
                api_error("Invalid or expired verification token."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.email_verified:
            return Response(
                api_success(message="Email is already verified."),
                status=status.HTTP_200_OK,
            )

        user.verify_email()
        try:
            send_welcome_email.delay(str(user.id))
        except Exception:
            pass

        return Response(
            api_success(message="Email verified successfully. You can now log in."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"], summary="Resend email verification link")
class ResendVerificationView(APIView):
    """
    POST /api/v1/accounts/resend-verification/

    Resend the email verification link.

    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = ResendVerificationSerializer

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = serializer.validated_data["email"]
        # Always respond with 200 to avoid leaking which emails are registered.
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            if not user.email_verified:
                token = RefreshToken.for_user(user)
                token["purpose"] = "email_verification"
                token.set_exp(lifetime=timezone.timedelta(hours=24))
                send_verification_email.delay(str(user.id), str(token.access_token))
        except User.DoesNotExist:
            pass

        return Response(
            api_success(
                message="If that email is registered and unverified, a new link has been sent."
            ),
            status=status.HTTP_200_OK,
        )


# ─── LOGIN ────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Auth"], summary="Authenticate and obtain JWT tokens")
class LoginView(APIView):
    """
    POST /api/v1/accounts/login/

    Authenticate with email or username + password.
    Returns an access token (15 min) and a refresh token (7 days).
    Set remember_me=true to extend refresh token lifetime to 30 days.

    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        identifier = serializer.validated_data["identifier"]
        password = serializer.validated_data["password"]
        remember_me = serializer.validated_data.get("remember_me", False)

        try:
            user = User.objects.get_by_natural_key(identifier)
        except User.DoesNotExist:
            return Response(
                api_error("Invalid credentials."),
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                api_error("This account has been deactivated. Please contact support."),
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.is_locked:
            return Response(
                api_error(
                    f"Account locked due to too many failed attempts. "
                    f"Try again after {user.locked_until.strftime('%Y-%m-%d %H:%M')} UTC."
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.check_password(password):
            user.increment_failed_login()
            remaining = max(0, user.MAX_FAILED_ATTEMPTS - user.failed_login_attempts)
            msg = (
                "Account locked due to too many failed attempts."
                if user.is_locked
                else f"Invalid credentials. {remaining} attempt(s) remaining before lockout."
            )
            return Response(api_error(msg), status=status.HTTP_401_UNAUTHORIZED)

        # Successful auth
        user.reset_failed_login()
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
        user.last_login_ip = ip.split(",")[0].strip() if ip else None
        user.last_login = timezone.now()
        user.save(update_fields=["last_login_ip", "last_login", "failed_login_attempts"])

        refresh = RefreshToken.for_user(user)
        if remember_me:
            refresh.set_exp(lifetime=timezone.timedelta(days=30))

        return Response(
            api_success(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                },
                "Login successful.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── LOGOUT ───────────────────────────────────────────────────────────────────

@extend_schema(tags=["Auth"], summary="Blacklist refresh token and log out")
class LogoutView(APIView):
    """
    POST /api/v1/accounts/logout/

    Blacklist the provided refresh token to invalidate the session.

    Auth: Authenticated
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TokenRefreshSerializer

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                api_error("Refresh token is required."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                api_error("Invalid or expired token."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            api_success(message="Logged out successfully."),
            status=status.HTTP_200_OK,
        )


# ─── PROFILE ──────────────────────────────────────────────────────────────────

@extend_schema(tags=["Profile"], summary="Retrieve or update current user profile")
class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/accounts/profile/  — Retrieve the authenticated user's profile.
    PATCH /api/v1/accounts/profile/  — Update profile fields (partial update).

    Auth: Authenticated + Not Locked
    """

    permission_classes = [IsAuthenticated, IsNotLocked]
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(
            api_success(serializer.data, "Profile retrieved."),
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            serializer.save()
        return Response(
            api_success(UserSerializer(request.user).data, "Profile updated."),
            status=status.HTTP_200_OK,
        )


# ─── PASSWORD RESET ───────────────────────────────────────────────────────────

@extend_schema(tags=["Auth"], summary="Request a password reset email")
class PasswordResetRequestView(APIView):
    """
    POST /api/v1/accounts/password-reset/

    Request a password reset email. Always returns 200 to avoid leaking
    which email addresses are registered.

    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            # Encode user PK and generate token
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_password_reset_email.delay(str(user.id), uid, token)
        except User.DoesNotExist:
            pass

        return Response(
            api_success(
                message="If that email is registered, a password reset link has been sent."
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"], summary="Confirm password reset with uid and token")
class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/accounts/password-reset/confirm/

    Confirm a password reset using the uid + token from the reset email.

    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                api_error("Invalid reset link."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = serializer.validated_data["token"]
        if not default_token_generator.check_token(user, token):
            return Response(
                api_error("Reset link has expired or is invalid."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response(
            api_success(message="Password reset successfully. You can now log in."),
            status=status.HTTP_200_OK,
        )


# ─── PASSWORD CHANGE ──────────────────────────────────────────────────────────

@extend_schema(tags=["Auth"], summary="Change password for authenticated user")
class PasswordChangeView(APIView):
    """
    POST /api/v1/accounts/change-password/

    Change password for the currently authenticated user.

    Auth: Authenticated + Not Locked
    """

    permission_classes = [IsAuthenticated, IsNotLocked]
    serializer_class = PasswordChangeSerializer

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(
            api_success(message="Password changed successfully."),
            status=status.HTTP_200_OK,
        )


# ─── USER MANAGEMENT (ADMIN) ─────────────────────────────────────────────────

@extend_schema(tags=["Admin — Users"], summary="List all users (admin only)")
class UserListView(generics.ListAPIView):
    """
    GET /api/v1/accounts/users/

    List all users. Supports filtering and search.
    - ?role=STAFF
    - ?is_active=true
    - ?search=<email or name>

    Auth: Admin
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserListSerializer
    filterset_fields = ["role", "is_active", "email_verified"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering_fields = ["date_joined", "email", "role"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        return User.objects.filter(is_deleted=False).select_related("profile").order_by(
            "-date_joined"
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return Response(
                api_success(paginated.data, "Users retrieved."),
                status=status.HTTP_200_OK,
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            api_success(serializer.data, "Users retrieved."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Admin — Users"], summary="Retrieve or update a user by ID (admin only)")
class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/accounts/users/<uuid>/   — Retrieve user detail.
    PATCH /api/v1/accounts/users/<uuid>/   — Update role, is_active, or email_verified.

    Auth: Admin
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return User.objects.filter(is_deleted=False).select_related("profile")

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return AdminUserUpdateSerializer
        return UserSerializer

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        return Response(
            api_success(UserSerializer(user).data, "User retrieved."),
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = AdminUserUpdateSerializer(
            user, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                api_error("Validation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            api_success(UserSerializer(user).data, "User updated."),
            status=status.HTTP_200_OK,
        )

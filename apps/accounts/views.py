"""
Views for user authentication and profile management.
"""
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.db import transaction
import jwt

from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    LoginSerializer,
    EmailVerificationSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
    UserUpdateSerializer,
    UserProfileSerializer,
    UserListSerializer,
)
from .permissions import (
    IsOwner,
    IsStaff,
    IsAdmin,
    IsSameUserOrAdmin,
    IsVerifiedUser,
    IsNotLocked,
)
from apps.core.utils import format_botswana_phone_number

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    
    POST /api/v1/auth/register/
    
    Creates a new user account with CITIZEN role and sends
    verification email. Implements comprehensive validation
    and security measures.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create a new user account.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Created user data with verification status
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            user = serializer.save()
            
            # Generate verification token
            token = jwt.encode(
                {
                    'user_id': str(user.id),
                    'email': user.email,
                    'exp': timezone.now() + timezone.timedelta(hours=24)
                },
                settings.SECRET_KEY,
                algorithm='HS256'
            )
            
            # Send verification email (async via Celery)
            try:
                from apps.accounts.tasks import send_verification_email
                send_verification_email.delay(user.id, token)
            except ImportError:
                # Fallback to synchronous email if Celery is not available
                self._send_verification_email_sync(user, token)
        
        return Response({
            'message': 'Registration successful. Please check your email to verify your account.',
            'user': UserSerializer(user).data,
            'verification_sent': True
        }, status=status.HTTP_201_CREATED)
    
    def _send_verification_email_sync(self, user, token):
        """
        Fallback method for sending verification email synchronously.
        
        Args:
            user: User instance
            token: Verification token
        """
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        subject = 'Verify Your BOCRA Account'
        message = f'''
        Hello {user.first_name},
        
        Please verify your email address by clicking the link below:
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you did not create this account, please ignore this email.
        
        Best regards,
        BOCRA Digital Platform Team
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class LoginView(TokenObtainPairView):
    """
    API endpoint for user login.
    
    POST /api/v1/auth/login/
    
    Authenticates user and returns JWT access and refresh tokens.
    Implements security measures like account locking and failed login tracking.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request, *args, **kwargs):
        """
        Authenticate user and return tokens.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: JWT tokens and user data
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        try:
            user = User.objects.get(email=email)
            
            # Check if account is locked
            if user.is_locked:
                return Response({
                    'error': 'Account is temporarily locked due to multiple failed login attempts.',
                    'locked_until': user.locked_until
                }, status=status.HTTP_423_LOCKED)
            
            # Check if account is active
            if not user.is_active:
                return Response({
                    'error': 'Account has been deactivated.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Authenticate user
            if not user.check_password(password):
                user.increment_failed_login()
                return Response({
                    'error': 'Invalid email or password.',
                    'failed_attempts': user.failed_login_attempts
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Reset failed login attempts on successful login
            user.reset_failed_login()
            
            # Update last login IP
            user.last_login_ip = self._get_client_ip(request)
            user.save(update_fields=['last_login_ip'])
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            # Set token lifetime based on remember_me
            if serializer.validated_data.get('remember_me', False):
                refresh.set_exp(lifetime=timezone.timedelta(days=30))
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
                'message': 'Login successful.'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Don't reveal if user exists for security
            return Response({
                'error': 'Invalid email or password.'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request.
        
        Args:
            request: HTTP request object
            
        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(APIView):
    """
    API endpoint for user logout.
    
    POST /api/v1/auth/logout/
    
    Blacklists the refresh token to prevent further use.
    Implements proper token invalidation for security.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Logout user by blacklisting refresh token.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Logout confirmation
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Successfully logged out.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Invalid token or logout failed.'
            }, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationView(APIView):
    """
    API endpoint for email verification.
    
    POST /api/v1/auth/verify-email/
    
    Verifies user's email address using the token sent during registration.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Verify user's email address.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Verification status
        """
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            
            if user.email_verified:
                return Response({
                    'message': 'Email already verified.'
                }, status=status.HTTP_200_OK)
            
            # Verify email
            user.verify_email()
            
            return Response({
                'message': 'Email verified successfully.',
                'email_verified': True
            }, status=status.HTTP_200_OK)
            
        except jwt.ExpiredSignatureError:
            return Response({
                'error': 'Verification token has expired. Please request a new verification email.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except jwt.InvalidTokenError:
            return Response({
                'error': 'Invalid verification token.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for user profile management.
    
    GET /api/v1/auth/profile/
    PUT /api/v1/auth/profile/
    
    Allows authenticated users to view and update their profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsNotLocked]
    
    def get_object(self):
        """Return the current user."""
        return self.request.user
    
    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer
    
    def update(self, request, *args, **kwargs):
        """
        Update user profile with proper validation.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Updated user data
        """
        # Set current user for audit trail
        request.user._current_user = request.user
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            user = serializer.save()
        
        return Response(UserSerializer(user).data)


class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for detailed user profile information.
    
    GET /api/v1/auth/profile/details/
    PUT /api/v1/auth/profile/details/
    
    Manages extended profile information like address, bio, etc.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsNotLocked]
    
    def get_object(self):
        """Return the current user's profile."""
        profile, created = User.profile.related.related_model.objects.get_or_create(
            user=self.request.user
        )
        return profile


class PasswordResetRequestView(APIView):
    """
    API endpoint to request password reset.
    
    POST /api/v1/auth/password-reset/
    
    Sends a password reset email to the user.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Send password reset email.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Password reset request status
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(str(user.pk).encode())
            
            # Send reset email (async via Celery)
            try:
                from apps.accounts.tasks import send_password_reset_email
                send_password_reset_email.delay(user.id, uid, token)
            except ImportError:
                # Fallback to synchronous email
                self._send_password_reset_email_sync(user, uid, token)
            
        except User.DoesNotExist:
            # Don't reveal that user doesn't exist for security
            pass
        
        return Response({
            'message': 'If the email exists, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)
    
    def _send_password_reset_email_sync(self, user, uid, token):
        """
        Fallback method for sending password reset email synchronously.
        
        Args:
            user: User instance
            uid: Base64 encoded user ID
            token: Password reset token
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        
        subject = 'Reset Your BOCRA Password'
        message = f'''
        Hello {user.first_name},
        
        You requested a password reset for your BOCRA account.
        
        Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 24 hours.
        
        If you did not request this password reset, please ignore this email.
        
        Best regards,
        BOCRA Digital Platform Team
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetConfirmView(APIView):
    """
    API endpoint to confirm password reset.
    
    POST /api/v1/auth/password-reset/confirm/
    
    Resets the user's password using the token from the reset email.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Reset user password.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Password reset status
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            uid = urlsafe_base64_decode(serializer.validated_data['uid']).decode()
            user = User.objects.get(pk=uid)
            
            if not default_token_generator.check_token(
                user, serializer.validated_data['token']
            ):
                return Response({
                    'error': 'Invalid or expired token.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({
                'message': 'Password reset successful. You can now login with your new password.'
            }, status=status.HTTP_200_OK)
            
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({
                'error': 'Invalid reset link.'
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """
    API endpoint for changing password when authenticated.
    
    POST /api/v1/auth/change-password/
    
    Allows authenticated users to change their password.
    """
    permission_classes = [IsAuthenticated, IsNotLocked]
    
    def post(self, request):
        """
        Change user password.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Password change status
        """
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully.'
        }, status=status.HTTP_200_OK)


class UserListView(generics.ListAPIView):
    """
    API endpoint for listing users.
    
    GET /api/v1/auth/users/
    
    Admin and staff users can view all users.
    """
    permission_classes = [IsAuthenticated, IsStaff]
    serializer_class = UserListSerializer
    filterset_fields = ['role', 'email_verified', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email', 'first_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        if self.request.user.is_admin:
            return User.objects.all()
        else:  # Staff
            return User.objects.filter(is_active=True)


class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for user details and management.
    
    GET /api/v1/auth/users/{id}/
    PUT /api/v1/auth/users/{id}/
    
    Admin users can manage any user, users can only manage themselves.
    """
    permission_classes = [IsAuthenticated, IsSameUserOrAdmin]
    queryset = User.objects.all()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def update(self, request, *args, **kwargs):
        """
        Update user with proper permissions.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Updated user data
        """
        # Only admins can change user roles
        if 'role' in request.data and not request.user.is_admin:
            request.data.pop('role')
        
        # Set current user for audit trail
        request.user._current_user = request.user
        
        return super().update(request, *args, **kwargs)


class ResendVerificationView(APIView):
    """
    API endpoint to resend verification email.
    
    POST /api/v1/auth/resend-verification/
    
    Sends new verification email to unverified users.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Resend verification email.
        
        Args:
            request: HTTP request object
            
        Returns:
            Response: Verification email status
        """
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email address is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            if user.email_verified:
                return Response({
                    'message': 'Email is already verified.'
                }, status=status.HTTP_200_OK)
            
            # Generate new verification token
            token = jwt.encode(
                {
                    'user_id': str(user.id),
                    'email': user.email,
                    'exp': timezone.now() + timezone.timedelta(hours=24)
                },
                settings.SECRET_KEY,
                algorithm='HS256'
            )
            
            # Send verification email
            try:
                from apps.accounts.tasks import send_verification_email
                send_verification_email.delay(user.id, token)
            except ImportError:
                self._send_verification_email_sync(user, token)
            
            return Response({
                'message': 'Verification email sent successfully.'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Don't reveal if user exists for security
            return Response({
                'message': 'If the email exists, a verification email has been sent.'
            }, status=status.HTTP_200_OK)

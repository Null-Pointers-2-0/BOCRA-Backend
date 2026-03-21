"""
Serializers for user authentication and profile management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re

from apps.core.utils import validate_botswana_phone_number, validate_botswana_id_number

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for reading user data.
    
    Excludes sensitive fields like password and provides
    additional computed fields for better API responses.
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.ReadOnlyField()
    is_locked = serializers.ReadOnlyField()
    profile_complete = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'phone_number', 'id_number',
            'email_verified', 'is_active', 'is_locked', 'created_at', 'last_login',
            'profile_complete'
        ]
        read_only_fields = [
            'id', 'email_verified', 'is_active', 'created_at', 'last_login'
        ]
    
    def get_profile_complete(self, obj):
        """Check if user profile is complete."""
        if hasattr(obj, 'profile'):
            return obj.profile.is_complete
        return False


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    """
    age = serializers.ReadOnlyField()
    is_complete = serializers.ReadOnlyField()
    
    class Meta:
        model = User.profile.related.related_model
        fields = [
            'date_of_birth', 'gender', 'address', 'city', 'postal_code',
            'profile_picture', 'bio', 'website', 'linkedin', 'age', 'is_complete'
        ]
    
    def validate_profile_picture(self, value):
        """Validate profile picture upload."""
        if value:
            # Check file size (max 5MB)
            max_size = 5 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError(
                    _('Profile picture size cannot exceed 5MB')
                )
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    _('Profile picture must be JPEG, PNG, or GIF')
                )
        
        return value


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    Handles password confirmation and validation with comprehensive
    error messages for better user experience.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password],
        help_text=_("Password must be at least 8 characters long")
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text=_("Must match the password field")
    )
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        default='CITIZEN',
        help_text=_("Select user role")
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number', 'id_number', 'role'
        ]
    
    def validate_email(self, value):
        """
        Ensure email is unique and properly formatted.
        
        Args:
            value (str): Email address to validate
            
        Returns:
            str: Normalized email address
            
        Raises:
            ValidationError: If email is invalid or already exists
        """
        # Normalize email to lowercase
        email = value.lower().strip()
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                _("A user with this email address already exists.")
            )
        
        return email
    
    def validate_username(self, value):
        """
        Ensure username is unique and properly formatted.
        
        Args:
            value (str): Username to validate
            
        Returns:
            str: Normalized username
            
        Raises:
            ValidationError: If username is invalid or already exists
        """
        username = value.strip().lower()
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError(
                _("A user with this username already exists.")
            )
        
        # Validate username format
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise serializers.ValidationError(
                _("Username can only contain letters, numbers, and underscores.")
            )
        
        return username
    
    def validate_phone_number(self, value):
        """
        Validate Botswana phone number format.
        
        Args:
            value (str): Phone number to validate
            
        Returns:
            str: Formatted phone number
            
        Raises:
            ValidationError: If phone number format is invalid
        """
        if value and not validate_botswana_phone_number(value):
            raise serializers.ValidationError(
                _("Invalid Botswana phone number format. Use +267XXXXXXXX or XXXXXXXX")
            )
        
        return value
    
    def validate_id_number(self, value):
        """
        Validate Botswana ID number format.
        
        Args:
            value (str): ID number to validate
            
        Returns:
            str: Validated ID number
            
        Raises:
            ValidationError: If ID number format is invalid
        """
        if value and not validate_botswana_id_number(value):
            raise serializers.ValidationError(
                _("Invalid Botswana ID number format. Use Omang (XXXXXX/XX/XX) or Passport format")
            )
        
        return value
    
    def validate(self, attrs):
        """
        Ensure passwords match and perform cross-field validation.
        
        Args:
            attrs (dict): Validated attributes
            
        Returns:
            dict: Validated attributes
            
        Raises:
            ValidationError: If validation fails
        """
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': _('Password fields do not match.')
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create user with hashed password and default CITIZEN role.
        
        Args:
            validated_data (dict): Validated user data
            
        Returns:
            User: Created user instance
        """
        # Remove password_confirm before creating user
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Create user with default CITIZEN role
        user = User.objects.create_user(
            role=User.Role.CITIZEN,
            **validated_data
        )
        user.set_password(password)
        user.save()
        
        # Create user profile
        from apps.accounts.models import UserProfile
        UserProfile.objects.create(user=user)
        
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    
    Accepts email and password, returns JWT tokens.
    Includes rate limiting information for security.
    """
    email = serializers.EmailField(
        required=True,
        help_text=_("User's registered email address")
    )
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        help_text=_("User's password")
    )
    remember_me = serializers.BooleanField(
        default=False,
        required=False,
        help_text=_("Keep me logged in for longer")
    )


class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for refreshing JWT tokens.
    """
    refresh = serializers.CharField(
        required=True,
        help_text=_("Valid refresh token")
    )


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification.
    """
    token = serializers.CharField(
        required=True,
        help_text=_("Verification token sent to email")
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset.
    """
    email = serializers.EmailField(
        required=True,
        help_text=_("Email address associated with the account")
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset.
    """
    token = serializers.CharField(
        required=True,
        help_text=_("Password reset token")
    )
    uid = serializers.CharField(
        required=True,
        help_text=_("User ID encoded in base64")
    )
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        help_text=_("New password")
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text=_("Confirm new password")
    )
    
    def validate(self, attrs):
        """
        Ensure new passwords match.
        
        Args:
            attrs (dict): Validated attributes
            
        Returns:
            dict: Validated attributes
            
        Raises:
            ValidationError: If passwords don't match
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _('Passwords do not match.')
            })
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing password when authenticated.
    """
    current_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        help_text=_("Current password")
    )
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        help_text=_("New password")
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text=_("Confirm new password")
    )
    
    def validate_current_password(self, value):
        """
        Validate current password.
        
        Args:
            value (str): Current password to validate
            
        Returns:
            str: Validated password
            
        Raises:
            ValidationError: If current password is incorrect
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                _("Current password is incorrect.")
            )
        return value
    
    def validate(self, attrs):
        """
        Ensure new passwords match.
        
        Args:
            attrs (dict): Validated attributes
            
        Returns:
            dict: Validated attributes
            
        Raises:
            ValidationError: If passwords don't match
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _('Passwords do not match.')
            })
        return attrs


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile information.
    
    Allows users to update their own profile information.
    """
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'id_number', 'profile'
        ]
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not validate_botswana_phone_number(value):
            raise serializers.ValidationError(
                _("Invalid Botswana phone number format")
            )
        return value
    
    def validate_id_number(self, value):
        """Validate ID number format."""
        if value and not validate_botswana_id_number(value):
            raise serializers.ValidationError(
                _("Invalid Botswana ID number format")
            )
        return value
    
    def update(self, instance, validated_data):
        """
        Update user and profile information.
        
        Args:
            instance (User): User instance to update
            validated_data (dict): Validated data
            
        Returns:
            User: Updated user instance
        """
        profile_data = validated_data.pop('profile', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile if provided
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for user lists.
    
    Used in API responses where only basic user information is needed.
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'email_verified', 'created_at'
        ]

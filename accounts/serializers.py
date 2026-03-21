from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from core.utils import (
    validate_botswana_id_number,
    validate_botswana_phone_number,
    format_botswana_phone_number,
)
from .models import Profile, UserRole

User = get_user_model()


# ─── PROFILE ──────────────────────────────────────────────────────────────────

class ProfileSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    is_complete = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = [
            "organisation",
            "position",
            "date_of_birth",
            "gender",
            "bio",
            "address",
            "city",
            "postal_code",
            "country",
            "id_number",
            "avatar",
            "age",
            "is_complete",
        ]

    def validate_avatar(self, value):
        if value:
            allowed = {"image/jpeg", "image/png", "image/gif"}
            if hasattr(value, "content_type") and value.content_type not in allowed:
                raise serializers.ValidationError(
                    "Only JPEG, PNG, and GIF avatars are supported."
                )
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Avatar must be under 5 MB.")
        return value


# ─── USER (read) ──────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    is_locked = serializers.ReadOnlyField()
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "id_number",
            "role",
            "role_display",
            "email_verified",
            "is_active",
            "is_locked",
            "date_joined",
            "last_login",
            "profile",
        ]
        read_only_fields = [
            "id", "email_verified", "is_active", "date_joined", "last_login",
        ]


# ─── USER (list — lighter payload) ───────────────────────────────────────────

class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "full_name", "role", "role_display",
            "email_verified", "is_active", "date_joined",
        ]


# ─── REGISTRATION ─────────────────────────────────────────────────────────────

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "phone_number",
            "id_number",
        ]

    def validate_email(self, value):
        normalised = value.strip().lower()
        if User.objects.filter(email__iexact=normalised).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalised

    def validate_username(self, value):
        if not value.isalnum():
            raise serializers.ValidationError(
                "Username may only contain letters and numbers."
            )
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_phone_number(self, value):
        if value and not validate_botswana_phone_number(value):
            raise serializers.ValidationError(
                "Enter a valid Botswana phone number (e.g. +26771234567 or 71234567)."
            )
        if value:
            return format_botswana_phone_number(value)
        return value

    def validate_id_number(self, value):
        if value and not validate_botswana_id_number(value):
            raise serializers.ValidationError(
                "Enter a valid Botswana ID (Omang) or passport number."
            )
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # New registrations always start as REGISTERED role
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone_number=validated_data.get("phone_number", ""),
            id_number=validated_data.get("id_number", ""),
            role=UserRole.REGISTERED,
        )
        Profile.objects.create(user=user, id_number=validated_data.get("id_number", ""))
        return user


# ─── PROFILE UPDATE ───────────────────────────────────────────────────────────

class UserUpdateSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "id_number",
            "profile",
        ]

    def validate_phone_number(self, value):
        if value and not validate_botswana_phone_number(value):
            raise serializers.ValidationError("Enter a valid Botswana phone number.")
        if value:
            return format_botswana_phone_number(value)
        return value

    def validate_id_number(self, value):
        if value and not validate_botswana_id_number(value):
            raise serializers.ValidationError(
                "Enter a valid Botswana ID (Omang) or passport number."
            )
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()
        return instance


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        help_text="Email address or username."
    )
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False, required=False)


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    uid = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Current password is incorrect."}
            )
        return attrs


# ─── ADMIN: USER ROLE / STATUS UPDATE ────────────────────────────────────────

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role", "is_active", "email_verified"]

    def validate_role(self, value):
        # Prevent escalating to SUPERADMIN unless requester is already SUPERADMIN
        request = self.context.get("request")
        if value == UserRole.SUPERADMIN and (
            not request or request.user.role != UserRole.SUPERADMIN
        ):
            raise serializers.ValidationError(
                "Only a Super Admin can assign the Super Admin role."
            )
        return value

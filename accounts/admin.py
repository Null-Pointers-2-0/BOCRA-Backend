from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone

from .models import Profile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email", "username", "full_name", "role", "is_active",
        "email_verified_badge", "is_locked_badge", "date_joined",
    )
    list_filter = ("role", "is_active", "email_verified", "is_deleted")
    search_fields = ("email", "username", "first_name", "last_name", "phone_number")
    ordering = ("-date_joined",)
    readonly_fields = (
        "id", "date_joined", "last_login", "last_login_ip",
        "failed_login_attempts", "locked_until",
    )

    fieldsets = (
        (None, {"fields": ("id", "email", "username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone_number", "id_number")}),
        ("Role & Status", {"fields": ("role", "is_active", "is_staff", "is_superuser", "email_verified", "groups", "user_permissions")}),
        ("Security", {"fields": ("last_login_ip", "failed_login_attempts", "locked_until")}),
        ("Soft Delete", {"fields": ("is_deleted",)}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )
    actions = [
        "bulk_verify_email",
        "unlock_accounts",
        "reset_failed_attempts",
        "bulk_deactivate",
        "bulk_activate",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile")

    @admin.display(description="Verified", boolean=False)
    def email_verified_badge(self, obj):
        if obj.email_verified:
            return format_html('<span style="color:green;">✓</span>')
        return format_html('<span style="color:red;">✗</span>')

    @admin.display(description="Locked", boolean=False)
    def is_locked_badge(self, obj):
        if obj.is_locked:
            return format_html('<span style="color:red;">Locked</span>')
        return format_html('<span style="color:green;">OK</span>')

    @admin.action(description="Verify email for selected users")
    def bulk_verify_email(self, request, queryset):
        queryset.update(email_verified=True)

    @admin.action(description="Unlock selected accounts")
    def unlock_accounts(self, request, queryset):
        queryset.update(locked_until=None, failed_login_attempts=0)

    @admin.action(description="Reset failed login attempts")
    def reset_failed_attempts(self, request, queryset):
        queryset.update(failed_login_attempts=0)

    @admin.action(description="Deactivate selected users")
    def bulk_deactivate(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Activate selected users")
    def bulk_activate(self, request, queryset):
        queryset.update(is_active=True)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organisation", "city", "country", "is_complete")
    search_fields = ("user__email", "user__username", "organisation", "city")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(boolean=True, description="Complete")
    def is_complete(self, obj):
        return obj.is_complete
    search_fields = ("user__email", "organisation")

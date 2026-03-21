"""
Admin configuration for the accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model.
    
    Provides enhanced admin interface with role-based filtering,
    email verification status, and bulk actions.
    """
    list_display = [
        'email', 'first_name', 'last_name', 'role', 'email_verified',
        'is_active', 'is_locked', 'created_at', 'last_login'
    ]
    list_filter = [
        'role', 'email_verified', 'is_active', 'created_at', 'last_login'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-created_at']
    
    # Custom fieldsets for better organization
    fieldsets = (
        (None, {
            'fields': ('email', 'username', 'password')
        }),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'phone_number', 'id_number')
        }),
        (_('Permissions'), {
            'fields': (
                'role', 'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        (_('Security'), {
            'fields': (
                'email_verified', 'last_login_ip', 'failed_login_attempts',
                'locked_until'
            )
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
    )
    
    # Add-only fieldsets for user creation
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'password1', 'password2',
                'first_name', 'last_name', 'role'
            ),
        }),
    )
    
    readonly_fields = [
        'created_at', 'updated_at', 'last_login', 'date_joined',
        'last_login_ip', 'failed_login_attempts'
    ]
    
    # Custom actions
    actions = [
        'send_verification_email',
        'unlock_accounts',
        'reset_failed_attempts',
        'bulk_verify_email',
        'bulk_deactivate',
        'bulk_activate'
    ]
    
    def get_queryset(self, request):
        """
        Optimize queryset with select_related for better performance.
        """
        return super().get_queryset(request).select_related('profile')
    
    def email_verified_badge(self, obj):
        """
        Display email verification status as a colored badge.
        """
        if obj.email_verified:
            return format_html(
                '<span style="color: green;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Not Verified</span>'
        )
    email_verified_badge.short_description = 'Email Status'
    
    def is_locked_badge(self, obj):
        """
        Display lock status as a colored badge.
        """
        if obj.is_locked:
            return format_html(
                '<span style="color: red;">🔒 Locked</span>'
            )
        return format_html(
            '<span style="color: green;">🔓 Unlocked</span>'
        )
    is_locked_badge.short_description = 'Lock Status'
    
    def send_verification_email(self, request, queryset):
        """
        Send verification emails to selected users.
        """
        count = 0
        for user in queryset.filter(email_verified=False):
            try:
                from .tasks import send_verification_email
                import jwt
                from django.conf import settings
                from django.utils import timezone
                
                token = jwt.encode(
                    {
                        'user_id': str(user.id),
                        'email': user.email,
                        'exp': timezone.now() + timezone.timedelta(hours=24)
                    },
                    settings.SECRET_KEY,
                    algorithm='HS256'
                )
                
                send_verification_email.delay(user.id, token)
                count += 1
            except Exception:
                pass
        
        self.message_user(
            request,
            f'Verification emails sent to {count} users.'
        )
    send_verification_email.short_description = 'Send verification email'
    
    def unlock_accounts(self, request, queryset):
        """
        Unlock selected user accounts.
        """
        count = queryset.update(
            locked_until=None,
            failed_login_attempts=0
        )
        self.message_user(
            request,
            f'{count} accounts unlocked successfully.'
        )
    unlock_accounts.short_description = 'Unlock selected accounts'
    
    def reset_failed_attempts(self, request, queryset):
        """
        Reset failed login attempts for selected users.
        """
        count = queryset.update(failed_login_attempts=0)
        self.message_user(
            request,
            f'Failed login attempts reset for {count} users.'
        )
    reset_failed_attempts.short_description = 'Reset failed attempts'
    
    def bulk_verify_email(self, request, queryset):
        """
        Bulk verify emails for selected users.
        """
        count = queryset.update(email_verified=True)
        self.message_user(
            request,
            f'{count} users marked as email verified.'
        )
    bulk_verify_email.short_description = 'Mark as email verified'
    
    def bulk_deactivate(self, request, queryset):
        """
        Bulk deactivate selected users.
        """
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{count} users deactivated.'
        )
    bulk_deactivate.short_description = 'Deactivate selected users'
    
    def bulk_activate(self, request, queryset):
        """
        Bulk activate selected users.
        """
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{count} users activated.'
        )
    bulk_activate.short_description = 'Activate selected users'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model.
    
    Provides interface for managing extended user profile information.
    """
    list_display = [
        'user', 'full_name', 'date_of_birth', 'gender', 'city', 'is_complete'
    ]
    list_filter = ['gender', 'city', 'date_of_birth']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'address', 'city'
    ]
    ordering = ['user__email']
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Personal Information'), {
            'fields': (
                'date_of_birth', 'gender', 'address', 'city',
                'postal_code'
            )
        }),
        (_('Profile'), {
            'fields': (
                'bio', 'website', 'linkedin'
            )
        }),
    )
    
    readonly_fields = ['is_complete']
    
    def get_queryset(self, request):
        """
        Optimize queryset with select_related for better performance.
        """
        return super().get_queryset(request).select_related('user')
    
    def full_name(self, obj):
        """Display user's full name."""
        return obj.user.full_name
    full_name.short_description = 'Full Name'
    
    def is_complete(self, obj):
        """
        Display profile completion status as a badge.
        """
        if obj.is_complete:
            return format_html(
                '<span style="color: green;">✓ Complete</span>'
            )
        return format_html(
            '<span style="color: orange;">⚠ Incomplete</span>'
        )
    is_complete.short_description = 'Profile Status'


# Customize admin site appearance
from django.contrib.admin import AdminSite
from django.contrib.admin.models import LogEntry

class BOCRAAdminSite(AdminSite):
    """
    Custom admin site for BOCRA Digital Platform.
    
    Provides branded admin interface with enhanced security
    and user experience features.
    """
    site_header = 'BOCRA Digital Platform Administration'
    site_title = 'BOCRA Admin'
    index_title = 'Welcome to BOCRA Digital Platform Admin'
    
    def get_urls(self):
        """
        Add custom URLs for admin functionality.
        """
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('user-stats/', self.admin_view(self.user_stats_view), name='user_stats'),
        ]
        return custom_urls + urls
    
    def user_stats_view(self, request):
        """
        Display user statistics dashboard.
        """
        from django.contrib.auth import get_user_model
        from django.db.models import Count
        from django.shortcuts import render
        
        User = get_user_model()
        
        stats = {
            'total_users': User.objects.filter(is_active=True).count(),
            'citizens': User.objects.filter(role='CITIZEN', is_active=True).count(),
            'staff': User.objects.filter(role='STAFF', is_active=True).count(),
            'admins': User.objects.filter(role='ADMIN', is_active=True).count(),
            'verified': User.objects.filter(email_verified=True, is_active=True).count(),
            'unverified': User.objects.filter(email_verified=False, is_active=True).count(),
            'locked': User.objects.filter(locked_until__isnull=False, is_active=True).count(),
        }
        
        # Calculate verification rate
        if stats['total_users'] > 0:
            stats['verification_rate'] = round(
                (stats['verified'] / stats['total_users']) * 100, 2
            )
        else:
            stats['verification_rate'] = 0
        
        # Recent users
        recent_users = User.objects.filter(
            is_active=True
        ).order_by('-created_at')[:10]
        
        context = {
            **self.each_context(request),
            'title': 'User Statistics',
            'stats': stats,
            'recent_users': recent_users,
        }
        
        return render(request, 'admin/user_stats.html', context)


# Create custom admin site instance
bocra_admin_site = BOCRAAdminSite(name='bocra_admin')

# Register models with custom admin site
bocra_admin_site.register(User, UserAdmin)
bocra_admin_site.register(UserProfile, UserProfileAdmin)
bocra_admin_site.register(LogEntry)


# Customize LogEntry display
@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """
    Admin interface for admin action logs.
    
    Provides visibility into admin activities for audit purposes.
    """
    list_display = [
        'action_time', 'user', 'content_type', 'object_repr',
        'action_flag', 'change_message'
    ]
    list_filter = [
        'action_flag', 'content_type', 'user', 'action_time'
    ]
    search_fields = [
        'user__username', 'user__email', 'object_repr', 'change_message'
    ]
    date_hierarchy = 'action_time'
    ordering = ['-action_time']
    
    readonly_fields = [
        'action_time', 'user', 'content_type', 'object_id',
        'object_repr', 'action_flag', 'change_message'
    ]
    
    def has_add_permission(self, request):
        """Prevent manual creation of log entries."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of log entries."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only allow deletion of log entries for admins."""
        return request.user.is_admin

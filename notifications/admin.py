from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "recipient", "notification_type", "is_read", "status", "created_at"]
    list_filter = ["notification_type", "is_read", "status"]
    search_fields = ["title", "message", "recipient__email"]
    readonly_fields = ["created_at"]

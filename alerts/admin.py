from django.contrib import admin

from .models import AlertCategory, AlertLog, AlertSubscription


@admin.register(AlertCategory)
class AlertCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_public", "is_active", "sort_order")
    list_filter = ("is_public", "is_active")
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")


@admin.register(AlertSubscription)
class AlertSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "is_confirmed", "is_active", "operator_filter", "created_at")
    list_filter = ("is_confirmed", "is_active", "operator_filter")
    search_fields = ("email",)
    readonly_fields = ("confirm_token", "unsubscribe_token", "confirmed_at")
    filter_horizontal = ("categories",)


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = ("subject", "category", "subscription", "status", "sent_at", "created_at")
    list_filter = ("status", "category")
    search_fields = ("subject", "subscription__email")
    readonly_fields = ("subscription", "category", "status", "sent_at", "error_message")

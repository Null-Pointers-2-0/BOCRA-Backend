from django.contrib import admin

from .models import Tender, TenderAddendum, TenderAward, TenderDocument


class TenderDocumentInline(admin.TabularInline):
    model = TenderDocument
    extra = 0


class TenderAddendumInline(admin.TabularInline):
    model = TenderAddendum
    extra = 0


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ["reference_number", "title", "category", "status", "closing_date"]
    list_filter = ["status", "category"]
    search_fields = ["title", "reference_number", "description"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TenderDocumentInline, TenderAddendumInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TenderAward)
class TenderAwardAdmin(admin.ModelAdmin):
    list_display = ["tender", "awardee_name", "award_date", "award_amount"]
    search_fields = ["awardee_name"]

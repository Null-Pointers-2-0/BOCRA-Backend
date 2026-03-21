from django.contrib import admin

from .models import Publication, PublicationAttachment


class PublicationAttachmentInline(admin.TabularInline):
    model = PublicationAttachment
    extra = 0


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "status", "published_date", "is_featured", "download_count"]
    list_filter = ["status", "category", "is_featured", "year"]
    search_fields = ["title", "summary"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PublicationAttachmentInline]
    readonly_fields = ["download_count", "created_at", "updated_at"]

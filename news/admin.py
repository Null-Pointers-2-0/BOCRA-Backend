from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "status", "author", "published_at", "is_featured", "view_count"]
    list_filter = ["status", "category", "is_featured"]
    search_fields = ["title", "excerpt"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["view_count", "created_at", "updated_at"]

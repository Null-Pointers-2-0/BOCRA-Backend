"""
News app models.

Entities
────────
Article   — A news article, press release, or announcement published by BOCRA.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.models import AuditableModel


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class NewsCategory(models.TextChoices):
    PRESS_RELEASE     = "PRESS_RELEASE",     "Press Release"
    ANNOUNCEMENT      = "ANNOUNCEMENT",      "Announcement"
    EVENT             = "EVENT",             "Event"
    REGULATORY_UPDATE = "REGULATORY_UPDATE", "Regulatory Update"
    OTHER             = "OTHER",             "Other"


class ArticleStatus(models.TextChoices):
    DRAFT     = "DRAFT",     "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED  = "ARCHIVED",  "Archived"


# ─── ARTICLE ──────────────────────────────────────────────────────────────────

def article_image_path(instance, filename):
    return f"news/images/{filename}"


class Article(AuditableModel):
    """A news article, press release, or announcement published by BOCRA."""

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True, blank=True)
    excerpt = models.TextField(
        blank=True,
        help_text="Short summary shown in listing views.",
    )
    content = models.TextField(
        help_text="Full article body (HTML or Markdown).",
    )
    category = models.CharField(
        max_length=30,
        choices=NewsCategory.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ArticleStatus.choices,
        default=ArticleStatus.DRAFT,
        db_index=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    featured_image = models.ImageField(
        upload_to=article_image_path,
        null=True,
        blank=True,
        help_text="Header image for the article.",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the article was published. Auto-set on first publish.",
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Pin to the homepage.",
    )
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:300]
            slug = base
            n = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

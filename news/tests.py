"""
Tests for the news app.

Test groups
───────────
ArticleModelTests                   — Model str, slug generation, soft delete
NewsCategoriesAPITests              — GET /categories/
PublicArticleListAPITests           — GET / (public list, search, filter)
PublicArticleDetailAPITests         — GET /<pk>/ (public detail, view count)
StaffArticleCreateAPITests          — POST /staff/
StaffArticleListAPITests            — GET /staff/list/
StaffArticleDetailAPITests          — GET /staff/<pk>/
StaffArticleUpdateAPITests          — PATCH /staff/<pk>/edit/
PublishArticleAPITests              — PATCH /staff/<pk>/publish/
ArchiveArticleAPITests              — PATCH /staff/<pk>/archive/
DeleteArticleAPITests               — DELETE /staff/<pk>/delete/
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserRole
from news.models import Article, ArticleStatus, NewsCategory

User = get_user_model()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def _staff_user(**kw):
    defaults = {
        "email": "staff@bocra.org.bw",
        "username": "news_staff",
        "password": "StaffPass123!",
        "first_name": "Staff",
        "last_name": "User",
        "role": UserRole.STAFF,
        "is_active": True,
        "email_verified": True,
    }
    defaults.update(kw)
    return User.objects.create_user(**defaults)


def _citizen_user(**kw):
    defaults = {
        "email": "citizen@test.bw",
        "username": "news_citizen",
        "password": "CitizenPass123!",
        "first_name": "Citizen",
        "last_name": "User",
        "role": UserRole.CITIZEN,
        "is_active": True,
        "email_verified": True,
    }
    defaults.update(kw)
    return User.objects.create_user(**defaults)


def _create_article(staff, **kw):
    defaults = {
        "title": "BOCRA Launches New Spectrum Policy",
        "excerpt": "BOCRA has unveiled a new spectrum management policy...",
        "content": "<p>Full article body about the new spectrum policy...</p>",
        "category": NewsCategory.ANNOUNCEMENT,
        "status": ArticleStatus.DRAFT,
        "author": staff,
        "created_by": staff,
    }
    defaults.update(kw)
    return Article.objects.create(**defaults)


# ─── MODEL TESTS ──────────────────────────────────────────────────────────────

class ArticleModelTests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_str(self):
        article = _create_article(self.staff)
        self.assertEqual(str(article), "BOCRA Launches New Spectrum Policy")

    def test_slug_auto_generated(self):
        article = _create_article(self.staff)
        self.assertTrue(article.slug)
        self.assertIn("bocra-launches", article.slug)

    def test_slug_unique_on_collision(self):
        a1 = _create_article(self.staff, title="Test Article")
        a2 = _create_article(self.staff, title="Test Article")
        self.assertNotEqual(a1.slug, a2.slug)

    def test_soft_delete(self):
        article = _create_article(self.staff)
        article.soft_delete()
        self.assertTrue(article.is_deleted)
        self.assertIsNotNone(article.deleted_at)


# ─── CATEGORIES ───────────────────────────────────────────────────────────────

class NewsCategoriesAPITests(APITestCase):
    def test_list_categories(self):
        url = reverse("news:categories")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["success"])
        values = [c["value"] for c in resp.data["data"]]
        self.assertIn("PRESS_RELEASE", values)
        self.assertIn("ANNOUNCEMENT", values)


# ─── PUBLIC LIST ──────────────────────────────────────────────────────────────

class PublicArticleListAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.url = reverse("news:list")
        # Published
        _create_article(self.staff, title="Published Article", status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        # Draft — should not appear
        _create_article(self.staff, title="Draft Article")

    def test_only_published_visible(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [a["title"] for a in resp.data["data"]]
        self.assertIn("Published Article", titles)
        self.assertNotIn("Draft Article", titles)

    def test_filter_by_category(self):
        _create_article(self.staff, title="Event News", category=NewsCategory.EVENT, status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        resp = self.client.get(self.url, {"category": "EVENT"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for a in resp.data["data"]:
            self.assertEqual(a["category"], "EVENT")

    def test_search(self):
        _create_article(self.staff, title="Unique Spectrum Policy", status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        resp = self.client.get(self.url, {"search": "Unique Spectrum"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)


# ─── PUBLIC DETAIL ────────────────────────────────────────────────────────────

class PublicArticleDetailAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_published_visible(self):
        article = _create_article(self.staff, status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        url = reverse("news:detail", args=[article.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["id"], str(article.pk))

    def test_draft_hidden(self):
        article = _create_article(self.staff)
        url = reverse("news:detail", args=[article.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_count_increments(self):
        article = _create_article(self.staff, status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        url = reverse("news:detail", args=[article.pk])
        self.assertEqual(article.view_count, 0)
        self.client.get(url)
        article.refresh_from_db()
        self.assertEqual(article.view_count, 1)


# ─── STAFF CREATE ─────────────────────────────────────────────────────────────

class StaffArticleCreateAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.url = reverse("news:staff-create")

    def test_create_article(self):
        _auth(self.client, self.staff)
        resp = self.client.post(self.url, {
            "title": "New Regulation Announced",
            "excerpt": "BOCRA announces a new regulation...",
            "content": "<p>Body of the article...</p>",
            "category": "REGULATORY_UPDATE",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["data"]["status"], "DRAFT")

    def test_citizen_denied(self):
        citizen = _citizen_user()
        _auth(self.client, citizen)
        resp = self.client.post(self.url, {
            "title": "Citizen Article",
            "content": "body",
            "category": "OTHER",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── STAFF LIST ───────────────────────────────────────────────────────────────

class StaffArticleListAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()
        self.url = reverse("news:staff-list")
        _create_article(self.staff, title="Draft One")
        _create_article(self.staff, title="Published One", status=ArticleStatus.PUBLISHED, published_at=timezone.now())

    def test_sees_all(self):
        _auth(self.client, self.staff)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 2)

    def test_citizen_denied(self):
        citizen = _citizen_user()
        _auth(self.client, citizen)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── STAFF DETAIL ─────────────────────────────────────────────────────────────

class StaffArticleDetailAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_staff_sees_draft(self):
        article = _create_article(self.staff)
        _auth(self.client, self.staff)
        url = reverse("news:staff-detail", args=[article.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["status"], "DRAFT")


# ─── STAFF UPDATE ─────────────────────────────────────────────────────────────

class StaffArticleUpdateAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_update_title(self):
        article = _create_article(self.staff)
        _auth(self.client, self.staff)
        url = reverse("news:staff-update", args=[article.pk])
        resp = self.client.patch(url, {"title": "Updated Title"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], "Updated Title")


# ─── PUBLISH ──────────────────────────────────────────────────────────────────

class PublishArticleAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_publish_success(self):
        article = _create_article(self.staff)
        _auth(self.client, self.staff)
        url = reverse("news:staff-publish", args=[article.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["status"], "PUBLISHED")

    def test_already_published(self):
        article = _create_article(self.staff, status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        _auth(self.client, self.staff)
        url = reverse("news:staff-publish", args=[article.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_archived_cannot_publish(self):
        article = _create_article(self.staff, status=ArticleStatus.ARCHIVED)
        _auth(self.client, self.staff)
        url = reverse("news:staff-publish", args=[article.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_citizen_denied(self):
        article = _create_article(self.staff)
        citizen = _citizen_user()
        _auth(self.client, citizen)
        url = reverse("news:staff-publish", args=[article.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── ARCHIVE ──────────────────────────────────────────────────────────────────

class ArchiveArticleAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_archive_success(self):
        article = _create_article(self.staff, status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        _auth(self.client, self.staff)
        url = reverse("news:staff-archive", args=[article.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["status"], "ARCHIVED")

    def test_already_archived(self):
        article = _create_article(self.staff, status=ArticleStatus.ARCHIVED)
        _auth(self.client, self.staff)
        url = reverse("news:staff-archive", args=[article.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── DELETE ───────────────────────────────────────────────────────────────────

class DeleteArticleAPITests(APITestCase):
    def setUp(self):
        self.staff = _staff_user()

    def test_soft_delete(self):
        article = _create_article(self.staff)
        _auth(self.client, self.staff)
        url = reverse("news:staff-delete", args=[article.pk])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        article.refresh_from_db()
        self.assertTrue(article.is_deleted)

    def test_deleted_not_in_public_list(self):
        article = _create_article(self.staff, status=ArticleStatus.PUBLISHED, published_at=timezone.now())
        _auth(self.client, self.staff)
        url = reverse("news:staff-delete", args=[article.pk])
        self.client.delete(url)
        resp = self.client.get(reverse("news:list"))
        titles = [a["title"] for a in resp.data["data"]]
        self.assertNotIn(article.title, titles)

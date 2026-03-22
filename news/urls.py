"""
News URL configuration.

Base: /api/v1/news/
"""

from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path("categories/", views.NewsCategoriesView.as_view(), name="categories"),
    path("<uuid:pk>/", views.PublicArticleDetailView.as_view(), name="detail"),
    path("", views.PublicArticleListView.as_view(), name="list"),

    # ── Staff ─────────────────────────────────────────────────────────────────
    path("staff/<uuid:pk>/publish/", views.PublishArticleView.as_view(), name="staff-publish"),
    path("staff/<uuid:pk>/archive/", views.ArchiveArticleView.as_view(), name="staff-archive"),
    path("staff/<uuid:pk>/delete/", views.DeleteArticleView.as_view(), name="staff-delete"),
    path("staff/<uuid:pk>/edit/", views.StaffArticleUpdateView.as_view(), name="staff-update"),
    path("staff/<uuid:pk>/", views.StaffArticleDetailView.as_view(), name="staff-detail"),
    path("staff/", views.StaffArticleCreateView.as_view(), name="staff-create"),
    path("staff/list/", views.StaffArticleListView.as_view(), name="staff-list"),
]

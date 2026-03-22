"""
publications URL configuration.

Base: /api/v1/publications/
"""

from django.urls import path

from . import views

app_name = "publications"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path("categories/", views.PublicationCategoriesView.as_view(), name="categories"),
    path("<uuid:pk>/download/", views.PublicationDownloadView.as_view(), name="download"),
    path("<uuid:pk>/", views.PublicPublicationDetailView.as_view(), name="detail"),
    path("", views.PublicPublicationListView.as_view(), name="list"),

    # ── Staff ─────────────────────────────────────────────────────────────────
    path("staff/<uuid:pk>/publish/", views.PublishPublicationView.as_view(), name="staff-publish"),
    path("staff/<uuid:pk>/archive/", views.ArchivePublicationView.as_view(), name="staff-archive"),
    path("staff/<uuid:pk>/delete/", views.DeletePublicationView.as_view(), name="staff-delete"),
    path("staff/<uuid:pk>/edit/", views.StaffPublicationUpdateView.as_view(), name="staff-update"),
    path("staff/<uuid:pk>/", views.StaffPublicationDetailView.as_view(), name="staff-detail"),
    path("staff/", views.StaffPublicationCreateView.as_view(), name="staff-create"),
    path("staff/list/", views.StaffPublicationListView.as_view(), name="staff-list"),
]

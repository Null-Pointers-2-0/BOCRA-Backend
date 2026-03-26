"""
tenders URL configuration.

Base: /api/v1/tenders/
"""

from django.urls import path

from . import views

app_name = "tenders"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path("categories/", views.TenderCategoriesView.as_view(), name="categories"),
    path("<uuid:pk>/documents/<uuid:doc_pk>/download/", views.TenderDocumentDownloadView.as_view(), name="doc-download"),
    path("<uuid:pk>/", views.PublicTenderDetailView.as_view(), name="detail"),
    path("", views.PublicTenderListView.as_view(), name="list"),

    # ── Applications (Authenticated) ─────────────────────────────────────────
    path("apply/", views.TenderApplicationCreateView.as_view(), name="apply"),
    path("my-applications/", views.MyTenderApplicationsView.as_view(), name="my-applications"),

    # ── Staff ─────────────────────────────────────────────────────────────────
    path("staff/<uuid:pk>/publish/", views.PublishTenderView.as_view(), name="staff-publish"),
    path("staff/<uuid:pk>/close/", views.CloseTenderView.as_view(), name="staff-close"),
    path("staff/<uuid:pk>/documents/", views.UploadTenderDocumentView.as_view(), name="staff-upload-doc"),
    path("staff/<uuid:pk>/addenda/", views.AddTenderAddendumView.as_view(), name="staff-addendum"),
    path("staff/<uuid:pk>/award/", views.AwardTenderView.as_view(), name="staff-award"),
    path("staff/<uuid:pk>/delete/", views.DeleteTenderView.as_view(), name="staff-delete"),
    path("staff/<uuid:pk>/edit/", views.StaffTenderUpdateView.as_view(), name="staff-update"),
    path("staff/<uuid:pk>/", views.StaffTenderDetailView.as_view(), name="staff-detail"),
    path("staff/", views.StaffTenderCreateView.as_view(), name="staff-create"),
    path("staff/list/", views.StaffTenderListView.as_view(), name="staff-list"),
]

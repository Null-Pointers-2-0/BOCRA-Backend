"""
URL configuration for the complaints app.

All routes are mounted under /api/v1/complaints/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    AddCaseNoteView,
    AssignComplaintView,
    ComplaintCategoriesView,
    ComplaintCountView,
    ComplaintDetailView,
    MyComplaintsView,
    ResolveComplaintView,
    StaffComplaintDetailView,
    StaffComplaintListView,
    SubmitComplaintView,
    TrackComplaintView,
    UpdateComplaintStatusView,
    UploadEvidenceView,
)

app_name = "complaints"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path("submit/",      SubmitComplaintView.as_view(),    name="submit"),
    path("track/",       TrackComplaintView.as_view(),     name="track"),
    path("categories/",  ComplaintCategoriesView.as_view(), name="categories"),

    # ── Complainant (authenticated) ───────────────────────────────────────────
    path("",                              MyComplaintsView.as_view(),        name="my-complaints"),
    path("<uuid:pk>/",                    ComplaintDetailView.as_view(),     name="detail"),
    path("<uuid:pk>/documents/",          UploadEvidenceView.as_view(),      name="upload-evidence"),

    # ── Staff ─────────────────────────────────────────────────────────────────
    path("<uuid:pk>/assign/",             AssignComplaintView.as_view(),     name="assign"),
    path("<uuid:pk>/status/",             UpdateComplaintStatusView.as_view(), name="update-status"),
    path("<uuid:pk>/notes/",              AddCaseNoteView.as_view(),         name="add-note"),
    path("<uuid:pk>/resolve/",            ResolveComplaintView.as_view(),    name="resolve"),
    path("staff/",                        StaffComplaintListView.as_view(),  name="staff-list"),
    path("staff/counts/",                 ComplaintCountView.as_view(),       name="staff-counts"),
    path("staff/<uuid:pk>/",              StaffComplaintDetailView.as_view(), name="staff-detail"),
]

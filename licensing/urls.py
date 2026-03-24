"""
URL configuration for the licensing app.

All routes are mounted under /api/v1/licensing/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    ApplicationDetailView,
    CancelApplicationView,
    LicenceCertificateView,
    LicenceDetailView,
    LicenceRenewView,
    LicenceSectorDetailView,
    LicenceSectorListView,
    LicenceTypeDetailView,
    LicenceTypeListView,
    LicenceVerifyView,
    MyApplicationsView,
    MyLicencesView,
    StaffApplicationDetailView,
    StaffApplicationListView,
    StaffLicenceTypeCreateView,
    StaffLicenceTypeDeleteView,
    StaffLicenceTypeDetailView,
    StaffLicenceTypeListView,
    StaffLicenceTypeUpdateView,
    StaffLicenceListView,
    StaffSectorCreateView,
    StaffSectorDeleteView,
    StaffSectorListView,
    StaffSectorUpdateView,
    UpdateApplicationStatusView,
    UploadDocumentView,
)

app_name = "licensing"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path("sectors/",           LicenceSectorListView.as_view(),   name="sector-list"),
    path("sectors/<uuid:pk>/", LicenceSectorDetailView.as_view(), name="sector-detail"),
    path("types/",             LicenceTypeListView.as_view(),     name="type-list"),
    path("types/<uuid:pk>/",   LicenceTypeDetailView.as_view(),   name="type-detail"),
    path("verify/",            LicenceVerifyView.as_view(),       name="verify"),

    # ── Applicant — Applications ───────────────────────────────────────────────
    path("applications/",                          MyApplicationsView.as_view(),         name="my-applications"),
    path("applications/<uuid:pk>/",                ApplicationDetailView.as_view(),      name="application-detail"),
    path("applications/<uuid:pk>/cancel/",         CancelApplicationView.as_view(),      name="application-cancel"),
    path("applications/<uuid:pk>/documents/",      UploadDocumentView.as_view(),         name="application-documents"),
    path("applications/<uuid:pk>/status/",         UpdateApplicationStatusView.as_view(), name="application-status"),

    # ── Applicant — Licences ──────────────────────────────────────────────────
    path("licences/",                        MyLicencesView.as_view(),         name="my-licences"),
    path("licences/<uuid:pk>/",              LicenceDetailView.as_view(),      name="licence-detail"),
    path("licences/<uuid:pk>/renew/",        LicenceRenewView.as_view(),       name="licence-renew"),
    path("licences/<uuid:pk>/certificate/",  LicenceCertificateView.as_view(), name="licence-certificate"),

    # ── Staff — Sectors ───────────────────────────────────────────────────────
    path("staff/sectors/",              StaffSectorListView.as_view(),   name="staff-sector-list"),
    path("staff/sectors/create/",       StaffSectorCreateView.as_view(), name="staff-sector-create"),
    path("staff/sectors/<uuid:pk>/",    StaffSectorUpdateView.as_view(), name="staff-sector-update"),
    path("staff/sectors/<uuid:pk>/delete/", StaffSectorDeleteView.as_view(), name="staff-sector-delete"),

    # ── Staff — Licence Types ─────────────────────────────────────────────────
    path("staff/types/",                StaffLicenceTypeListView.as_view(),   name="staff-type-list"),
    path("staff/types/create/",         StaffLicenceTypeCreateView.as_view(), name="staff-type-create"),
    path("staff/types/<uuid:pk>/",      StaffLicenceTypeDetailView.as_view(), name="staff-type-detail"),
    path("staff/types/<uuid:pk>/update/", StaffLicenceTypeUpdateView.as_view(), name="staff-type-update"),
    path("staff/types/<uuid:pk>/delete/", StaffLicenceTypeDeleteView.as_view(), name="staff-type-delete"),

    # ── Staff — Licences ──────────────────────────────────────────────────────
    path("staff/licences/",          StaffLicenceListView.as_view(),       name="staff-licences"),

    # ── Staff — Applications ──────────────────────────────────────────────────
    path("staff/applications/",           StaffApplicationListView.as_view(),   name="staff-applications"),
    path("staff/applications/<uuid:pk>/", StaffApplicationDetailView.as_view(), name="staff-application-detail"),
]

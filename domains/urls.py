"""
Domains app URL configuration.
"""
from django.urls import path

from . import views

app_name = "domains"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────
    path("zones/", views.DomainZoneListView.as_view(), name="zone-list"),
    path("check/", views.DomainAvailabilityView.as_view(), name="availability-check"),
    path("whois/", views.DomainWhoisView.as_view(), name="whois"),

    # ── Applicant — Applications ──────────────────────────────────────────
    path("apply/", views.DomainApplicationCreateView.as_view(), name="application-create"),
    path("my-applications/", views.MyApplicationsListView.as_view(), name="my-applications"),
    path("my-applications/<uuid:pk>/", views.MyApplicationDetailView.as_view(), name="my-application-detail"),
    path("my-applications/<uuid:pk>/update/", views.MyApplicationUpdateView.as_view(), name="my-application-update"),
    path("my-applications/<uuid:pk>/submit/", views.SubmitApplicationView.as_view(), name="my-application-submit"),
    path("my-applications/<uuid:pk>/cancel/", views.CancelApplicationView.as_view(), name="my-application-cancel"),
    path("my-applications/<uuid:pk>/respond/", views.RespondToInfoRequestView.as_view(), name="my-application-respond"),

    # ── Applicant — My Domains ────────────────────────────────────────────
    path("my-domains/", views.MyDomainsListView.as_view(), name="my-domains"),
    path("my-domains/<uuid:pk>/", views.MyDomainDetailView.as_view(), name="my-domain-detail"),

    # ── Staff — Application Queue ─────────────────────────────────────────
    path("staff/applications/", views.StaffApplicationListView.as_view(), name="staff-applications"),
    path("staff/applications/<uuid:pk>/", views.StaffApplicationDetailView.as_view(), name="staff-application-detail"),
    path("staff/applications/<uuid:pk>/review/", views.ReviewApplicationView.as_view(), name="staff-application-review"),
    path("staff/applications/<uuid:pk>/approve/", views.ApproveApplicationView.as_view(), name="staff-application-approve"),
    path("staff/applications/<uuid:pk>/reject/", views.RejectApplicationView.as_view(), name="staff-application-reject"),
    path("staff/applications/<uuid:pk>/request-info/", views.RequestInfoView.as_view(), name="staff-application-request-info"),

    # ── Staff — Domain Registry ───────────────────────────────────────────
    path("staff/list/", views.StaffDomainListView.as_view(), name="staff-domain-list"),
    path("staff/<uuid:pk>/", views.StaffDomainDetailView.as_view(), name="staff-domain-detail"),
    path("staff/<uuid:pk>/update/", views.StaffDomainUpdateView.as_view(), name="staff-domain-update"),
    path("staff/<uuid:pk>/suspend/", views.SuspendDomainView.as_view(), name="staff-domain-suspend"),
    path("staff/<uuid:pk>/unsuspend/", views.UnsuspendDomainView.as_view(), name="staff-domain-unsuspend"),
    path("staff/<uuid:pk>/reassign/", views.ReassignDomainView.as_view(), name="staff-domain-reassign"),
    path("staff/<uuid:pk>/delete/", views.DeleteDomainView.as_view(), name="staff-domain-delete"),

    # ── Staff — Zone Management ───────────────────────────────────────────
    path("staff/zones/", views.StaffZoneListView.as_view(), name="staff-zone-list"),
    path("staff/zones/create/", views.StaffZoneCreateView.as_view(), name="staff-zone-create"),
    path("staff/zones/<uuid:pk>/", views.StaffZoneUpdateView.as_view(), name="staff-zone-update"),

    # ── Staff — Statistics ────────────────────────────────────────────────
    path("staff/stats/", views.DomainStatsView.as_view(), name="staff-stats"),
]

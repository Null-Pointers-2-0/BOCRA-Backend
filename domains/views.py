"""
Domains API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Public
──────
GET    /domains/zones/                              DomainZoneListView
GET    /domains/check/                              DomainAvailabilityView
GET    /domains/whois/                              DomainWhoisView

Applicant
─────────
POST   /domains/apply/                              DomainApplicationCreateView
GET    /domains/my-applications/                    MyApplicationsListView
GET    /domains/my-applications/<pk>/               MyApplicationDetailView
PATCH  /domains/my-applications/<pk>/               MyApplicationUpdateView
POST   /domains/my-applications/<pk>/submit/        SubmitApplicationView
POST   /domains/my-applications/<pk>/cancel/        CancelApplicationView
POST   /domains/my-applications/<pk>/respond/       RespondToInfoRequestView
GET    /domains/my-domains/                         MyDomainsListView
GET    /domains/my-domains/<pk>/                    MyDomainDetailView

Staff
─────
GET    /domains/staff/applications/                 StaffApplicationListView
GET    /domains/staff/applications/<pk>/            StaffApplicationDetailView
PATCH  /domains/staff/applications/<pk>/review/     ReviewApplicationView
PATCH  /domains/staff/applications/<pk>/approve/    ApproveApplicationView
PATCH  /domains/staff/applications/<pk>/reject/     RejectApplicationView
PATCH  /domains/staff/applications/<pk>/request-info/ RequestInfoView
GET    /domains/staff/list/                         StaffDomainListView
GET    /domains/staff/<pk>/                         StaffDomainDetailView
PATCH  /domains/staff/<pk>/update/                  StaffDomainUpdateView
PATCH  /domains/staff/<pk>/suspend/                 SuspendDomainView
PATCH  /domains/staff/<pk>/unsuspend/               UnsuspendDomainView
PATCH  /domains/staff/<pk>/reassign/                ReassignDomainView
DELETE /domains/staff/<pk>/delete/                  DeleteDomainView
GET    /domains/staff/zones/                        StaffZoneListView
POST   /domains/staff/zones/                        StaffZoneCreateView
PATCH  /domains/staff/zones/<pk>/                   StaffZoneUpdateView
GET    /domains/staff/stats/                        DomainStatsView
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema

from accounts.permissions import IsStaff
from core.utils import api_error, api_success
from .models import (
    Domain,
    DomainApplication,
    DomainApplicationDocument,
    DomainApplicationStatus,
    DomainApplicationStatusLog,
    DomainApplicationType,
    DomainEvent,
    DomainEventType,
    DomainStatus,
    DomainZone,
)
from .serializers import (
    DomainApplicationCreateSerializer,
    DomainApplicationDetailSerializer,
    DomainApplicationListSerializer,
    DomainApplicationUpdateSerializer,
    DomainAvailabilitySerializer,
    DomainDetailSerializer,
    DomainListSerializer,
    DomainStatusUpdateSerializer,
    DomainWhoisSerializer,
    DomainZoneDetailSerializer,
    DomainZoneListSerializer,
    StaffApplicationDetailSerializer,
    StaffApplicationListSerializer,
    StaffDomainDetailSerializer,
    StaffDomainListSerializer,
    StaffDomainReassignSerializer,
    StaffDomainUpdateSerializer,
    StaffZoneCreateSerializer,
)
from .utils import generate_domain_reference

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@extend_schema(tags=["Domains — Public"], summary="List available .bw zones with fees")
class DomainZoneListView(generics.ListAPIView):
    """
    GET /api/v1/domains/zones/
    List all active domain zones. Public.
    """
    serializer_class = DomainZoneListSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "code", "description"]
    ordering = ["name"]

    def get_queryset(self):
        return DomainZone.objects.filter(is_active=True, is_deleted=False)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Domain zones retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Domains — Public"],
    summary="Check if a .bw domain is available",
    parameters=[
        OpenApiParameter("name", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description="FQDN to check (e.g. example.co.bw)"),
    ],
)
class DomainAvailabilityView(APIView):
    """
    GET /api/v1/domains/check/?name=example.co.bw
    Public domain availability check.
    """
    permission_classes = [AllowAny]
    serializer_class = DomainAvailabilitySerializer

    def get(self, request):
        name = request.query_params.get("name", "").strip().lower()
        if not name:
            return Response(
                api_error("Provide a domain name as ?name=example.co.bw"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse zone from domain name
        zone = None
        for z in DomainZone.objects.filter(is_active=True, is_deleted=False).order_by("-name"):
            if name.endswith(z.name):
                zone = z
                break

        if not zone:
            return Response(
                api_success(
                    {"domain_name": name, "available": False, "zone": None,
                     "message": "Invalid zone. No matching .bw zone found."},
                    "Invalid zone.",
                ),
                status=status.HTTP_200_OK,
            )

        zone_data = DomainZoneListSerializer(zone).data

        # Check if domain is already registered
        existing = Domain.objects.filter(
            domain_name=name, is_deleted=False
        ).first()

        if existing and existing.status in (DomainStatus.ACTIVE, DomainStatus.SUSPENDED):
            return Response(
                api_success(
                    {"domain_name": name, "available": False, "zone": zone_data,
                     "message": "This domain is already registered."},
                    "Domain is taken.",
                ),
                status=status.HTTP_200_OK,
            )

        if existing and existing.status == DomainStatus.EXPIRED:
            return Response(
                api_success(
                    {"domain_name": name, "available": False, "zone": zone_data,
                     "message": "This domain is expired but within the renewal grace period."},
                    "Domain is taken (pending renewal).",
                ),
                status=status.HTTP_200_OK,
            )

        # Check for pending applications
        pending = DomainApplication.objects.filter(
            domain_name=name,
            status__in=[
                DomainApplicationStatus.DRAFT,
                DomainApplicationStatus.SUBMITTED,
                DomainApplicationStatus.UNDER_REVIEW,
                DomainApplicationStatus.INFO_REQUESTED,
            ],
            is_deleted=False,
        ).exists()

        if pending:
            return Response(
                api_success(
                    {"domain_name": name, "available": False, "zone": zone_data,
                     "message": "Unavailable — there is a pending application for this domain."},
                    "Domain unavailable (pending application).",
                ),
                status=status.HTTP_200_OK,
            )

        # Available!
        message = f"Available! Registration fee: {zone.fee_currency} {zone.registration_fee}/yr"
        if zone.is_restricted:
            message += f" (Restricted: {zone.eligibility_criteria})"

        return Response(
            api_success(
                {"domain_name": name, "available": True, "zone": zone_data,
                 "message": message},
                "Domain is available.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Domains — Public"],
    summary="Public WHOIS-style lookup",
    parameters=[
        OpenApiParameter("name", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description="FQDN to look up (e.g. mascom.co.bw)"),
    ],
)
class DomainWhoisView(APIView):
    """
    GET /api/v1/domains/whois/?name=mascom.co.bw
    Public WHOIS-style lookup — returns limited registrant info.
    """
    permission_classes = [AllowAny]
    serializer_class = DomainWhoisSerializer

    def get(self, request):
        name = request.query_params.get("name", "").strip().lower()
        if not name:
            return Response(
                api_error("Provide a domain name as ?name=example.co.bw"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        domain = Domain.objects.filter(
            domain_name=name, is_deleted=False
        ).select_related("zone").first()

        if not domain:
            return Response(
                api_error("No domain found matching that name."),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DomainWhoisSerializer(domain)
        return Response(
            api_success(serializer.data, "WHOIS data retrieved."),
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  APPLICANT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@extend_schema(tags=["Domains — Applications"], summary="Submit a new domain application")
class DomainApplicationCreateView(APIView):
    """
    POST /api/v1/domains/apply/
    Auth: Authenticated user
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DomainApplicationCreateSerializer

    def post(self, request):
        serializer = DomainApplicationCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                api_error("Application submission failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        application = serializer.save()
        msg = (
            "Application submitted successfully."
            if application.status == DomainApplicationStatus.SUBMITTED
            else "Application saved as draft."
        )
        return Response(
            api_success(DomainApplicationListSerializer(application).data, msg),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Domains — Applications"], summary="List my domain applications")
class MyApplicationsListView(generics.ListAPIView):
    """
    GET /api/v1/domains/my-applications/
    Auth: Authenticated user
    """
    serializer_class = DomainApplicationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "application_type", "zone"]
    ordering_fields = ["created_at", "submitted_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            DomainApplication.objects.filter(
                applicant=self.request.user, is_deleted=False
            )
            .select_related("zone")
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Applications retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Applications"], summary="View application detail + status timeline")
class MyApplicationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/domains/my-applications/<pk>/
    Auth: Application owner
    """
    serializer_class = DomainApplicationDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            DomainApplication.objects.filter(
                applicant=self.request.user, is_deleted=False
            ).select_related("zone").prefetch_related("documents", "status_logs__changed_by"),
            pk=self.kwargs["pk"],
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Application retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Applications"], summary="Update a draft application")
class MyApplicationUpdateView(APIView):
    """
    PATCH /api/v1/domains/my-applications/<pk>/
    Only DRAFT applications can be updated.
    Auth: Application owner
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DomainApplicationUpdateSerializer

    def patch(self, request, pk):
        application = get_object_or_404(
            DomainApplication, pk=pk, applicant=request.user, is_deleted=False
        )
        if application.status != DomainApplicationStatus.DRAFT:
            return Response(
                api_error("Only draft applications can be updated."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DomainApplicationUpdateSerializer(
            application, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                api_error("Update failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            api_success(
                DomainApplicationDetailSerializer(application).data,
                "Application updated successfully.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Applications"], summary="Submit a draft application")
class SubmitApplicationView(APIView):
    """
    POST /api/v1/domains/my-applications/<pk>/submit/
    Auth: Application owner
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        application = get_object_or_404(
            DomainApplication, pk=pk, applicant=request.user, is_deleted=False
        )
        if not application.can_transition_to(DomainApplicationStatus.SUBMITTED):
            return Response(
                api_error(
                    f"Cannot submit application in '{application.get_status_display()}' status."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.transition_status(
            DomainApplicationStatus.SUBMITTED,
            changed_by=request.user,
            reason="Application submitted by applicant.",
        )
        return Response(
            api_success(message="Application submitted successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Applications"], summary="Cancel (withdraw) an application")
class CancelApplicationView(APIView):
    """
    POST /api/v1/domains/my-applications/<pk>/cancel/
    Auth: Application owner
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        application = get_object_or_404(
            DomainApplication, pk=pk, applicant=request.user, is_deleted=False
        )
        if not application.can_transition_to(DomainApplicationStatus.CANCELLED):
            return Response(
                api_error(
                    f"Cannot cancel application in '{application.get_status_display()}' status."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.transition_status(
            DomainApplicationStatus.CANCELLED,
            changed_by=request.user,
            reason=request.data.get("reason", "Cancelled by applicant."),
        )
        return Response(
            api_success(message="Application cancelled successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Applications"], summary="Respond to an info request from staff")
class RespondToInfoRequestView(APIView):
    """
    POST /api/v1/domains/my-applications/<pk>/respond/
    Applicant responds to staff info request. Moves status back to SUBMITTED.
    Auth: Application owner
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        application = get_object_or_404(
            DomainApplication, pk=pk, applicant=request.user, is_deleted=False
        )
        if application.status != DomainApplicationStatus.INFO_REQUESTED:
            return Response(
                api_error("This application is not awaiting additional information."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_message = request.data.get("message", "")
        if not response_message:
            return Response(
                api_error("A response message is required."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Move back to UNDER_REVIEW for re-review
        application.transition_status(
            DomainApplicationStatus.UNDER_REVIEW,
            changed_by=request.user,
            reason=f"Applicant response: {response_message}",
        )
        return Response(
            api_success(message="Response submitted. Your application will be reviewed again."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — My Domains"], summary="List my registered domains")
class MyDomainsListView(generics.ListAPIView):
    """
    GET /api/v1/domains/my-domains/
    Auth: Authenticated user
    """
    serializer_class = DomainListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "zone"]
    ordering_fields = ["domain_name", "registered_at", "expires_at"]
    ordering = ["domain_name"]

    def get_queryset(self):
        return Domain.objects.filter(
            registrant=self.request.user, is_deleted=False
        ).select_related("zone")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Domains retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — My Domains"], summary="View domain details")
class MyDomainDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/domains/my-domains/<pk>/
    Auth: Domain registrant
    """
    serializer_class = DomainDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            Domain.objects.filter(
                registrant=self.request.user, is_deleted=False
            ).select_related("zone"),
            pk=self.kwargs["pk"],
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Domain retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF ENDPOINTS — APPLICATIONS
# ═══════════════════════════════════════════════════════════════════════════════


@extend_schema(tags=["Domains — Staff"], summary="Application queue (all applications)")
class StaffApplicationListView(generics.ListAPIView):
    """
    GET /api/v1/domains/staff/applications/
    Auth: Staff
    """
    serializer_class = StaffApplicationListSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "application_type", "zone"]
    search_fields = ["reference_number", "domain_name", "organisation_name", "applicant__email"]
    ordering_fields = ["created_at", "submitted_at", "status", "domain_name"]
    ordering = ["-submitted_at"]

    def get_queryset(self):
        return (
            DomainApplication.objects.filter(is_deleted=False)
            .select_related("zone", "applicant")
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Applications retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Full application detail with documents")
class StaffApplicationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/domains/staff/applications/<pk>/
    Auth: Staff
    """
    serializer_class = StaffApplicationDetailSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return (
            DomainApplication.objects.filter(is_deleted=False)
            .select_related("zone", "applicant", "reviewed_by")
            .prefetch_related("documents", "status_logs__changed_by")
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Application retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Begin review (SUBMITTED → UNDER_REVIEW)")
class ReviewApplicationView(APIView):
    """
    PATCH /api/v1/domains/staff/applications/<pk>/review/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        application = get_object_or_404(
            DomainApplication.objects.select_related("zone", "applicant"),
            pk=pk, is_deleted=False,
        )
        if not application.can_transition_to(DomainApplicationStatus.UNDER_REVIEW):
            return Response(
                api_error(
                    f"Cannot move to Under Review from '{application.get_status_display()}'."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.transition_status(
            DomainApplicationStatus.UNDER_REVIEW,
            changed_by=request.user,
            reason="Application picked up for review.",
        )
        return Response(
            api_success(message="Application is now under review."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Approve application → auto-creates Domain")
class ApproveApplicationView(APIView):
    """
    PATCH /api/v1/domains/staff/applications/<pk>/approve/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        application = get_object_or_404(
            DomainApplication.objects.select_related("zone", "applicant"),
            pk=pk, is_deleted=False,
        )
        if not application.can_transition_to(DomainApplicationStatus.APPROVED):
            return Response(
                api_error(
                    f"Cannot approve from '{application.get_status_display()}'."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "Application approved.")

        with transaction.atomic():
            application.transition_status(
                DomainApplicationStatus.APPROVED,
                changed_by=request.user,
                reason=reason,
            )

            # Auto-create Domain record
            now = timezone.now()
            domain = Domain.objects.create(
                domain_name=application.domain_name,
                zone=application.zone,
                status=DomainStatus.ACTIVE,
                registrant=application.applicant,
                registrant_name=application.registrant_name,
                registrant_email=application.registrant_email,
                registrant_phone=application.registrant_phone,
                registrant_address=application.registrant_address,
                organisation_name=application.organisation_name,
                nameserver_1=application.nameserver_1,
                nameserver_2=application.nameserver_2,
                nameserver_3=application.nameserver_3,
                nameserver_4=application.nameserver_4,
                tech_contact_name=application.tech_contact_name,
                tech_contact_email=application.tech_contact_email,
                registered_at=now,
                expires_at=now + timedelta(days=365 * application.registration_period_years),
                created_from_application=application,
                created_by=request.user,
            )

            DomainEvent.objects.create(
                domain=domain,
                event_type=DomainEventType.REGISTERED,
                description=f"Domain {domain.domain_name} registered via application {application.reference_number}.",
                performed_by=request.user,
                metadata={
                    "application_ref": application.reference_number,
                    "period_years": application.registration_period_years,
                },
            )

        return Response(
            api_success(
                {"domain_id": str(domain.id), "domain_name": domain.domain_name},
                f"Application approved. Domain {domain.domain_name} registered.",
            ),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Reject application with reason")
class RejectApplicationView(APIView):
    """
    PATCH /api/v1/domains/staff/applications/<pk>/reject/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        application = get_object_or_404(
            DomainApplication, pk=pk, is_deleted=False
        )
        if not application.can_transition_to(DomainApplicationStatus.REJECTED):
            return Response(
                api_error(
                    f"Cannot reject from '{application.get_status_display()}'."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "")
        if not reason:
            return Response(
                api_error("A reason is required when rejecting an application."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.decision_reason = reason
        application.save(update_fields=["decision_reason", "updated_at"])
        application.transition_status(
            DomainApplicationStatus.REJECTED,
            changed_by=request.user,
            reason=reason,
        )
        return Response(
            api_success(message="Application rejected."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Request additional info from applicant")
class RequestInfoView(APIView):
    """
    PATCH /api/v1/domains/staff/applications/<pk>/request-info/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        application = get_object_or_404(
            DomainApplication, pk=pk, is_deleted=False
        )
        if not application.can_transition_to(DomainApplicationStatus.INFO_REQUESTED):
            return Response(
                api_error(
                    f"Cannot request info from '{application.get_status_display()}'."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = request.data.get("message", "")
        if not message:
            return Response(
                api_error("A message describing what info is needed is required."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.info_request_message = message
        application.save(update_fields=["info_request_message", "updated_at"])
        application.transition_status(
            DomainApplicationStatus.INFO_REQUESTED,
            changed_by=request.user,
            reason=message,
        )
        return Response(
            api_success(message="Information requested from applicant."),
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF ENDPOINTS — DOMAIN REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


@extend_schema(tags=["Domains — Staff"], summary="All domains in registry")
class StaffDomainListView(generics.ListAPIView):
    """
    GET /api/v1/domains/staff/list/
    Auth: Staff
    """
    serializer_class = StaffDomainListSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "zone", "is_seeded"]
    search_fields = ["domain_name", "organisation_name", "registrant_name", "registrant_email"]
    ordering_fields = ["domain_name", "registered_at", "expires_at", "status"]
    ordering = ["domain_name"]

    def get_queryset(self):
        return Domain.objects.filter(is_deleted=False).select_related("zone")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Domains retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Full domain detail with events")
class StaffDomainDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/domains/staff/<pk>/
    Auth: Staff
    """
    serializer_class = StaffDomainDetailSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return (
            Domain.objects.filter(is_deleted=False)
            .select_related("zone", "created_from_application")
            .prefetch_related("events__performed_by")
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Domain retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Update domain nameservers/contacts")
class StaffDomainUpdateView(APIView):
    """
    PATCH /api/v1/domains/staff/<pk>/update/
    Auth: Staff
    """
    permission_classes = [IsStaff]
    serializer_class = StaffDomainUpdateSerializer

    def patch(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk, is_deleted=False)

        serializer = StaffDomainUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Update failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        old_values = {}
        updated_fields = []

        # Track changes for audit
        for field_name in data:
            old_val = getattr(domain, field_name, "")
            new_val = data[field_name]
            if str(old_val) != str(new_val):
                old_values[field_name] = str(old_val)
                setattr(domain, field_name, new_val)
                updated_fields.append(field_name)

        if not updated_fields:
            return Response(
                api_success(message="No changes detected."),
                status=status.HTTP_200_OK,
            )

        updated_fields.append("updated_at")
        domain.modified_by = request.user
        updated_fields.append("modified_by")
        domain.save(update_fields=updated_fields)

        # Determine event type
        ns_fields = {"nameserver_1", "nameserver_2", "nameserver_3", "nameserver_4"}
        if ns_fields & set(updated_fields):
            event_type = DomainEventType.NS_UPDATED
        else:
            event_type = DomainEventType.CONTACT_UPDATED

        DomainEvent.objects.create(
            domain=domain,
            event_type=event_type,
            description=f"Domain updated: {', '.join(f for f in updated_fields if f not in ('updated_at', 'modified_by'))}",
            performed_by=request.user,
            metadata={"old_values": old_values, "new_values": {k: str(data[k]) for k in old_values}},
        )

        return Response(
            api_success(message="Domain updated successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Suspend a domain")
class SuspendDomainView(APIView):
    """
    PATCH /api/v1/domains/staff/<pk>/suspend/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk, is_deleted=False)

        if domain.status != DomainStatus.ACTIVE:
            return Response(
                api_error(f"Can only suspend ACTIVE domains. Current: {domain.get_status_display()}."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "")
        if not reason:
            return Response(
                api_error("A reason is required to suspend a domain."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        domain.status = DomainStatus.SUSPENDED
        domain.modified_by = request.user
        domain.save(update_fields=["status", "modified_by", "updated_at"])

        DomainEvent.objects.create(
            domain=domain,
            event_type=DomainEventType.SUSPENDED,
            description=f"Domain {domain.domain_name} suspended. Reason: {reason}",
            performed_by=request.user,
            metadata={"reason": reason},
        )

        return Response(
            api_success(message=f"Domain {domain.domain_name} suspended."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Reactivate a suspended domain")
class UnsuspendDomainView(APIView):
    """
    PATCH /api/v1/domains/staff/<pk>/unsuspend/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk, is_deleted=False)

        if domain.status != DomainStatus.SUSPENDED:
            return Response(
                api_error(f"Can only unsuspend SUSPENDED domains. Current: {domain.get_status_display()}."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        domain.status = DomainStatus.ACTIVE
        domain.modified_by = request.user
        domain.save(update_fields=["status", "modified_by", "updated_at"])

        DomainEvent.objects.create(
            domain=domain,
            event_type=DomainEventType.UNSUSPENDED,
            description=f"Domain {domain.domain_name} reactivated.",
            performed_by=request.user,
            metadata={},
        )

        return Response(
            api_success(message=f"Domain {domain.domain_name} reactivated."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Transfer domain ownership to another user")
class ReassignDomainView(APIView):
    """
    PATCH /api/v1/domains/staff/<pk>/reassign/
    Auth: Staff
    """
    permission_classes = [IsStaff]
    serializer_class = StaffDomainReassignSerializer

    def patch(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk, is_deleted=False)

        serializer = StaffDomainReassignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Reassignment failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        new_owner = User.objects.get(id=serializer.validated_data["new_owner_id"])
        old_owner_name = domain.registrant_name
        reason = serializer.validated_data["reason"]

        domain.registrant = new_owner
        domain.registrant_name = new_owner.get_full_name() or new_owner.email
        domain.registrant_email = new_owner.email
        domain.modified_by = request.user
        domain.save(update_fields=[
            "registrant", "registrant_name", "registrant_email",
            "modified_by", "updated_at",
        ])

        DomainEvent.objects.create(
            domain=domain,
            event_type=DomainEventType.TRANSFERRED,
            description=f"Domain {domain.domain_name} transferred from {old_owner_name} to {domain.registrant_name}.",
            performed_by=request.user,
            metadata={
                "old_registrant": old_owner_name,
                "new_registrant": domain.registrant_name,
                "reason": reason,
            },
        )

        return Response(
            api_success(message=f"Domain {domain.domain_name} reassigned to {domain.registrant_name}."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Soft-delete a domain")
class DeleteDomainView(APIView):
    """
    DELETE /api/v1/domains/staff/<pk>/delete/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def delete(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk, is_deleted=False)

        DomainEvent.objects.create(
            domain=domain,
            event_type=DomainEventType.DELETED,
            description=f"Domain {domain.domain_name} deleted.",
            performed_by=request.user,
            metadata={"previous_status": domain.status},
        )

        domain.status = DomainStatus.DELETED
        domain.save(update_fields=["status", "updated_at"])
        domain.soft_delete()

        return Response(
            api_success(message=f"Domain {domain.domain_name} deleted."),
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF ENDPOINTS — ZONE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@extend_schema(tags=["Domains — Staff"], summary="List all zones (staff)")
class StaffZoneListView(generics.ListAPIView):
    """
    GET /api/v1/domains/staff/zones/
    Auth: Staff
    """
    serializer_class = DomainZoneDetailSerializer
    permission_classes = [IsStaff]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "code"]
    ordering = ["name"]

    def get_queryset(self):
        return DomainZone.objects.filter(is_deleted=False)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Zones retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Domains — Staff"], summary="Create a new zone")
class StaffZoneCreateView(APIView):
    """
    POST /api/v1/domains/staff/zones/
    Auth: Staff
    """
    permission_classes = [IsStaff]
    serializer_class = StaffZoneCreateSerializer

    def post(self, request):
        serializer = StaffZoneCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("Zone creation failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        zone = serializer.save()
        return Response(
            api_success(DomainZoneDetailSerializer(zone).data, "Zone created successfully."),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Domains — Staff"], summary="Update zone fees/eligibility")
class StaffZoneUpdateView(APIView):
    """
    PATCH /api/v1/domains/staff/zones/<pk>/
    Auth: Staff
    """
    permission_classes = [IsStaff]
    serializer_class = StaffZoneCreateSerializer

    def patch(self, request, pk):
        zone = get_object_or_404(DomainZone, pk=pk, is_deleted=False)
        serializer = StaffZoneCreateSerializer(zone, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                api_error("Zone update failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            api_success(DomainZoneDetailSerializer(zone).data, "Zone updated successfully."),
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF ENDPOINTS — STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════


@extend_schema(tags=["Domains — Staff"], summary="Registry statistics")
class DomainStatsView(APIView):
    """
    GET /api/v1/domains/staff/stats/
    Auth: Staff
    """
    permission_classes = [IsStaff]

    def get(self, request):
        now = timezone.now()
        thirty_days = now + timedelta(days=30)

        total_domains = Domain.objects.filter(is_deleted=False).count()
        active_domains = Domain.objects.filter(is_deleted=False, status=DomainStatus.ACTIVE).count()
        expired_domains = Domain.objects.filter(is_deleted=False, status=DomainStatus.EXPIRED).count()
        suspended_domains = Domain.objects.filter(is_deleted=False, status=DomainStatus.SUSPENDED).count()
        expiring_soon = Domain.objects.filter(
            is_deleted=False, status=DomainStatus.ACTIVE,
            expires_at__lte=thirty_days, expires_at__gte=now,
        ).count()

        pending_applications = DomainApplication.objects.filter(
            is_deleted=False,
            status__in=[
                DomainApplicationStatus.SUBMITTED,
                DomainApplicationStatus.UNDER_REVIEW,
                DomainApplicationStatus.INFO_REQUESTED,
            ],
        ).count()

        # Domains by zone
        by_zone = (
            Domain.objects.filter(is_deleted=False)
            .values("zone__name", "zone__code")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Domains by status
        by_status = (
            Domain.objects.filter(is_deleted=False)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Applications by status
        apps_by_status = (
            DomainApplication.objects.filter(is_deleted=False)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        stats = {
            "total_domains": total_domains,
            "active_domains": active_domains,
            "expired_domains": expired_domains,
            "suspended_domains": suspended_domains,
            "expiring_soon": expiring_soon,
            "pending_applications": pending_applications,
            "domains_by_zone": list(by_zone),
            "domains_by_status": list(by_status),
            "applications_by_status": list(apps_by_status),
        }

        return Response(
            api_success(stats, "Domain statistics retrieved."),
            status=status.HTTP_200_OK,
        )

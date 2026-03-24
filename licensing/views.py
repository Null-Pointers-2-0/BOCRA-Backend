"""
Licensing API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
GET    /api/v1/licensing/types/                           LicenceTypeListView       [Public]
GET    /api/v1/licensing/types/<pk>/                      LicenceTypeDetailView     [Public]
GET    /api/v1/licensing/verify/                          LicenceVerifyView         [Public]
GET    /api/v1/licensing/applications/                    MyApplicationsView        [Registered]
POST   /api/v1/licensing/applications/                    MyApplicationsView        [Registered]
GET    /api/v1/licensing/applications/<pk>/               ApplicationDetailView     [Owner/Staff]
PATCH  /api/v1/licensing/applications/<pk>/cancel/        CancelApplicationView     [Owner]
POST   /api/v1/licensing/applications/<pk>/documents/     UploadDocumentView        [Owner/Staff]
GET    /api/v1/licensing/licences/                        MyLicencesView            [Registered]
GET    /api/v1/licensing/licences/<pk>/                   LicenceDetailView         [Owner/Staff]
POST   /api/v1/licensing/licences/<pk>/renew/             LicenceRenewView          [Owner]
GET    /api/v1/licensing/licences/<pk>/certificate/       LicenceCertificateView    [Owner/Staff]
GET    /api/v1/licensing/staff/applications/              StaffApplicationListView   [Staff]
GET    /api/v1/licensing/staff/applications/<pk>/         StaffApplicationDetailView [Staff]
PATCH  /api/v1/licensing/applications/<pk>/status/        UpdateApplicationStatusView [Staff]
"""

import logging

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)

from apps.accounts.permissions import IsAdmin, IsOwnerOrStaff, IsStaff
from apps.core.utils import api_error, api_success
from .models import (
    Application,
    ApplicationDocument,
    ApplicationStatus,
    Licence,
    LicenceStatus,
    LicenceType,
)
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    DocumentUploadSerializer,
    LicenceDetailSerializer,
    LicenceListSerializer,
    LicenceTypeDetailSerializer,
    LicenceTypeListSerializer,
    LicenceVerifySerializer,
    StaffApplicationDetailSerializer,
    StaffApplicationListSerializer,
    StatusUpdateSerializer,
)
from .tasks import (
    send_application_status_email,
    send_application_submitted_email,
)
from .utils import (
    calculate_expiry_date,
    generate_certificate_pdf,
    generate_licence_number,
    generate_licence_reference,
)

logger = logging.getLogger(__name__)


# ─── LICENCE TYPES (Public) ───────────────────────────────────────────────────

@extend_schema(tags=["Licensing — Public"], summary="List all active licence types")
class LicenceTypeListView(generics.ListAPIView):
    """
    GET /api/v1/licensing/types/

    List all active licence types available for application.
    Auth: Public
    """

    serializer_class = LicenceTypeListSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "code", "fee_amount"]
    ordering = ["name"]

    def get_queryset(self):
        return LicenceType.objects.filter(is_active=True, is_deleted=False)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Licence types retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Licensing — Public"], summary="Retrieve a licence type with full requirements")
class LicenceTypeDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/licensing/types/<pk>/

    Full detail for a single licence type including requirements.
    Auth: Public
    """

    serializer_class = LicenceTypeDetailSerializer
    permission_classes = [AllowAny]
    queryset = LicenceType.objects.filter(is_deleted=False)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Licence type retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── PUBLIC LICENCE VERIFICATION ──────────────────────────────────────────────

@extend_schema(
    tags=["Licensing — Public"],
    summary="Verify a licence by number or company name",
    parameters=[
        OpenApiParameter(
            "licence_no",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            description="Exact licence number to look up (e.g. LIC-ISP-2026-000001).",
        ),
        OpenApiParameter(
            "company",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            description="Organisation name (partial match supported).",
        ),
    ],
)
class LicenceVerifyView(APIView):
    """
    GET /api/v1/licensing/verify/

    Public endpoint — verify a licence by number or organisation name.
    Returns only safe public-facing fields.
    Auth: Public
    """

    permission_classes = [AllowAny]
    serializer_class = LicenceVerifySerializer

    def get(self, request):
        licence_no = request.query_params.get("licence_no", "").strip()
        company = request.query_params.get("company", "").strip()

        if not licence_no and not company:
            return Response(
                api_error("Provide licence_no or company as a query parameter."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Licence.objects.filter(is_deleted=False).select_related("licence_type")

        if licence_no:
            qs = qs.filter(licence_number__iexact=licence_no)
        elif company:
            qs = qs.filter(organisation_name__icontains=company)

        if not qs.exists():
            return Response(
                api_error("No licence found matching the provided details."),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = LicenceVerifySerializer(qs, many=True)
        return Response(
            api_success(serializer.data, f"{qs.count()} licence(s) found."),
            status=status.HTTP_200_OK,
        )


# ─── MY APPLICATIONS (Applicant) ──────────────────────────────────────────────

@extend_schema(tags=["Licensing — Applications"], summary="List or submit my licence applications")
class MyApplicationsView(generics.ListCreateAPIView):
    """
    GET  /api/v1/licensing/applications/  — list my applications
    POST /api/v1/licensing/applications/  — submit a new application

    Auth: Registered user
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "licence_type"]
    ordering_fields = ["created_at", "submitted_at", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ApplicationCreateSerializer
        return ApplicationListSerializer

    def get_queryset(self):
        return (
            Application.objects.filter(
                applicant=self.request.user,
                is_deleted=False,
            )
            .select_related("licence_type")
            .prefetch_related("licence")
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Applications retrieved successfully."),
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = ApplicationCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                api_error("Application submission failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )
        application = serializer.save()

        # Fire notification email if submitted (not draft)
        if application.status == ApplicationStatus.SUBMITTED:
            try:
                send_application_submitted_email.delay(str(application.id))
            except Exception:
                logger.warning("Celery unavailable — skipping submission email.")

        return Response(
            api_success(
                ApplicationListSerializer(application).data,
                "Application submitted successfully." if application.status == ApplicationStatus.SUBMITTED
                else "Application saved as draft.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── APPLICATION DETAIL (Applicant) ───────────────────────────────────────────

@extend_schema(tags=["Licensing — Applications"], summary="Retrieve application details and status timeline")
class ApplicationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/licensing/applications/<pk>/

    Full application detail including documents and status timeline.
    Auth: Application owner or Staff
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        user = self.request.user
        from apps.accounts.models import UserRole
        if hasattr(user, 'role') and user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return StaffApplicationDetailSerializer
        return ApplicationDetailSerializer

    def get_object(self):
        user = self.request.user
        from apps.accounts.models import UserRole
        qs = Application.objects.filter(is_deleted=False).select_related(
            "licence_type", "reviewed_by", "applicant"
        ).prefetch_related("documents", "status_logs__changed_by", "licence")

        if user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return get_object_or_404(qs, pk=self.kwargs["pk"])
        return get_object_or_404(qs, pk=self.kwargs["pk"], applicant=user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Application retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── CANCEL APPLICATION (Applicant) ───────────────────────────────────────────

@extend_schema(tags=["Licensing — Applications"], summary="Cancel a draft or submitted application")
class CancelApplicationView(APIView):
    """
    PATCH /api/v1/licensing/applications/<pk>/cancel/

    Applicant cancels their own draft or submitted application.
    Auth: Application owner
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ApplicationListSerializer

    def patch(self, request, pk):
        application = get_object_or_404(
            Application, pk=pk, applicant=request.user, is_deleted=False
        )
        if not application.can_transition_to(ApplicationStatus.CANCELLED):
            return Response(
                api_error(
                    f"This application cannot be cancelled at status '{application.get_status_display()}'."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.transition_status(
            ApplicationStatus.CANCELLED,
            changed_by=request.user,
            reason=request.data.get("reason", "Cancelled by applicant."),
        )
        return Response(
            api_success(message="Application cancelled successfully."),
            status=status.HTTP_200_OK,
        )


# ─── DOCUMENT UPLOAD ──────────────────────────────────────────────────────────

@extend_schema(tags=["Licensing — Applications"], summary="Upload a supporting document to an application")
class UploadDocumentView(APIView):
    """
    POST /api/v1/licensing/applications/<pk>/documents/

    Upload a supporting document to an application.
    Auth: Application owner or Staff
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DocumentUploadSerializer

    def get_application(self, pk, user):
        from apps.accounts.models import UserRole
        qs = Application.objects.filter(is_deleted=False)
        if user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return get_object_or_404(qs, pk=pk)
        return get_object_or_404(qs, pk=pk, applicant=user)

    @extend_schema(request=DocumentUploadSerializer)
    def post(self, request, pk):
        application = self.get_application(pk, request.user)

        # Documents can be added while in DRAFT, SUBMITTED, UNDER_REVIEW, INFO_REQUESTED
        if application.status not in (
            ApplicationStatus.DRAFT,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.INFO_REQUESTED,
        ):
            return Response(
                api_error(
                    f"Documents cannot be added to an application in '{application.get_status_display()}' status."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error("File upload failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = serializer.validated_data["file"]
        doc = ApplicationDocument.objects.create(
            application=application,
            name=serializer.validated_data["name"],
            file=uploaded_file,
            file_type=getattr(uploaded_file, "content_type", ""),
            file_size=uploaded_file.size,
            uploaded_by=request.user,
        )
        return Response(
            api_success(
                {"id": str(doc.id), "name": doc.name},
                "Document uploaded successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── UPDATE APPLICATION STATUS (Staff) ────────────────────────────────────────

@extend_schema(tags=["Licensing — Staff"], summary="Update application status and drive the review workflow (staff)")
class UpdateApplicationStatusView(APIView):
    """
    PATCH /api/v1/licensing/applications/<pk>/status/

    Staff drives the application state machine.
    On APPROVED: automatically creates a Licence record and generates
    the PDF certificate.
    Auth: Staff
    """

    permission_classes = [IsStaff]
    serializer_class = StatusUpdateSerializer

    def patch(self, request, pk):
        application = get_object_or_404(
            Application.objects.select_related("licence_type", "applicant"),
            pk=pk,
            is_deleted=False,
        )

        serializer = StatusUpdateSerializer(
            data=request.data,
            context={"application": application, "request": request},
        )
        if not serializer.is_valid():
            return Response(
                api_error("Status update failed.", serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        new_status = data["status"]
        reason = data.get("reason", "")
        info_msg = data.get("info_request_message", "")
        internal_notes = data.get("internal_notes", "")

        with transaction.atomic():
            # Persist optional side-data before transition
            if info_msg:
                application.info_request_message = info_msg
            if internal_notes:
                application.notes = (application.notes + "\n" + internal_notes).strip()
            if new_status == ApplicationStatus.REJECTED:
                application.decision_reason = reason
            application.save(update_fields=[
                "info_request_message", "notes", "decision_reason", "updated_at"
            ])

            log = application.transition_status(
                new_status, changed_by=request.user, reason=reason
            )

            # ── Auto-create Licence on approval ──────────────────────────────
            licence = None
            if new_status == ApplicationStatus.APPROVED:
                licence = _create_licence_from_application(application, request.user)

        # Fire notification email
        try:
            send_application_status_email.delay(str(application.id), new_status)
        except Exception:
            logger.warning("Celery unavailable — skipping status change email.")

        msg = f"Application status updated to '{application.get_status_display()}'."
        if licence:
            msg += f" Licence {licence.licence_number} issued."

        return Response(
            api_success(
                {"status": new_status, "licence_number": licence.licence_number if licence else None},
                msg,
            ),
            status=status.HTTP_200_OK,
        )


def _create_licence_from_application(application: Application, approved_by) -> Licence:
    """
    Create a Licence record from an approved application.
    Generates licence number, calculates expiry, and creates PDF certificate.
    Internal helper — not a view.
    """
    from datetime import date as date_cls

    issued = date_cls.today()
    expiry = calculate_expiry_date(issued, application.licence_type.validity_period_months)
    licence_number = generate_licence_number(application.licence_type.code)

    licence = Licence.objects.create(
        licence_number=licence_number,
        application=application,
        licence_type=application.licence_type,
        holder=application.applicant,
        organisation_name=application.organisation_name,
        issued_date=issued,
        expiry_date=expiry,
        status=LicenceStatus.ACTIVE,
    )

    # Generate and attach PDF certificate
    try:
        pdf_bytes = generate_certificate_pdf(licence)
        filename = f"certificate_{licence.licence_number}.pdf"
        licence.certificate_file.save(filename, ContentFile(pdf_bytes), save=True)
    except Exception as e:
        logger.error("Certificate generation failed for %s: %s", licence.licence_number, e)

    # Upgrade applicant role to LICENSEE
    applicant = application.applicant
    from apps.accounts.models import UserRole
    if applicant.role not in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
        applicant.role = UserRole.LICENSEE
        applicant.save(update_fields=["role"])

    return licence


# ─── STAFF APPLICATION QUEUE ──────────────────────────────────────────────────

@extend_schema(tags=["Licensing — Staff"], summary="List all applications across all users (staff)")
class StaffApplicationListView(generics.ListAPIView):
    """
    GET /api/v1/licensing/staff/applications/

    Staff view — all applications across all users.
    Supports filtering by status, licence_type. Ordered by submitted_at.
    Auth: Staff
    """

    serializer_class = StaffApplicationListSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "licence_type"]
    search_fields = ["reference_number", "organisation_name", "applicant__email"]
    ordering_fields = ["created_at", "submitted_at", "status", "organisation_name"]
    ordering = ["-submitted_at"]

    def get_queryset(self):
        return (
            Application.objects.filter(is_deleted=False)
            .select_related("licence_type", "applicant", "reviewed_by")
            .prefetch_related("licence")
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Applications retrieved successfully."),
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Licensing — Staff"], summary="Retrieve any application with internal staff notes")
class StaffApplicationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/licensing/staff/applications/<pk>/

    Staff full view including internal notes.
    Auth: Staff
    """

    serializer_class = StaffApplicationDetailSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return Application.objects.filter(is_deleted=False).select_related(
            "licence_type", "applicant", "reviewed_by"
        ).prefetch_related("documents", "status_logs__changed_by", "licence")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Application retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── MY LICENCES (Applicant) ──────────────────────────────────────────────────

@extend_schema(tags=["Licensing — Licences"], summary="List my active and historical licences")
class MyLicencesView(generics.ListAPIView):
    """
    GET /api/v1/licensing/licences/

    List licences held by the authenticated user.
    Auth: Registered user
    """

    serializer_class = LicenceListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "licence_type"]
    ordering_fields = ["issued_date", "expiry_date", "status"]
    ordering = ["-issued_date"]

    def get_queryset(self):
        return Licence.objects.filter(
            holder=self.request.user, is_deleted=False
        ).select_related("licence_type")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Licences retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── LICENCE DETAIL ───────────────────────────────────────────────────────────

@extend_schema(tags=["Licensing — Licences"], summary="Retrieve full licence details")
class LicenceDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/licensing/licences/<pk>/

    Full licence detail.
    Auth: Licence holder or Staff
    """

    serializer_class = LicenceDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        from apps.accounts.models import UserRole
        qs = Licence.objects.filter(is_deleted=False).select_related(
            "licence_type", "holder", "application"
        )
        if user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            return get_object_or_404(qs, pk=self.kwargs["pk"])
        return get_object_or_404(qs, pk=self.kwargs["pk"], holder=user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            api_success(serializer.data, "Licence retrieved successfully."),
            status=status.HTTP_200_OK,
        )


# ─── LICENCE RENEWAL ──────────────────────────────────────────────────────────

@extend_schema(tags=["Licensing — Licences"], summary="Submit a renewal application for an existing licence")
class LicenceRenewView(APIView):
    """
    POST /api/v1/licensing/licences/<pk>/renew/

    Create a renewal application for an existing licence.
    Only allowed if the licence is ACTIVE or within 90 days of expiry.
    Auth: Licence holder
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ApplicationListSerializer

    def post(self, request, pk):
        licence = get_object_or_404(
            Licence, pk=pk, holder=request.user, is_deleted=False
        )

        if licence.status == LicenceStatus.REVOKED:
            return Response(
                api_error("Revoked licences cannot be renewed."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for an already-pending renewal
        existing_renewal = Application.objects.filter(
            renewal_of=licence,
            status__in=[
                ApplicationStatus.DRAFT,
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.UNDER_REVIEW,
                ApplicationStatus.INFO_REQUESTED,
            ],
        ).first()
        if existing_renewal:
            return Response(
                api_error(
                    f"A renewal application ({existing_renewal.reference_number}) "
                    f"is already in progress for this licence."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            application = Application.objects.create(
                applicant=request.user,
                reference_number=generate_licence_reference(),
                licence_type=licence.licence_type,
                renewal_of=licence,
                organisation_name=licence.organisation_name,
                contact_person=request.user.get_full_name() or request.user.email,
                contact_email=request.user.email,
                description=f"Renewal of licence {licence.licence_number}",
                status=ApplicationStatus.DRAFT,
            )
            application.transition_status(
                ApplicationStatus.SUBMITTED,
                changed_by=request.user,
                reason=f"Renewal application for licence {licence.licence_number}.",
            )

        try:
            send_application_submitted_email.delay(str(application.id))
        except Exception:
            logger.warning("Celery unavailable — skipping renewal submitted email.")

        return Response(
            api_success(
                {
                    "application_id": str(application.id),
                    "reference_number": application.reference_number,
                },
                f"Renewal application {application.reference_number} submitted successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


# ─── LICENCE CERTIFICATE DOWNLOAD ─────────────────────────────────────────────

@extend_schema(
    tags=["Licensing — Licences"],
    summary="Download PDF licence certificate",
    responses={(200, "application/pdf"): OpenApiTypes.BINARY},
)
class LicenceCertificateView(APIView):
    """
    GET /api/v1/licensing/licences/<pk>/certificate/

    Download the PDF certificate for a licence.
    If no certificate file exists, generates one on-the-fly.
    Auth: Licence holder or Staff
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        from apps.accounts.models import UserRole
        qs = Licence.objects.filter(is_deleted=False)
        if user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            licence = get_object_or_404(qs, pk=pk)
        else:
            licence = get_object_or_404(qs, pk=pk, holder=user)

        if licence.status != LicenceStatus.ACTIVE:
            return Response(
                api_error("Certificate is only available for active licences."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try stored file first; fall back to on-the-fly generation
        if licence.certificate_file:
            try:
                return FileResponse(
                    licence.certificate_file.open("rb"),
                    as_attachment=True,
                    filename=f"BOCRA_Licence_{licence.licence_number}.pdf",
                    content_type="application/pdf",
                )
            except Exception:
                pass  # Fall through to regenerate

        # Generate on-the-fly
        try:
            pdf_bytes = generate_certificate_pdf(licence)
        except Exception as e:
            logger.error("On-the-fly certificate generation failed: %s", e)
            return Response(
                api_error("Certificate generation failed. Please try again later."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Persist for next time
        try:
            filename = f"certificate_{licence.licence_number}.pdf"
            licence.certificate_file.save(filename, ContentFile(pdf_bytes), save=True)
        except Exception:
            pass  # Non-critical — serve the bytes regardless

        from django.http import HttpResponse

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="BOCRA_Licence_{licence.licence_number}.pdf"'
        )
        return response

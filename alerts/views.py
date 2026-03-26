"""
Alerts API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints (9)
-------------
GET  /api/v1/alerts/categories/                     AlertCategoriesView          [Public]
POST /api/v1/alerts/subscribe/                       AlertSubscribeView           [Public]
GET  /api/v1/alerts/confirm/{token}/                 ConfirmSubscriptionView      [Public]
GET  /api/v1/alerts/unsubscribe/{token}/             UnsubscribeView              [Public]
GET  /api/v1/alerts/subscriptions/                   MySubscriptionsView          [Auth]
PATCH /api/v1/alerts/subscriptions/                  UpdateSubscriptionView       [Auth]
DELETE /api/v1/alerts/subscriptions/                 DeleteSubscriptionView       [Auth]
GET  /api/v1/alerts/logs/                            AlertLogsView                [Staff]
GET  /api/v1/alerts/stats/                           AlertStatsView               [Staff]
"""

import hashlib
import logging

from django.db.models import Count, Q
from django.utils import timezone

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)

from accounts.permissions import IsStaff
from core.utils import api_error, api_success

from .models import AlertCategory, AlertLog, AlertStatus, AlertSubscription
from .serializers import (
    AlertCategorySerializer,
    AlertLogSerializer,
    AlertSubscribeSerializer,
    AlertSubscriptionDetailSerializer,
    AlertSubscriptionUpdateSerializer,
)

logger = logging.getLogger(__name__)


# -- HELPERS -------------------------------------------------------------------

SUBSCRIBE_RATE_LIMIT = 3
SUBSCRIBE_RATE_WINDOW_HOURS = 1


def _hash_email(email):
    """SHA-256 hash for rate limiting by email."""
    return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()


# -- PAGINATION ----------------------------------------------------------------

class AlertLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


# -- PUBLIC VIEWS --------------------------------------------------------------

class AlertCategoriesView(APIView):
    """GET list all public, active alert categories."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Alerts"],
        summary="List alert categories",
        description="Returns all public and active alert categories.",
        responses={200: AlertCategorySerializer(many=True)},
    )
    def get(self, request):
        categories = AlertCategory.objects.filter(
            is_public=True,
            is_active=True,
            is_deleted=False,
        )
        serializer = AlertCategorySerializer(categories, many=True)
        return Response(api_success(
            message="Alert categories retrieved.",
            data=serializer.data,
        ))


class AlertSubscribeView(APIView):
    """POST subscribe an email to alert categories."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Alerts"],
        summary="Subscribe to alerts",
        description=(
            "Subscribe an email address to one or more alert categories. "
            "A confirmation email will be sent (double opt-in). "
            "Rate limited to 3 requests per email per hour."
        ),
        request=AlertSubscribeSerializer,
        responses={201: AlertSubscriptionDetailSerializer},
    )
    def post(self, request):
        serializer = AlertSubscribeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error(message="Validation failed.", errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"].lower().strip()
        category_codes = serializer.validated_data["categories"]
        operator_filter = serializer.validated_data.get("operator_filter", "")

        # Rate limiting: max 3 subscription creates per email per hour
        cutoff = timezone.now() - timezone.timedelta(hours=SUBSCRIBE_RATE_WINDOW_HOURS)
        recent_count = AlertSubscription.objects.filter(
            email=email,
            created_at__gte=cutoff,
        ).count()
        if recent_count >= SUBSCRIBE_RATE_LIMIT:
            return Response(
                api_error(message="Rate limit exceeded. Maximum 3 subscription requests per hour."),
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Get or create subscription
        subscription, created = AlertSubscription.objects.get_or_create(
            email=email,
            defaults={
                "operator_filter": operator_filter,
                "is_active": True,
            },
        )

        if not created:
            # Reactivate if previously deactivated
            if not subscription.is_active:
                subscription.is_active = True
            if operator_filter:
                subscription.operator_filter = operator_filter
            subscription.save(update_fields=["is_active", "operator_filter", "updated_at"])

        # Link user if authenticated
        if request.user and request.user.is_authenticated and not subscription.user:
            subscription.user = request.user
            subscription.save(update_fields=["user", "updated_at"])

        # Set categories
        categories = AlertCategory.objects.filter(
            code__in=category_codes,
            is_active=True,
            is_deleted=False,
        )
        subscription.categories.set(categories)

        result = AlertSubscriptionDetailSerializer(subscription)

        msg = "Subscription created." if created else "Subscription updated."
        if not subscription.is_confirmed:
            msg += " Please check your email to confirm."

        return Response(
            api_success(message=msg, data=result.data),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConfirmSubscriptionView(APIView):
    """GET confirm subscription via email token."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Alerts"],
        summary="Confirm subscription",
        description="Confirm an alert subscription using the token from the confirmation email.",
    )
    def get(self, request, token):
        try:
            subscription = AlertSubscription.objects.get(
                confirm_token=token,
                is_deleted=False,
            )
        except AlertSubscription.DoesNotExist:
            return Response(
                api_error(message="Invalid or expired confirmation token."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if subscription.is_confirmed:
            return Response(api_success(
                message="Subscription already confirmed.",
                data={"email": subscription.email, "confirmed_at": str(subscription.confirmed_at)},
            ))

        # Check token expiry (72 hours)
        if subscription.is_token_expired:
            return Response(
                api_error(message="Confirmation token has expired. Please subscribe again."),
                status=status.HTTP_410_GONE,
            )

        subscription.is_confirmed = True
        subscription.confirmed_at = timezone.now()
        subscription.save(update_fields=["is_confirmed", "confirmed_at", "updated_at"])

        return Response(api_success(
            message="Subscription confirmed successfully!",
            data={
                "email": subscription.email,
                "confirmed_at": str(subscription.confirmed_at),
                "categories": list(subscription.categories.values_list("code", flat=True)),
            },
        ))


class UnsubscribeView(APIView):
    """GET one-click unsubscribe via token. No login required."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Alerts"],
        summary="Unsubscribe from alerts",
        description="One-click unsubscribe using the token from any alert email. No login required.",
    )
    def get(self, request, token):
        try:
            subscription = AlertSubscription.objects.get(
                unsubscribe_token=token,
                is_deleted=False,
            )
        except AlertSubscription.DoesNotExist:
            return Response(
                api_error(message="Invalid unsubscribe token."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if not subscription.is_active:
            return Response(api_success(
                message="Already unsubscribed.",
                data={"email": subscription.email},
            ))

        subscription.is_active = False
        subscription.save(update_fields=["is_active", "updated_at"])

        return Response(api_success(
            message="Successfully unsubscribed. You will no longer receive alerts.",
            data={"email": subscription.email},
        ))


# -- AUTHENTICATED VIEWS -------------------------------------------------------

class MySubscriptionsView(APIView):
    """GET list authenticated user's subscriptions."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Alerts"],
        summary="Get my subscriptions",
        description="Returns the authenticated user's alert subscriptions.",
        responses={200: AlertSubscriptionDetailSerializer},
    )
    def get(self, request):
        subscriptions = AlertSubscription.objects.filter(
            Q(user=request.user) | Q(email=request.user.email),
            is_deleted=False,
        ).prefetch_related("categories").distinct()

        serializer = AlertSubscriptionDetailSerializer(subscriptions, many=True)
        return Response(api_success(
            message="Subscriptions retrieved.",
            data=serializer.data,
        ))


class UpdateSubscriptionView(APIView):
    """PATCH update authenticated user's subscription categories."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Alerts"],
        summary="Update my subscription",
        description="Update the categories and/or operator filter for your subscription.",
        request=AlertSubscriptionUpdateSerializer,
        responses={200: AlertSubscriptionDetailSerializer},
    )
    def patch(self, request):
        try:
            subscription = AlertSubscription.objects.get(
                Q(user=request.user) | Q(email=request.user.email),
                is_deleted=False,
            )
        except AlertSubscription.DoesNotExist:
            return Response(
                api_error(message="No subscription found for your account."),
                status=status.HTTP_404_NOT_FOUND,
            )
        except AlertSubscription.MultipleObjectsReturned:
            subscription = AlertSubscription.objects.filter(
                Q(user=request.user) | Q(email=request.user.email),
                is_deleted=False,
            ).first()

        serializer = AlertSubscriptionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_error(message="Validation failed.", errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update categories
        category_codes = serializer.validated_data["categories"]
        categories = AlertCategory.objects.filter(
            code__in=category_codes,
            is_active=True,
            is_deleted=False,
        )
        subscription.categories.set(categories)

        # Update operator filter if provided
        if "operator_filter" in serializer.validated_data:
            subscription.operator_filter = serializer.validated_data["operator_filter"]
            subscription.save(update_fields=["operator_filter", "updated_at"])

        result = AlertSubscriptionDetailSerializer(subscription)
        return Response(api_success(
            message="Subscription updated.",
            data=result.data,
        ))


class DeleteSubscriptionView(APIView):
    """DELETE remove authenticated user's subscription."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Alerts"],
        summary="Delete my subscription",
        description="Permanently delete your alert subscription.",
    )
    def delete(self, request):
        deleted_count = AlertSubscription.objects.filter(
            Q(user=request.user) | Q(email=request.user.email),
            is_deleted=False,
        ).update(is_deleted=True, deleted_at=timezone.now())

        if deleted_count == 0:
            return Response(
                api_error(message="No subscription found for your account."),
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(api_success(
            message="Subscription deleted.",
            data={"deleted": deleted_count},
        ))


# -- STAFF VIEWS ---------------------------------------------------------------

class AlertLogsView(APIView):
    """GET alert sending audit log. Staff only."""

    permission_classes = [IsStaff]

    @extend_schema(
        tags=["Alerts -- Staff"],
        summary="List alert logs",
        description="Returns paginated alert sending audit log.",
        parameters=[
            OpenApiParameter("category", OpenApiTypes.STR, description="Filter by category code"),
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter: PENDING, SENT, FAILED"),
            OpenApiParameter("date_from", OpenApiTypes.DATE, description="Logs from this date"),
            OpenApiParameter("date_to", OpenApiTypes.DATE, description="Logs up to this date"),
            OpenApiParameter("page", OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT),
        ],
        responses={200: AlertLogSerializer(many=True)},
    )
    def get(self, request):
        qs = AlertLog.objects.filter(
            is_deleted=False,
        ).select_related("subscription", "category")

        # Filters
        category_code = request.query_params.get("category")
        if category_code:
            qs = qs.filter(category__code__iexact=category_code)

        log_status = request.query_params.get("status")
        if log_status:
            qs = qs.filter(status=log_status.upper())

        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        paginator = AlertLogPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AlertLogSerializer(page, many=True)

        return Response(api_success(
            message="Alert logs retrieved.",
            data={
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data,
            },
        ))


class AlertStatsView(APIView):
    """GET subscription and delivery analytics. Staff only."""

    permission_classes = [IsStaff]

    @extend_schema(
        tags=["Alerts -- Staff"],
        summary="Subscription analytics",
        description=(
            "Returns subscription analytics: total/confirmed/active counts, "
            "per-category breakdown, delivery stats."
        ),
        parameters=[
            OpenApiParameter("days", OpenApiTypes.INT, description="Lookback window in days (default 30)"),
        ],
    )
    def get(self, request):
        days = int(request.query_params.get("days", 30))
        cutoff = timezone.now() - timezone.timedelta(days=days)

        # Subscription stats
        total_subs = AlertSubscription.objects.filter(is_deleted=False).count()
        confirmed_subs = AlertSubscription.objects.filter(
            is_deleted=False, is_confirmed=True,
        ).count()
        active_subs = AlertSubscription.objects.filter(
            is_deleted=False, is_confirmed=True, is_active=True,
        ).count()
        recent_subs = AlertSubscription.objects.filter(
            is_deleted=False, created_at__gte=cutoff,
        ).count()

        # Per-category subscription counts
        by_category = []
        categories = AlertCategory.objects.filter(is_deleted=False, is_active=True)
        for cat in categories:
            sub_count = cat.subscriptions.filter(
                is_deleted=False, is_confirmed=True, is_active=True,
            ).count()
            by_category.append({
                "code": cat.code,
                "name": cat.name,
                "active_subscribers": sub_count,
            })
        by_category.sort(key=lambda x: x["active_subscribers"], reverse=True)

        # Delivery stats
        recent_logs = AlertLog.objects.filter(
            is_deleted=False, created_at__gte=cutoff,
        )
        total_sent = recent_logs.filter(status=AlertStatus.SENT).count()
        total_failed = recent_logs.filter(status=AlertStatus.FAILED).count()
        total_pending = recent_logs.filter(status=AlertStatus.PENDING).count()

        # Per-category delivery
        delivery_by_category = list(
            recent_logs.values(
                "category__code", "category__name",
            ).annotate(
                total=Count("id"),
                sent=Count("id", filter=Q(status=AlertStatus.SENT)),
                failed=Count("id", filter=Q(status=AlertStatus.FAILED)),
            ).order_by("-total")
        )

        return Response(api_success(
            message="Alert statistics retrieved.",
            data={
                "days": days,
                "subscriptions": {
                    "total": total_subs,
                    "confirmed": confirmed_subs,
                    "active": active_subs,
                    "recent_signups": recent_subs,
                },
                "by_category": by_category,
                "delivery": {
                    "total_sent": total_sent,
                    "total_failed": total_failed,
                    "total_pending": total_pending,
                    "by_category": delivery_by_category,
                },
            },
        ))

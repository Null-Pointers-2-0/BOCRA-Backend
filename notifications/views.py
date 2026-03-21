"""
Notifications API views.

All responses use the standard BOCRA envelope:
    { "success": bool, "message": str, "data": ..., "errors": ... }

Endpoints
─────────
GET    /api/v1/notifications/                       MyNotificationsView          [Registered]
GET    /api/v1/notifications/unread-count/           UnreadCountView              [Registered]
PATCH  /api/v1/notifications/<pk>/read/              MarkReadView                 [Owner]
PATCH  /api/v1/notifications/read-all/               MarkAllReadView              [Registered]
DELETE /api/v1/notifications/<pk>/                   DismissNotificationView      [Owner]
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, serializers as drf_serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiTypes

from core.utils import api_error, api_success
from .models import Notification
from .serializers import NotificationSerializer


# ─── LIST MY NOTIFICATIONS ────────────────────────────────────────────────────

@extend_schema(tags=["Notifications"], summary="List my notifications")
class MyNotificationsView(generics.ListAPIView):
    """
    GET /api/v1/notifications/

    Returns all notifications for the authenticated user, newest first.
    Auth: Registered
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(
            api_success(serializer.data, "Notifications retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── UNREAD COUNT ─────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Notifications"],
    summary="Get unread notification count",
    responses={200: OpenApiTypes.OBJECT},
)
class UnreadCountView(generics.GenericAPIView):
    """
    GET /api/v1/notifications/unread-count/

    Quick badge count for the UI.
    Auth: Registered
    """

    permission_classes = [IsAuthenticated]
    serializer_class = drf_serializers.Serializer

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response(
            api_success({"unread_count": count}, "Unread count retrieved."),
            status=status.HTTP_200_OK,
        )


# ─── MARK SINGLE READ ────────────────────────────────────────────────────────

class MarkReadView(generics.GenericAPIView):
    """
    PATCH /api/v1/notifications/<pk>/read/

    Mark a single notification as read.
    Auth: Owner
    """

    permission_classes = [IsAuthenticated]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Notifications"], summary="Mark notification as read", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        notification = get_object_or_404(
            Notification, pk=pk, recipient=request.user
        )
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(
            api_success(
                NotificationSerializer(notification).data,
                "Notification marked as read.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── MARK ALL READ ───────────────────────────────────────────────────────────

class MarkAllReadView(generics.GenericAPIView):
    """
    PATCH /api/v1/notifications/read-all/

    Mark all unread notifications as read.
    Auth: Registered
    """

    permission_classes = [IsAuthenticated]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Notifications"], summary="Mark all notifications as read", responses={200: OpenApiTypes.OBJECT})
    def patch(self, request):
        now = timezone.now()
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=now)
        return Response(
            api_success(
                {"marked_read": updated},
                f"{updated} notification(s) marked as read.",
            ),
            status=status.HTTP_200_OK,
        )


# ─── DISMISS ──────────────────────────────────────────────────────────────────

class DismissNotificationView(generics.GenericAPIView):
    """
    DELETE /api/v1/notifications/<pk>/

    Permanently delete a notification.
    Auth: Owner
    """

    permission_classes = [IsAuthenticated]
    serializer_class = drf_serializers.Serializer

    @extend_schema(tags=["Notifications"], summary="Dismiss a notification", responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk):
        notification = get_object_or_404(
            Notification, pk=pk, recipient=request.user
        )
        notification.delete()
        return Response(
            api_success(None, "Notification dismissed."),
            status=status.HTTP_200_OK,
        )

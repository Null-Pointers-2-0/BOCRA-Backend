"""
Notifications URL configuration.

Base: /api/v1/notifications/
"""

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("unread-count/", views.UnreadCountView.as_view(), name="unread-count"),
    path("read-all/", views.MarkAllReadView.as_view(), name="read-all"),
    path("<uuid:pk>/read/", views.MarkReadView.as_view(), name="mark-read"),
    path("<uuid:pk>/", views.DismissNotificationView.as_view(), name="dismiss"),
    path("", views.MyNotificationsView.as_view(), name="list"),
]

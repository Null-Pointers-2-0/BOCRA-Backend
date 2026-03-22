"""
Notification serializers.
"""
from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title", "message", "is_read",
            "read_at", "status", "related_object_type", "related_object_id",
            "created_at",
        ]
        read_only_fields = fields

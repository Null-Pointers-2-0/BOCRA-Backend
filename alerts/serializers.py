"""
Alerts app serializers.

Public
------
AlertCategorySerializer         -- Category listing
AlertSubscribeSerializer        -- Subscribe to categories (POST)
AlertSubscriptionDetailSerializer -- Subscription detail with categories

Staff
-----
AlertLogSerializer              -- Alert sending audit log
"""
from rest_framework import serializers

from .models import AlertCategory, AlertLog, AlertSubscription


class AlertCategorySerializer(serializers.ModelSerializer):
    """Public category listing."""

    class Meta:
        model = AlertCategory
        fields = [
            "id",
            "name",
            "code",
            "description",
            "icon",
            "is_public",
            "is_active",
            "sort_order",
        ]


class AlertSubscribeSerializer(serializers.Serializer):
    """
    Subscribe an email to alert categories.
    Accepts email + list of category codes.
    """

    email = serializers.EmailField()
    categories = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=1,
        help_text="List of category codes to subscribe to.",
    )
    operator_filter = serializers.CharField(
        max_length=20,
        required=False,
        default="",
        help_text="Optional operator code filter (MASCOM, ORANGE, BTCL).",
    )

    def validate_categories(self, value):
        valid_codes = set(
            AlertCategory.objects.filter(
                is_active=True, is_deleted=False,
            ).values_list("code", flat=True)
        )
        invalid = [c for c in value if c not in valid_codes]
        if invalid:
            raise serializers.ValidationError(
                f"Invalid category codes: {', '.join(invalid)}. "
                f"Valid codes: {', '.join(sorted(valid_codes))}"
            )
        return value

    def validate_operator_filter(self, value):
        if value:
            valid_ops = {"MASCOM", "ORANGE", "BTCL"}
            if value.upper() not in valid_ops:
                raise serializers.ValidationError(
                    f"Invalid operator. Must be one of: {', '.join(sorted(valid_ops))}"
                )
            return value.upper()
        return value


class AlertSubscriptionDetailSerializer(serializers.ModelSerializer):
    """Subscription detail with nested categories."""

    categories = AlertCategorySerializer(many=True, read_only=True)

    class Meta:
        model = AlertSubscription
        fields = [
            "id",
            "email",
            "categories",
            "is_confirmed",
            "confirmed_at",
            "operator_filter",
            "is_active",
            "created_at",
        ]


class AlertSubscriptionUpdateSerializer(serializers.Serializer):
    """Update subscription categories."""

    categories = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=1,
        help_text="New list of category codes.",
    )
    operator_filter = serializers.CharField(
        max_length=20,
        required=False,
        help_text="Optional operator code filter.",
    )

    def validate_categories(self, value):
        valid_codes = set(
            AlertCategory.objects.filter(
                is_active=True, is_deleted=False,
            ).values_list("code", flat=True)
        )
        invalid = [c for c in value if c not in valid_codes]
        if invalid:
            raise serializers.ValidationError(
                f"Invalid category codes: {', '.join(invalid)}"
            )
        return value


class AlertLogSerializer(serializers.ModelSerializer):
    """Alert log for staff audit trail."""

    subscription_email = serializers.CharField(
        source="subscription.email", read_only=True,
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True,
    )
    category_code = serializers.CharField(
        source="category.code", read_only=True,
    )

    class Meta:
        model = AlertLog
        fields = [
            "id",
            "subscription",
            "subscription_email",
            "category",
            "category_name",
            "category_code",
            "subject",
            "body_preview",
            "related_object_type",
            "related_object_id",
            "status",
            "sent_at",
            "error_message",
            "created_at",
        ]

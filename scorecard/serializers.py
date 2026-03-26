"""
Scorecard app serializers.

Public
------
ScorecardWeightSerializer      -- Weight config (read for public, write for admin)
OperatorScoreSerializer        -- Monthly operator score with all dimensions
OperatorScoreDetailSerializer  -- Extended detail with metadata

Staff
-----
ManualMetricEntrySerializer    -- Manual metric CRUD
"""
from rest_framework import serializers

from .models import ManualMetricEntry, OperatorScore, ScorecardWeightConfig


class ScorecardWeightSerializer(serializers.ModelSerializer):
    """Serializer for scorecard weight configuration."""

    dimension_display = serializers.CharField(
        source="get_dimension_display", read_only=True,
    )

    class Meta:
        model = ScorecardWeightConfig
        fields = [
            "id",
            "dimension",
            "dimension_display",
            "weight",
            "description",
            "updated_at",
        ]
        read_only_fields = ["id", "dimension_display", "updated_at"]


class ScorecardWeightUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a single weight."""

    class Meta:
        model = ScorecardWeightConfig
        fields = ["weight", "description"]


class OperatorScoreSerializer(serializers.ModelSerializer):
    """Public operator score serializer with denormalized operator info."""

    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)

    class Meta:
        model = OperatorScore
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "period",
            "coverage_score",
            "qoe_score",
            "complaints_score",
            "qos_score",
            "composite_score",
            "rank",
            "created_at",
        ]


class OperatorScoreDetailSerializer(serializers.ModelSerializer):
    """Extended detail including metadata with calculation breakdown."""

    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)

    class Meta:
        model = OperatorScore
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "period",
            "coverage_score",
            "qoe_score",
            "complaints_score",
            "qos_score",
            "composite_score",
            "rank",
            "metadata",
            "created_at",
            "updated_at",
        ]


class ManualMetricEntrySerializer(serializers.ModelSerializer):
    """Serializer for staff-entered manual metrics."""

    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)
    entered_by_email = serializers.SerializerMethodField()

    class Meta:
        model = ManualMetricEntry
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "period",
            "metric_name",
            "value",
            "unit",
            "entered_by",
            "entered_by_email",
            "created_at",
        ]
        read_only_fields = ["id", "operator_name", "operator_code", "entered_by", "entered_by_email", "created_at"]

    def get_entered_by_email(self, obj):
        return obj.entered_by.email if obj.entered_by else None

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["entered_by"] = request.user
        return super().create(validated_data)

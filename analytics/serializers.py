"""
Analytics app serializers.

Public
──────
NetworkOperatorSerializer   — operator info
TelecomsStatSerializer      — subscriber / market data
QoSRecordSerializer         — quality of service measurements

Dashboard
─────────
PublicDashboardSerializer   — aggregated public-safe stats
StaffDashboardSerializer    — full operational dashboard
"""
from rest_framework import serializers

from .models import NetworkOperator, QoSRecord, TelecomsStat


# ─── NETWORK OPERATOR ─────────────────────────────────────────────────────────

class NetworkOperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkOperator
        fields = ["id", "name", "code", "logo", "is_active"]


# ─── TELECOMS STAT ─────────────────────────────────────────────────────────────

class TelecomsStatSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)

    class Meta:
        model = TelecomsStat
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "period",
            "technology",
            "subscriber_count",
            "market_share_percent",
            "revenue",
        ]


# ─── QOS RECORD ────────────────────────────────────────────────────────────────

class QoSRecordSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)
    metric_type_display = serializers.CharField(
        source="get_metric_type_display", read_only=True
    )
    meets_benchmark = serializers.ReadOnlyField()

    class Meta:
        model = QoSRecord
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "period",
            "metric_type",
            "metric_type_display",
            "value",
            "unit",
            "region",
            "benchmark",
            "meets_benchmark",
        ]

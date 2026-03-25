"""
QoE Reporter app serializers.

Public
------
QoEReportSubmitSerializer   -- Citizen submission (POST /reports/)
QoEReportListSerializer     -- Staff listing with full detail

Read-only / aggregation serializers are built inline in views.
"""
import hashlib
from decimal import Decimal

from rest_framework import serializers

from coverages.models import District
from .models import ConnectionType, QoEReport, ServiceType


class QoEReportSubmitSerializer(serializers.ModelSerializer):
    """
    Serializer for citizen QoE report submission.

    Accepts operator UUID, service/connection type, rating, optional speed
    test data, optional location, and optional description.
    Handles coordinate rounding, district auto-resolution, and IP hashing.
    """

    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    district_code = serializers.CharField(source="district.code", read_only=True)

    class Meta:
        model = QoEReport
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "service_type",
            "connection_type",
            "rating",
            "download_speed",
            "upload_speed",
            "latency_ms",
            "latitude",
            "longitude",
            "district",
            "district_name",
            "district_code",
            "description",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "operator_name",
            "operator_code",
            "district_name",
            "district_code",
            "submitted_at",
        ]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_latitude(self, value):
        if value is not None:
            if value < Decimal("-90") or value > Decimal("90"):
                raise serializers.ValidationError("Latitude must be between -90 and 90.")
            # Round to 3 decimal places for privacy (~100m precision)
            return round(value, 3)
        return value

    def validate_longitude(self, value):
        if value is not None:
            if value < Decimal("-180") or value > Decimal("180"):
                raise serializers.ValidationError("Longitude must be between -180 and 180.")
            return round(value, 3)
        return value

    def validate_description(self, value):
        if len(value) > 1000:
            raise serializers.ValidationError("Description must be 1000 characters or fewer.")
        return value

    def _resolve_district(self, latitude, longitude):
        """
        Resolve district from coordinates using bounding-box lookup
        against District boundary GeoJSON.
        Simple point-in-bounding-box check (not full polygon intersection).
        """
        if latitude is None or longitude is None:
            return None

        lat = float(latitude)
        lng = float(longitude)

        districts = District.objects.filter(is_active=True, is_deleted=False)
        for district in districts:
            boundary = district.boundary_geojson
            if not boundary:
                continue

            coords = boundary.get("coordinates", [])
            if not coords:
                continue

            # Get the outer ring (first ring of the polygon)
            ring = coords[0] if boundary.get("type") == "Polygon" else coords[0][0]
            if not ring:
                continue

            # Bounding box check
            lngs = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            if min(lngs) <= lng <= max(lngs) and min(lats) <= lat <= max(lats):
                return district

        return None

    def _hash_ip(self, ip_address):
        """SHA-256 hash of IP address for rate limiting."""
        if not ip_address:
            return ""
        return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()

    def _get_client_ip(self):
        """Extract client IP from request."""
        request = self.context.get("request")
        if not request:
            return ""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def create(self, validated_data):
        request = self.context.get("request")

        # Set submitted_by if authenticated
        if request and request.user and request.user.is_authenticated:
            validated_data["submitted_by"] = request.user

        # Auto-resolve district from coordinates if not provided
        if not validated_data.get("district"):
            district = self._resolve_district(
                validated_data.get("latitude"),
                validated_data.get("longitude"),
            )
            if district:
                validated_data["district"] = district

        # Hash IP for rate limiting
        client_ip = self._get_client_ip()
        validated_data["ip_hash"] = self._hash_ip(client_ip)

        return super().create(validated_data)


class QoEReportListSerializer(serializers.ModelSerializer):
    """
    Full report detail for staff listing.
    Includes denormalised operator/district names and submitter info.
    """

    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)
    district_name = serializers.SerializerMethodField()
    district_code = serializers.SerializerMethodField()
    submitted_by_email = serializers.SerializerMethodField()
    service_type_display = serializers.CharField(
        source="get_service_type_display", read_only=True,
    )
    connection_type_display = serializers.CharField(
        source="get_connection_type_display", read_only=True,
    )

    class Meta:
        model = QoEReport
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "service_type",
            "service_type_display",
            "connection_type",
            "connection_type_display",
            "rating",
            "download_speed",
            "upload_speed",
            "latency_ms",
            "latitude",
            "longitude",
            "district",
            "district_name",
            "district_code",
            "description",
            "submitted_by",
            "submitted_by_email",
            "submitted_at",
            "ip_hash",
            "is_verified",
            "is_flagged",
            "created_at",
        ]

    def get_district_name(self, obj):
        return obj.district.name if obj.district else None

    def get_district_code(self, obj):
        return obj.district.code if obj.district else None

    def get_submitted_by_email(self, obj):
        return obj.submitted_by.email if obj.submitted_by else None

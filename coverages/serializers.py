"""
Coverages app serializers.

Public
------
DistrictSerializer            -- District info (without heavy GeoJSON)
DistrictDetailSerializer      -- District with full boundary GeoJSON
DistrictGeoJSONSerializer     -- GeoJSON Feature format for Leaflet
CoverageAreaSerializer        -- Coverage record with operator/district names
CoverageAreaGeoJSONSerializer -- GeoJSON Feature format for map overlay

Staff
-----
CoverageUploadSerializer      -- Upload creation and listing
"""
from rest_framework import serializers

from analytics.serializers import NetworkOperatorSerializer
from .models import CoverageArea, CoverageUpload, District


# -- DISTRICT ------------------------------------------------------------------

class DistrictListSerializer(serializers.ModelSerializer):
    """Lightweight district info -- no boundary GeoJSON for list views."""

    class Meta:
        model = District
        fields = [
            "id",
            "name",
            "code",
            "region",
            "population",
            "area_sq_km",
            "center_lat",
            "center_lng",
            "is_active",
        ]


class DistrictDetailSerializer(serializers.ModelSerializer):
    """Full district detail including boundary GeoJSON."""

    class Meta:
        model = District
        fields = [
            "id",
            "name",
            "code",
            "region",
            "population",
            "area_sq_km",
            "boundary_geojson",
            "center_lat",
            "center_lng",
            "is_active",
        ]


class DistrictGeoJSONSerializer(serializers.ModelSerializer):
    """
    Serialise a District as a GeoJSON Feature.
    The boundary_geojson becomes the geometry; other fields become properties.
    """

    type = serializers.SerializerMethodField()
    geometry = serializers.JSONField(source="boundary_geojson")
    properties = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = ["type", "geometry", "properties"]

    def get_type(self, obj):
        return "Feature"

    def get_properties(self, obj):
        return {
            "id": str(obj.id),
            "name": obj.name,
            "code": obj.code,
            "region": obj.region,
            "population": obj.population,
            "area_sq_km": float(obj.area_sq_km) if obj.area_sq_km else None,
            "center_lat": float(obj.center_lat) if obj.center_lat else None,
            "center_lng": float(obj.center_lng) if obj.center_lng else None,
        }


# -- COVERAGE AREA -------------------------------------------------------------

class CoverageAreaSerializer(serializers.ModelSerializer):
    """Standard coverage record with denormalized operator and district names."""

    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    district_code = serializers.CharField(source="district.code", read_only=True)
    coverage_level_display = serializers.CharField(
        source="get_coverage_level_display", read_only=True
    )

    class Meta:
        model = CoverageArea
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "district",
            "district_name",
            "district_code",
            "technology",
            "coverage_level",
            "coverage_level_display",
            "coverage_percentage",
            "population_covered",
            "signal_strength_avg",
            "period",
            "source",
            "notes",
        ]


class CoverageAreaGeoJSONSerializer(serializers.ModelSerializer):
    """
    Serialise a CoverageArea as a GeoJSON Feature for Leaflet map overlay.
    Uses geometry_geojson if present, otherwise falls back to district boundary.
    """

    type = serializers.SerializerMethodField()
    geometry = serializers.SerializerMethodField()
    properties = serializers.SerializerMethodField()

    class Meta:
        model = CoverageArea
        fields = ["type", "geometry", "properties"]

    def get_type(self, obj):
        return "Feature"

    def get_geometry(self, obj):
        if obj.geometry_geojson:
            return obj.geometry_geojson
        return obj.district.boundary_geojson

    def get_properties(self, obj):
        return {
            "id": str(obj.id),
            "operator": obj.operator.code,
            "operator_name": obj.operator.name,
            "technology": obj.technology,
            "coverage_level": obj.coverage_level,
            "coverage_percentage": float(obj.coverage_percentage),
            "district": obj.district.name,
            "district_code": obj.district.code,
            "period": str(obj.period),
            "population_covered": obj.population_covered,
        }


# -- COVERAGE UPLOAD -----------------------------------------------------------

class CoverageUploadSerializer(serializers.ModelSerializer):
    """Serializer for admin coverage data uploads."""

    operator_name = serializers.CharField(source="operator.name", read_only=True)
    operator_code = serializers.CharField(source="operator.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CoverageUpload
        fields = [
            "id",
            "operator",
            "operator_name",
            "operator_code",
            "technology",
            "file",
            "file_name",
            "file_size",
            "period",
            "status",
            "status_display",
            "records_created",
            "error_message",
            "processed_at",
            "created_at",
            "created_by",
        ]
        read_only_fields = [
            "id",
            "file_name",
            "file_size",
            "status",
            "records_created",
            "error_message",
            "processed_at",
            "created_at",
            "created_by",
        ]

    def create(self, validated_data):
        upload_file = validated_data.get("file")
        if upload_file:
            validated_data["file_name"] = upload_file.name
            validated_data["file_size"] = upload_file.size
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
            validated_data["modified_by"] = request.user
        return super().create(validated_data)

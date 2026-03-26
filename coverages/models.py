"""
Coverages app models.

Entities
--------
District       -- Botswana administrative district with boundary GeoJSON.
CoverageArea   -- Network coverage record per operator / district / technology.
CoverageUpload -- Audit trail for admin uploads of coverage data.
"""
from django.db import models

from core.models import AuditableModel, BaseModel
from analytics.models import Technology


# -- ENUMS ---------------------------------------------------------------------

class CoverageLevel(models.TextChoices):
    FULL    = "FULL",    "Full (80-100%)"
    PARTIAL = "PARTIAL", "Partial (30-79%)"
    MINIMAL = "MINIMAL", "Minimal (1-29%)"
    NONE    = "NONE",    "None (0%)"


class CoverageSource(models.TextChoices):
    BOCRA               = "BOCRA",               "BOCRA Internal Data"
    OPERATOR_SUBMISSION = "OPERATOR_SUBMISSION",  "Operator Submission"
    ESTIMATED           = "ESTIMATED",            "Estimated / Extrapolated"


class UploadStatus(models.TextChoices):
    PENDING    = "PENDING",    "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED  = "COMPLETED",  "Completed"
    FAILED     = "FAILED",     "Failed"


# -- DISTRICT ------------------------------------------------------------------

class District(BaseModel):
    """Botswana administrative district with boundary GeoJSON for map rendering."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    region = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Broader region grouping.",
    )
    population = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Approximate population from latest census.",
    )
    area_sq_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Area in square kilometres.",
    )
    boundary_geojson = models.JSONField(
        help_text="GeoJSON Polygon or MultiPolygon of district boundary.",
    )
    center_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Centre latitude for map positioning.",
    )
    center_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Centre longitude for map positioning.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "District"
        verbose_name_plural = "Districts"

    def __str__(self):
        return f"{self.name} ({self.code})"


# -- COVERAGE AREA -------------------------------------------------------------

class CoverageArea(BaseModel):
    """
    Network coverage record linking an operator to a district at a specific
    technology tier for a given reporting period.
    """

    operator = models.ForeignKey(
        "analytics.NetworkOperator",
        on_delete=models.CASCADE,
        related_name="coverage_areas",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name="coverage_areas",
    )
    technology = models.CharField(
        max_length=5,
        choices=Technology.choices,
        db_index=True,
    )
    coverage_level = models.CharField(
        max_length=10,
        choices=CoverageLevel.choices,
        db_index=True,
    )
    coverage_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Numeric coverage percentage (0-100).",
    )
    population_covered = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated population with access.",
    )
    geometry_geojson = models.JSONField(
        null=True,
        blank=True,
        help_text="Coverage polygon GeoJSON (if different from full district boundary).",
    )
    signal_strength_avg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Average signal strength in dBm.",
    )
    period = models.DateField(
        db_index=True,
        help_text="Reporting period (first day of quarter).",
    )
    source = models.CharField(
        max_length=25,
        choices=CoverageSource.choices,
        default=CoverageSource.BOCRA,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-period", "operator__name", "district__name"]
        verbose_name = "Coverage Area"
        verbose_name_plural = "Coverage Areas"
        unique_together = [("operator", "district", "technology", "period")]

    def __str__(self):
        return (
            f"{self.operator.code} - {self.district.code} - "
            f"{self.technology} - {self.coverage_level} ({self.period})"
        )


# -- COVERAGE UPLOAD -----------------------------------------------------------

class CoverageUpload(AuditableModel):
    """
    Tracks admin uploads of coverage data from operator submissions.
    Each upload is processed asynchronously and creates CoverageArea records.
    """

    operator = models.ForeignKey(
        "analytics.NetworkOperator",
        on_delete=models.CASCADE,
        related_name="coverage_uploads",
    )
    technology = models.CharField(
        max_length=5,
        choices=Technology.choices,
    )
    file = models.FileField(upload_to="coverages/uploads/%Y/%m/")
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes.")
    period = models.DateField(help_text="Reporting period this upload covers.")
    status = models.CharField(
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.PENDING,
        db_index=True,
    )
    records_created = models.PositiveIntegerField(
        default=0,
        help_text="Number of CoverageArea records created from this upload.",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error details if processing failed.",
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Coverage Upload"
        verbose_name_plural = "Coverage Uploads"

    def __str__(self):
        return f"Upload: {self.operator.code} - {self.technology} - {self.period} ({self.status})"

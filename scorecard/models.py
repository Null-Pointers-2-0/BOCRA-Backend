"""
Scorecard app models.

Entities
--------
ScorecardWeightConfig  -- Configurable weights for each scoring dimension.
OperatorScore          -- Monthly computed scorecard per operator.
ManualMetricEntry      -- Staff-entered metrics that cannot be auto-computed.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import BaseModel


# -- ENUMS ---------------------------------------------------------------------

class ScoringDimension(models.TextChoices):
    COVERAGE   = "COVERAGE",   "Network Coverage"
    QOE        = "QOE",        "Quality of Experience"
    COMPLAINTS = "COMPLAINTS", "Complaint Handling"
    QOS        = "QOS",        "QoS Compliance"


# -- SCORECARD WEIGHT CONFIG ---------------------------------------------------

class ScorecardWeightConfig(BaseModel):
    """
    Configurable weight for a single scoring dimension.
    BOCRA admin can adjust how the composite score is calculated.
    All weights should sum to 1.0 across all dimensions.
    """

    dimension = models.CharField(
        max_length=20,
        choices=ScoringDimension.choices,
        unique=True,
        db_index=True,
    )
    weight = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Weight value between 0 and 1. All weights should sum to 1.0.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Explanation of what this dimension measures.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scorecard_weight_updates",
    )

    class Meta:
        ordering = ["dimension"]
        verbose_name = "Scorecard Weight"
        verbose_name_plural = "Scorecard Weights"

    def __str__(self):
        return f"{self.get_dimension_display()} = {self.weight}"


# -- OPERATOR SCORE ------------------------------------------------------------

class OperatorScore(BaseModel):
    """
    Monthly computed scorecard for a network operator.
    Each dimension is scored 0-100, and the composite score is the weighted sum.
    """

    operator = models.ForeignKey(
        "analytics.NetworkOperator",
        on_delete=models.CASCADE,
        related_name="scorecard_scores",
    )
    period = models.DateField(
        db_index=True,
        help_text="Reporting period (first day of month).",
    )

    # Individual dimension scores (0-100)
    coverage_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score based on network coverage percentage (0-100).",
    )
    qoe_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score based on citizen QoE ratings (0-100).",
    )
    complaints_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score based on complaint handling (fewer = higher, 0-100).",
    )
    qos_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score based on QoS benchmark compliance (0-100).",
    )

    # Weighted composite
    composite_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weighted composite of all dimension scores (0-100).",
    )
    rank = models.PositiveSmallIntegerField(
        help_text="Rank among operators for this period (1 = best).",
    )

    # Calculation details stored as JSON for transparency
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON with raw values and calculation details.",
    )

    class Meta:
        ordering = ["-period", "rank"]
        verbose_name = "Operator Score"
        verbose_name_plural = "Operator Scores"
        unique_together = [("operator", "period")]
        indexes = [
            models.Index(fields=["operator", "-period"]),
        ]

    def __str__(self):
        return f"{self.operator.code} {self.period} - Rank #{self.rank} ({self.composite_score})"


# -- MANUAL METRIC ENTRY ------------------------------------------------------

class ManualMetricEntry(BaseModel):
    """
    Staff-entered metrics that cannot be auto-computed from existing data.
    Examples: customer satisfaction survey results, infrastructure investment data.
    """

    operator = models.ForeignKey(
        "analytics.NetworkOperator",
        on_delete=models.CASCADE,
        related_name="manual_metrics",
    )
    period = models.DateField(
        db_index=True,
        help_text="Reporting period (first day of month).",
    )
    metric_name = models.CharField(
        max_length=200,
        help_text="Name of the metric (e.g. 'Customer Satisfaction Index').",
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Metric value.",
    )
    unit = models.CharField(
        max_length=50,
        help_text="Unit of measurement (%, score, BWP, etc.).",
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_metric_entries",
    )

    class Meta:
        ordering = ["-period", "operator__name", "metric_name"]
        verbose_name = "Manual Metric Entry"
        verbose_name_plural = "Manual Metric Entries"
        unique_together = [("operator", "period", "metric_name")]

    def __str__(self):
        return f"{self.operator.code} {self.period} - {self.metric_name}: {self.value} {self.unit}"

"""
Analytics app models.

Entities
────────
NetworkOperator  — Telecoms operators (Mascom, BTC, Orange, etc.)
TelecomsStat     — Periodic subscriber / market data per operator.
QoSRecord        — Quality of Service measurements.
"""
from django.db import models

from core.models import BaseModel


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class Technology(models.TextChoices):
    TWO_G  = "2G",  "2G"
    THREE_G = "3G", "3G"
    FOUR_G = "4G",  "4G"
    FIVE_G = "5G",  "5G"


class MetricType(models.TextChoices):
    CALL_SUCCESS = "CALL_SUCCESS", "Call Success Rate"
    DATA_SPEED   = "DATA_SPEED",   "Data Speed"
    LATENCY      = "LATENCY",      "Latency"
    DROP_RATE    = "DROP_RATE",     "Drop Rate"


# ─── NETWORK OPERATOR ─────────────────────────────────────────────────────────

class NetworkOperator(BaseModel):
    """A telecoms network operator in Botswana."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    logo = models.FileField(upload_to="analytics/logos/", null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Network Operator"
        verbose_name_plural = "Network Operators"

    def __str__(self):
        return f"{self.name} ({self.code})"


# ─── TELECOMS STAT ─────────────────────────────────────────────────────────────

class TelecomsStat(BaseModel):
    """Periodic subscriber and market data per operator."""

    operator = models.ForeignKey(
        NetworkOperator,
        on_delete=models.CASCADE,
        related_name="stats",
    )
    period = models.DateField(db_index=True, help_text="Reporting period (first day of month).")
    technology = models.CharField(
        max_length=5,
        choices=Technology.choices,
        db_index=True,
    )
    subscriber_count = models.PositiveIntegerField(default=0)
    market_share_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Revenue in BWP (optional).",
    )

    class Meta:
        ordering = ["-period", "operator__name"]
        verbose_name = "Telecoms Statistic"
        verbose_name_plural = "Telecoms Statistics"
        unique_together = [("operator", "period", "technology")]

    def __str__(self):
        return f"{self.operator.code} — {self.technology} — {self.period}"


# ─── QOS RECORD ────────────────────────────────────────────────────────────────

class QoSRecord(BaseModel):
    """Quality of Service measurement for a network operator."""

    operator = models.ForeignKey(
        NetworkOperator,
        on_delete=models.CASCADE,
        related_name="qos_records",
    )
    period = models.DateField(db_index=True, help_text="Reporting period.")
    metric_type = models.CharField(
        max_length=20,
        choices=MetricType.choices,
        db_index=True,
    )
    value = models.DecimalField(max_digits=10, decimal_places=4)
    unit = models.CharField(max_length=20, help_text="Unit of measurement (%, Mbps, ms, etc.)")
    region = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Geographic region (optional).",
    )
    benchmark = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="BOCRA benchmark/target for this metric.",
    )

    class Meta:
        ordering = ["-period", "operator__name"]
        verbose_name = "QoS Record"
        verbose_name_plural = "QoS Records"

    def __str__(self):
        return f"{self.operator.code} — {self.get_metric_type_display()} — {self.period}"

    @property
    def meets_benchmark(self) -> bool | None:
        """Returns True if value meets/exceeds benchmark, None if no benchmark set."""
        if self.benchmark is None:
            return None
        if self.metric_type in (MetricType.LATENCY, MetricType.DROP_RATE):
            return self.value <= self.benchmark  # lower is better
        return self.value >= self.benchmark  # higher is better

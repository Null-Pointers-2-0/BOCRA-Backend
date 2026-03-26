"""
Seed scorecard data.

Creates:
- 4 ScorecardWeightConfig entries (one per dimension)
- Computes OperatorScore for 6 months (Oct 2025 - Mar 2026)
- 12 ManualMetricEntry entries (2 per operator per quarter)
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import NetworkOperator
from scorecard.models import (
    ManualMetricEntry,
    OperatorScore,
    ScorecardWeightConfig,
    ScoringDimension,
)


# Operator-specific score profiles for realistic data
OPERATOR_PROFILES = {
    "MASCOM": {
        "coverage_base": 78,
        "qoe_base": 65,
        "complaints_base": 82,
        "qos_base": 85,
        "volatility": 3,
    },
    "ORANGE": {
        "coverage_base": 72,
        "qoe_base": 61,
        "complaints_base": 78,
        "qos_base": 80,
        "volatility": 4,
    },
    "BTCL": {
        "coverage_base": 55,
        "qoe_base": 41,
        "complaints_base": 70,
        "qos_base": 65,
        "volatility": 5,
    },
}

MANUAL_METRICS = [
    ("Customer Satisfaction Index", "%", 60, 90),
    ("Infrastructure Investment", "Million BWP", 5, 50),
]


class Command(BaseCommand):
    help = "Seed scorecard data: weights, operator scores (6 months), manual metrics."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing scorecard data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            ScorecardWeightConfig.objects.all().delete()
            OperatorScore.objects.all().delete()
            ManualMetricEntry.objects.all().delete()
            self.stdout.write("Cleared existing scorecard data.")

        operators = list(NetworkOperator.objects.filter(is_active=True, is_deleted=False))
        if not operators:
            self.stderr.write("No active operators found. Run seed_coverages first.")
            return

        # 1. Seed weights
        self._seed_weights()

        # 2. Seed operator scores for 6 months
        self._seed_scores(operators)

        # 3. Seed manual metric entries
        self._seed_manual_metrics(operators)

        self.stdout.write(self.style.SUCCESS("Scorecard seeding complete."))

    def _seed_weights(self):
        defaults = [
            (ScoringDimension.COVERAGE, Decimal("0.30"), "Average network coverage percentage across all districts and technologies."),
            (ScoringDimension.QOE, Decimal("0.30"), "Normalized average citizen QoE rating (1-5 mapped to 0-100)."),
            (ScoringDimension.COMPLAINTS, Decimal("0.20"), "Inverse of complaint volume with resolution rate bonus."),
            (ScoringDimension.QOS, Decimal("0.20"), "QoS benchmark compliance across all reported metrics."),
        ]
        created = 0
        for dimension, weight, description in defaults:
            _, was_created = ScorecardWeightConfig.objects.update_or_create(
                dimension=dimension,
                defaults={
                    "weight": weight,
                    "description": description,
                    "is_deleted": False,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Weights: {created} created, {len(defaults) - created} updated.")

    def _seed_scores(self, operators):
        random.seed(42)
        periods = []
        for month_offset in range(6):
            # Oct 2025 through Mar 2026
            year = 2025 + (9 + month_offset) // 12
            month = (9 + month_offset) % 12 + 1
            periods.append(date(year, month, 1))

        count = 0
        for period in periods:
            scores_for_period = []

            for op in operators:
                profile = OPERATOR_PROFILES.get(op.code, {
                    "coverage_base": 60,
                    "qoe_base": 50,
                    "complaints_base": 75,
                    "qos_base": 70,
                    "volatility": 4,
                })
                v = profile["volatility"]

                # Add slight upward trend over time
                month_idx = periods.index(period)
                trend = Decimal(str(month_idx * 0.5))

                cov = Decimal(str(min(100, max(0, profile["coverage_base"] + random.uniform(-v, v))))) + trend
                qoe = Decimal(str(min(100, max(0, profile["qoe_base"] + random.uniform(-v, v))))) + trend
                comp = Decimal(str(min(100, max(0, profile["complaints_base"] + random.uniform(-v, v))))) + trend
                qos = Decimal(str(min(100, max(0, profile["qos_base"] + random.uniform(-v, v))))) + trend

                # Clamp
                cov = min(Decimal("100"), max(Decimal("0"), cov))
                qoe = min(Decimal("100"), max(Decimal("0"), qoe))
                comp = min(Decimal("100"), max(Decimal("0"), comp))
                qos = min(Decimal("100"), max(Decimal("0"), qos))

                composite = (
                    cov * Decimal("0.30")
                    + qoe * Decimal("0.30")
                    + comp * Decimal("0.20")
                    + qos * Decimal("0.20")
                )
                composite = min(Decimal("100"), max(Decimal("0"), round(composite, 2)))

                scores_for_period.append({
                    "operator": op,
                    "coverage_score": round(cov, 2),
                    "qoe_score": round(qoe, 2),
                    "complaints_score": round(comp, 2),
                    "qos_score": round(qos, 2),
                    "composite_score": composite,
                    "metadata": {
                        "weights": {"coverage": 0.30, "qoe": 0.30, "complaints": 0.20, "qos": 0.20},
                        "seeded": True,
                    },
                })

            # Sort by composite descending to assign ranks
            scores_for_period.sort(key=lambda x: x["composite_score"], reverse=True)

            for rank, data in enumerate(scores_for_period, start=1):
                OperatorScore.objects.update_or_create(
                    operator=data["operator"],
                    period=period,
                    defaults={
                        "coverage_score": data["coverage_score"],
                        "qoe_score": data["qoe_score"],
                        "complaints_score": data["complaints_score"],
                        "qos_score": data["qos_score"],
                        "composite_score": data["composite_score"],
                        "rank": rank,
                        "metadata": data["metadata"],
                        "is_deleted": False,
                    },
                )
                count += 1

        self.stdout.write(f"  Operator scores: {count} records ({len(periods)} months x {len(operators)} operators).")

    def _seed_manual_metrics(self, operators):
        random.seed(99)
        count = 0
        # Two quarters worth of data
        quarters = [date(2025, 10, 1), date(2026, 1, 1)]

        for period in quarters:
            for op in operators:
                for metric_name, unit, low, high in MANUAL_METRICS:
                    value = Decimal(str(round(random.uniform(low, high), 2)))
                    ManualMetricEntry.objects.update_or_create(
                        operator=op,
                        period=period,
                        metric_name=metric_name,
                        defaults={
                            "value": value,
                            "unit": unit,
                            "is_deleted": False,
                        },
                    )
                    count += 1

        self.stdout.write(f"  Manual metrics: {count} entries.")

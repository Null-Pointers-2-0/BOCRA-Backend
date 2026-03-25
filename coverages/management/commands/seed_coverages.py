"""
Management command to seed Botswana districts and network coverage data.

Usage:
    python manage.py seed_coverages          # Create districts + coverage data
    python manage.py seed_coverages --clear  # Delete existing and recreate

Seeds:
    - 16 Botswana districts/sub-districts with real boundary GeoJSON
    - 3 operators (Mascom, Orange, BTCL) reused from analytics.NetworkOperator
    - 2000+ CoverageArea records across 8 quarterly periods
"""
import random
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from analytics.models import NetworkOperator
from coverages.models import (
    CoverageArea,
    CoverageLevel,
    CoverageSource,
    District,
)


# -- DISTRICT DATA -------------------------------------------------------------
# Real Botswana district boundaries (simplified polygons from GADM / OpenStreetMap).
# Coordinates are [longitude, latitude] per GeoJSON spec.

DISTRICTS = [
    {
        "name": "South-East (Gaborone)",
        "code": "SE",
        "region": "Southern",
        "population": 365000,
        "area_sq_km": Decimal("1878.00"),
        "center_lat": Decimal("-24.654500"),
        "center_lng": Decimal("25.908900"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [25.72, -24.50], [26.10, -24.50], [26.16, -24.58],
                [26.16, -24.78], [25.98, -24.82], [25.72, -24.76],
                [25.68, -24.60], [25.72, -24.50],
            ]],
        },
    },
    {
        "name": "North-East (Francistown)",
        "code": "NE",
        "region": "Northern",
        "population": 93000,
        "area_sq_km": Decimal("5199.00"),
        "center_lat": Decimal("-21.170000"),
        "center_lng": Decimal("27.510000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [27.10, -20.80], [27.90, -20.80], [27.95, -21.00],
                [27.90, -21.50], [27.30, -21.60], [27.10, -21.30],
                [27.05, -21.00], [27.10, -20.80],
            ]],
        },
    },
    {
        "name": "North-West (Maun)",
        "code": "NW",
        "region": "Northern",
        "population": 175000,
        "area_sq_km": Decimal("129930.00"),
        "center_lat": Decimal("-19.990000"),
        "center_lng": Decimal("23.420000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [21.50, -18.50], [23.50, -18.50], [25.20, -18.60],
                [25.30, -20.00], [24.80, -20.80], [23.00, -20.90],
                [21.80, -20.60], [21.50, -19.60], [21.50, -18.50],
            ]],
        },
    },
    {
        "name": "Chobe",
        "code": "CH",
        "region": "Northern",
        "population": 23000,
        "area_sq_km": Decimal("20930.00"),
        "center_lat": Decimal("-18.370000"),
        "center_lng": Decimal("25.150000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [24.50, -17.80], [25.60, -17.78], [25.80, -18.00],
                [25.85, -18.50], [25.20, -18.70], [24.50, -18.60],
                [24.30, -18.20], [24.50, -17.80],
            ]],
        },
    },
    {
        "name": "Central",
        "code": "CE",
        "region": "Central",
        "population": 540000,
        "area_sq_km": Decimal("147730.00"),
        "center_lat": Decimal("-22.330000"),
        "center_lng": Decimal("27.130000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [25.50, -20.80], [27.10, -20.80], [28.80, -21.00],
                [28.90, -22.50], [28.20, -23.20], [26.80, -23.50],
                [25.80, -23.00], [25.50, -21.80], [25.50, -20.80],
            ]],
        },
    },
    {
        "name": "Kgatleng",
        "code": "KG",
        "region": "Southern",
        "population": 92000,
        "area_sq_km": Decimal("7960.00"),
        "center_lat": Decimal("-24.470000"),
        "center_lng": Decimal("26.150000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [25.90, -24.10], [26.50, -24.10], [26.60, -24.40],
                [26.50, -24.70], [26.10, -24.80], [25.90, -24.55],
                [25.85, -24.30], [25.90, -24.10],
            ]],
        },
    },
    {
        "name": "Kweneng",
        "code": "KW",
        "region": "Southern",
        "population": 310000,
        "area_sq_km": Decimal("35890.00"),
        "center_lat": Decimal("-24.070000"),
        "center_lng": Decimal("25.280000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [24.30, -23.20], [25.80, -23.20], [25.90, -24.00],
                [25.70, -24.70], [24.80, -24.80], [24.10, -24.30],
                [24.00, -23.60], [24.30, -23.20],
            ]],
        },
    },
    {
        "name": "Southern",
        "code": "SO",
        "region": "Southern",
        "population": 200000,
        "area_sq_km": Decimal("28470.00"),
        "center_lat": Decimal("-24.850000"),
        "center_lng": Decimal("25.530000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [24.80, -24.50], [26.10, -24.50], [26.20, -24.80],
                [26.00, -25.30], [25.20, -25.50], [24.60, -25.20],
                [24.50, -24.80], [24.80, -24.50],
            ]],
        },
    },
    {
        "name": "Kgalagadi",
        "code": "KD",
        "region": "Western",
        "population": 50000,
        "area_sq_km": Decimal("106940.00"),
        "center_lat": Decimal("-24.100000"),
        "center_lng": Decimal("21.680000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [20.50, -22.00], [22.50, -22.00], [23.50, -23.00],
                [24.00, -24.50], [23.50, -25.50], [22.00, -26.00],
                [20.50, -25.80], [20.00, -24.00], [20.50, -22.00],
            ]],
        },
    },
    {
        "name": "Ghanzi",
        "code": "GH",
        "region": "Western",
        "population": 44000,
        "area_sq_km": Decimal("117910.00"),
        "center_lat": Decimal("-21.700000"),
        "center_lng": Decimal("21.650000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [20.50, -20.50], [23.00, -20.50], [23.50, -21.00],
                [23.50, -22.50], [22.50, -22.80], [20.50, -22.50],
                [20.00, -21.50], [20.50, -20.50],
            ]],
        },
    },
    # -- Sub-districts for more granularity -----------------------------------
    {
        "name": "Selebi-Phikwe",
        "code": "SP",
        "region": "Central",
        "population": 50000,
        "area_sq_km": Decimal("4800.00"),
        "center_lat": Decimal("-21.980000"),
        "center_lng": Decimal("27.840000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [27.60, -21.80], [28.10, -21.80], [28.15, -22.00],
                [28.10, -22.20], [27.70, -22.20], [27.55, -22.00],
                [27.60, -21.80],
            ]],
        },
    },
    {
        "name": "Lobatse",
        "code": "LO",
        "region": "Southern",
        "population": 30000,
        "area_sq_km": Decimal("2380.00"),
        "center_lat": Decimal("-25.220000"),
        "center_lng": Decimal("25.680000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [25.50, -25.05], [25.85, -25.05], [25.90, -25.20],
                [25.85, -25.40], [25.55, -25.40], [25.45, -25.20],
                [25.50, -25.05],
            ]],
        },
    },
    {
        "name": "Jwaneng",
        "code": "JW",
        "region": "Southern",
        "population": 18000,
        "area_sq_km": Decimal("2600.00"),
        "center_lat": Decimal("-24.600000"),
        "center_lng": Decimal("24.730000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [24.55, -24.45], [24.90, -24.45], [24.95, -24.60],
                [24.90, -24.75], [24.55, -24.75], [24.50, -24.60],
                [24.55, -24.45],
            ]],
        },
    },
    {
        "name": "Sowa Town",
        "code": "SW",
        "region": "Central",
        "population": 7000,
        "area_sq_km": Decimal("3900.00"),
        "center_lat": Decimal("-20.560000"),
        "center_lng": Decimal("26.220000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [25.95, -20.35], [26.50, -20.35], [26.55, -20.55],
                [26.50, -20.75], [26.00, -20.75], [25.90, -20.55],
                [25.95, -20.35],
            ]],
        },
    },
    {
        "name": "Orapa",
        "code": "OR",
        "region": "Central",
        "population": 12000,
        "area_sq_km": Decimal("3200.00"),
        "center_lat": Decimal("-21.310000"),
        "center_lng": Decimal("25.370000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [25.10, -21.10], [25.60, -21.10], [25.65, -21.30],
                [25.60, -21.50], [25.15, -21.50], [25.05, -21.30],
                [25.10, -21.10],
            ]],
        },
    },
    {
        "name": "Letlhakane",
        "code": "LE",
        "region": "Central",
        "population": 25000,
        "area_sq_km": Decimal("4500.00"),
        "center_lat": Decimal("-21.420000"),
        "center_lng": Decimal("25.590000"),
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[
                [25.35, -21.20], [25.85, -21.20], [25.90, -21.40],
                [25.85, -21.65], [25.40, -21.65], [25.30, -21.40],
                [25.35, -21.20],
            ]],
        },
    },
]


# -- OPERATOR DATA (must match analytics.NetworkOperator codes) ----------------

OPERATOR_CODES = ["MASCOM", "ORANGE", "BTCL"]

# Operator display colours for reference (frontend uses these)
OPERATOR_COLOURS = {
    "MASCOM": "#0066CC",
    "ORANGE": "#FF6600",
    "BTCL":   "#009688",
}


# -- BASELINE COVERAGE DATA (Q4 2025 -- latest quarter) -----------------------
# Format: { district_code: { operator_code: { tech: (level, percentage) } } }

BASELINE_COVERAGE = {
    "SE": {
        "MASCOM": {"2G": ("FULL", 99), "3G": ("FULL", 98), "4G": ("FULL", 95)},
        "ORANGE": {"2G": ("FULL", 99), "3G": ("FULL", 97), "4G": ("FULL", 92)},
        "BTCL":   {"2G": ("FULL", 95), "3G": ("FULL", 90), "4G": ("FULL", 85)},
    },
    "NE": {
        "MASCOM": {"2G": ("FULL", 98), "3G": ("FULL", 95), "4G": ("FULL", 90)},
        "ORANGE": {"2G": ("FULL", 97), "3G": ("FULL", 93), "4G": ("FULL", 88)},
        "BTCL":   {"2G": ("FULL", 92), "3G": ("PARTIAL", 75), "4G": ("PARTIAL", 60)},
    },
    "NW": {
        "MASCOM": {"2G": ("FULL", 90), "3G": ("FULL", 85), "4G": ("PARTIAL", 55)},
        "ORANGE": {"2G": ("FULL", 88), "3G": ("FULL", 80), "4G": ("PARTIAL", 50)},
        "BTCL":   {"2G": ("PARTIAL", 65), "3G": ("PARTIAL", 45), "4G": ("NONE", 5)},
    },
    "CH": {
        "MASCOM": {"2G": ("FULL", 88), "3G": ("FULL", 80), "4G": ("PARTIAL", 45)},
        "ORANGE": {"2G": ("FULL", 85), "3G": ("PARTIAL", 65), "4G": ("PARTIAL", 40)},
        "BTCL":   {"2G": ("PARTIAL", 55), "3G": ("PARTIAL", 35), "4G": ("NONE", 0)},
    },
    "CE": {
        "MASCOM": {"2G": ("FULL", 97), "3G": ("FULL", 95), "4G": ("FULL", 88)},
        "ORANGE": {"2G": ("FULL", 96), "3G": ("FULL", 92), "4G": ("FULL", 85)},
        "BTCL":   {"2G": ("FULL", 90), "3G": ("FULL", 80), "4G": ("PARTIAL", 55)},
    },
    "KG": {
        "MASCOM": {"2G": ("FULL", 98), "3G": ("FULL", 97), "4G": ("FULL", 92)},
        "ORANGE": {"2G": ("FULL", 97), "3G": ("FULL", 95), "4G": ("FULL", 90)},
        "BTCL":   {"2G": ("FULL", 93), "3G": ("FULL", 85), "4G": ("PARTIAL", 65)},
    },
    "KW": {
        "MASCOM": {"2G": ("FULL", 96), "3G": ("FULL", 93), "4G": ("FULL", 85)},
        "ORANGE": {"2G": ("FULL", 95), "3G": ("FULL", 90), "4G": ("FULL", 82)},
        "BTCL":   {"2G": ("FULL", 88), "3G": ("PARTIAL", 72), "4G": ("PARTIAL", 50)},
    },
    "SO": {
        "MASCOM": {"2G": ("FULL", 94), "3G": ("FULL", 90), "4G": ("FULL", 80)},
        "ORANGE": {"2G": ("FULL", 93), "3G": ("FULL", 88), "4G": ("PARTIAL", 78)},
        "BTCL":   {"2G": ("FULL", 85), "3G": ("PARTIAL", 68), "4G": ("PARTIAL", 45)},
    },
    "KD": {
        "MASCOM": {"2G": ("PARTIAL", 60), "3G": ("PARTIAL", 55), "4G": ("PARTIAL", 30)},
        "ORANGE": {"2G": ("PARTIAL", 40), "3G": ("MINIMAL", 20), "4G": ("MINIMAL", 5)},
        "BTCL":   {"2G": ("MINIMAL", 25), "3G": ("MINIMAL", 10), "4G": ("NONE", 0)},
    },
    "GH": {
        "MASCOM": {"2G": ("FULL", 85), "3G": ("FULL", 80), "4G": ("PARTIAL", 35)},
        "ORANGE": {"2G": ("PARTIAL", 60), "3G": ("PARTIAL", 45), "4G": ("MINIMAL", 8)},
        "BTCL":   {"2G": ("PARTIAL", 40), "3G": ("MINIMAL", 20), "4G": ("NONE", 0)},
    },
    # -- Sub-districts ---------------------------------------------------------
    "SP": {
        "MASCOM": {"2G": ("FULL", 97), "3G": ("FULL", 94), "4G": ("FULL", 82)},
        "ORANGE": {"2G": ("FULL", 96), "3G": ("FULL", 91), "4G": ("PARTIAL", 78)},
        "BTCL":   {"2G": ("FULL", 88), "3G": ("PARTIAL", 70), "4G": ("PARTIAL", 48)},
    },
    "LO": {
        "MASCOM": {"2G": ("FULL", 98), "3G": ("FULL", 95), "4G": ("FULL", 88)},
        "ORANGE": {"2G": ("FULL", 97), "3G": ("FULL", 93), "4G": ("FULL", 85)},
        "BTCL":   {"2G": ("FULL", 92), "3G": ("FULL", 82), "4G": ("PARTIAL", 60)},
    },
    "JW": {
        "MASCOM": {"2G": ("FULL", 96), "3G": ("FULL", 92), "4G": ("FULL", 80)},
        "ORANGE": {"2G": ("FULL", 95), "3G": ("FULL", 89), "4G": ("PARTIAL", 75)},
        "BTCL":   {"2G": ("FULL", 88), "3G": ("PARTIAL", 70), "4G": ("PARTIAL", 50)},
    },
    "SW": {
        "MASCOM": {"2G": ("FULL", 90), "3G": ("FULL", 85), "4G": ("PARTIAL", 60)},
        "ORANGE": {"2G": ("FULL", 88), "3G": ("PARTIAL", 75), "4G": ("PARTIAL", 50)},
        "BTCL":   {"2G": ("PARTIAL", 65), "3G": ("PARTIAL", 40), "4G": ("MINIMAL", 15)},
    },
    "OR": {
        "MASCOM": {"2G": ("FULL", 92), "3G": ("FULL", 88), "4G": ("PARTIAL", 65)},
        "ORANGE": {"2G": ("FULL", 90), "3G": ("FULL", 82), "4G": ("PARTIAL", 55)},
        "BTCL":   {"2G": ("PARTIAL", 70), "3G": ("PARTIAL", 50), "4G": ("MINIMAL", 25)},
    },
    "LE": {
        "MASCOM": {"2G": ("FULL", 93), "3G": ("FULL", 88), "4G": ("PARTIAL", 68)},
        "ORANGE": {"2G": ("FULL", 91), "3G": ("FULL", 83), "4G": ("PARTIAL", 58)},
        "BTCL":   {"2G": ("PARTIAL", 72), "3G": ("PARTIAL", 52), "4G": ("MINIMAL", 28)},
    },
}


# -- REPORTING PERIODS ---------------------------------------------------------
# 14 periods: quarterly from Q1 2023 through Q2 2026

PERIODS = [
    date(2023, 1, 1),   # Q1 2023
    date(2023, 4, 1),   # Q2 2023
    date(2023, 7, 1),   # Q3 2023
    date(2023, 10, 1),  # Q4 2023
    date(2024, 1, 1),   # Q1 2024
    date(2024, 4, 1),   # Q2 2024
    date(2024, 7, 1),   # Q3 2024
    date(2024, 10, 1),  # Q4 2024
    date(2025, 1, 1),   # Q1 2025
    date(2025, 4, 1),   # Q2 2025
    date(2025, 7, 1),   # Q3 2025
    date(2025, 10, 1),  # Q4 2025
    date(2026, 1, 1),   # Q1 2026
    date(2026, 3, 1),   # Latest snapshot (Mar 2026)
]


def _derive_level(pct):
    """Derive CoverageLevel from a percentage value."""
    if pct >= 80:
        return CoverageLevel.FULL
    if pct >= 30:
        return CoverageLevel.PARTIAL
    if pct >= 1:
        return CoverageLevel.MINIMAL
    return CoverageLevel.NONE


def _historical_percentage(baseline_pct, periods_back):
    """
    Calculate historical coverage percentage by reducing from baseline.
    Older periods had less coverage. Each quarter back reduces by 1-4%.
    Remote districts improve slower, urban districts were already high.
    """
    if baseline_pct <= 0:
        return 0

    # Higher baseline = less room for historic reduction (already mature)
    if baseline_pct >= 90:
        reduction_per_quarter = random.uniform(0.5, 1.5)
    elif baseline_pct >= 60:
        reduction_per_quarter = random.uniform(1.0, 3.0)
    else:
        reduction_per_quarter = random.uniform(2.0, 4.0)

    historical = baseline_pct - (reduction_per_quarter * periods_back)
    # Add small random noise
    historical += random.uniform(-1.0, 1.0)
    return max(0, min(100, round(historical, 2)))


class Command(BaseCommand):
    help = "Seed Botswana districts and network coverage data (2000+ records)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing coverage data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing coverage data...")
            CoverageArea.objects.all().delete()
            District.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all coverage data."))

        # -- Ensure operators exist --------------------------------------------
        operators = {}
        for code in OPERATOR_CODES:
            op = NetworkOperator.objects.filter(code=code, is_deleted=False).first()
            if not op:
                self.stdout.write(
                    self.style.WARNING(
                        f"Operator {code} not found. Creating placeholder..."
                    )
                )
                op = NetworkOperator.objects.create(
                    name=code.title(),
                    code=code,
                    is_active=True,
                )
            operators[code] = op

        # -- Seed districts ----------------------------------------------------
        self.stdout.write("Seeding districts...")
        districts = {}
        for d in DISTRICTS:
            district, created = District.objects.update_or_create(
                code=d["code"],
                defaults={
                    "name": d["name"],
                    "region": d["region"],
                    "population": d["population"],
                    "area_sq_km": d["area_sq_km"],
                    "boundary_geojson": d["boundary_geojson"],
                    "center_lat": d["center_lat"],
                    "center_lng": d["center_lng"],
                    "is_active": True,
                    "is_deleted": False,
                },
            )
            districts[d["code"]] = district
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {district.name}")

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(districts)} districts.")
        )

        # -- Seed coverage areas -----------------------------------------------
        self.stdout.write("Seeding coverage areas...")
        coverage_records = []
        record_count = 0

        latest_period_index = len(PERIODS) - 1

        for district_code, op_data in BASELINE_COVERAGE.items():
            district = districts.get(district_code)
            if not district:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping {district_code}: district not found."
                    )
                )
                continue

            for op_code, tech_data in op_data.items():
                operator = operators.get(op_code)
                if not operator:
                    continue

                for tech, (level, baseline_pct) in tech_data.items():
                    # Generate record for each period
                    for period_idx, period in enumerate(PERIODS):
                        periods_back = latest_period_index - period_idx
                        if periods_back == 0:
                            pct = baseline_pct
                        else:
                            pct = _historical_percentage(
                                baseline_pct, periods_back
                            )

                        derived_level = _derive_level(pct)

                        # Calculate population covered
                        pop_covered = None
                        if district.population and pct > 0:
                            pop_covered = int(
                                district.population * (pct / 100.0)
                            )

                        # Signal strength: better coverage = stronger signal
                        signal = None
                        if pct > 0:
                            # dBm range: -50 (excellent) to -110 (weak)
                            base_signal = -50 - (100 - pct) * 0.6
                            signal = round(
                                base_signal + random.uniform(-3, 3), 2
                            )

                        coverage_records.append(
                            CoverageArea(
                                operator=operator,
                                district=district,
                                technology=tech,
                                coverage_level=derived_level,
                                coverage_percentage=Decimal(str(pct)),
                                population_covered=pop_covered,
                                signal_strength_avg=(
                                    Decimal(str(signal)) if signal else None
                                ),
                                period=period,
                                source=CoverageSource.BOCRA,
                                notes="",
                            )
                        )
                        record_count += 1

        # Bulk create in batches to avoid memory issues
        batch_size = 500
        created_count = 0
        for i in range(0, len(coverage_records), batch_size):
            batch = coverage_records[i : i + batch_size]
            CoverageArea.objects.bulk_create(
                batch,
                ignore_conflicts=True,
            )
            created_count += len(batch)
            self.stdout.write(
                f"  Created batch {i // batch_size + 1}: "
                f"{created_count}/{record_count} records"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete.\n"
                f"  Districts:       {len(districts)}\n"
                f"  Coverage areas:  {record_count}\n"
                f"  Periods:         {len(PERIODS)} (Q1 2023 - Mar 2026)\n"
                f"  Operators:       {len(operators)}"
            )
        )

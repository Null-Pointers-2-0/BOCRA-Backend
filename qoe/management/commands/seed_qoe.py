"""
Management command to seed QoE (Quality of Experience) reports.

Usage:
    python manage.py seed_qoe          # Create 5000 QoE reports
    python manage.py seed_qoe --clear  # Delete existing and recreate
    python manage.py seed_qoe --count 1000  # Custom count

Seeds:
    - 5,000 QoEReport records across 6 months (Oct 2025 - Mar 2026)
    - Distribution weighted by district population
    - Operator split: Mascom ~42%, Orange ~43%, BTCL ~15%
    - 60% include speed test results, 40% rating-only
    - 80% have GPS coordinates, 20% manual district selection only
    - Realistic bell-curve ratings per operator per district
"""
import hashlib
import random
from datetime import datetime, timedelta, timezone as dt_tz
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from analytics.models import NetworkOperator
from coverages.models import District
from qoe.models import ConnectionType, QoEReport, ServiceType


# -- OPERATOR PROFILES ---------------------------------------------------------
# Each operator has a quality profile that affects ratings and speeds.
# key = operator code

OPERATOR_PROFILES = {
    "MASCOM": {
        "market_share": 0.42,
        "rating_mean": 3.6,
        "rating_std": 0.9,
        "download_4g_mean": 18.0,
        "download_3g_mean": 6.5,
        "download_2g_mean": 0.8,
        "upload_factor": 0.25,  # upload ~ download * factor
        "latency_4g_mean": 35,
        "latency_3g_mean": 85,
        "latency_2g_mean": 250,
    },
    "ORANGE": {
        "market_share": 0.43,
        "rating_mean": 3.4,
        "rating_std": 1.0,
        "download_4g_mean": 15.0,
        "download_3g_mean": 5.5,
        "download_2g_mean": 0.6,
        "upload_factor": 0.22,
        "latency_4g_mean": 42,
        "latency_3g_mean": 95,
        "latency_2g_mean": 270,
    },
    "BTCL": {
        "market_share": 0.15,
        "rating_mean": 2.8,
        "rating_std": 1.1,
        "download_4g_mean": 10.0,
        "download_3g_mean": 4.0,
        "download_2g_mean": 0.5,
        "upload_factor": 0.20,
        "latency_4g_mean": 55,
        "latency_3g_mean": 110,
        "latency_2g_mean": 300,
    },
}

# District population weights -- more reports from populous districts.
# Maps district code to relative weight.
DISTRICT_WEIGHTS = {
    "SE": 40,   # Gaborone -- capital, most reports
    "NE": 12,   # Francistown
    "CE": 10,   # Central
    "KW": 10,   # Kweneng
    "SO": 7,    # Southern
    "NW": 6,    # Maun
    "KL": 5,    # Kgatleng
    "CH": 3,    # Chobe
    "GZ": 2,    # Ghanzi
    "KD": 2,    # Kgalagadi
    "SP": 3,    # Selebi-Phikwe
    "LO": 2,    # Lobatse
    "JW": 2,    # Jwaneng
    "SW": 1,    # Sowa Town
    "OR": 1,    # Orapa
    "LK": 1,    # Letlhakane
}

# Connection type distribution (varies by district urbanization)
URBAN_DISTRICTS = {"SE", "NE", "SP", "LO", "JW"}
SEMI_URBAN_DISTRICTS = {"KW", "KL", "CE", "SO", "NW", "SW", "OR", "LK"}
# Rest are rural

# Service type distribution
SERVICE_TYPE_WEIGHTS = {
    ServiceType.DATA: 55,
    ServiceType.VOICE: 25,
    ServiceType.SMS: 10,
    ServiceType.FIXED: 10,
}

# Date range: Oct 2025 - Mar 2026 (6 months)
DATE_START = datetime(2025, 10, 1, tzinfo=dt_tz.utc)
DATE_END = datetime(2026, 3, 25, tzinfo=dt_tz.utc)


def _random_rating(mean, std):
    """Generate a rating 1-5 from a normal distribution, clamped."""
    raw = random.gauss(mean, std)
    return max(1, min(5, round(raw)))


def _random_download(profile, connection_type):
    """Generate a download speed based on operator profile and connection type."""
    if connection_type == ConnectionType.FOUR_G:
        mean = profile["download_4g_mean"]
    elif connection_type == ConnectionType.THREE_G:
        mean = profile["download_3g_mean"]
    elif connection_type == ConnectionType.FIVE_G:
        mean = profile.get("download_4g_mean", 18) * 2.5
    else:
        mean = profile["download_2g_mean"]

    speed = max(0.1, random.gauss(mean, mean * 0.35))
    return round(Decimal(str(speed)), 2)


def _random_upload(download, factor):
    """Upload speed is roughly a fraction of download."""
    upload = float(download) * factor * random.uniform(0.7, 1.3)
    return round(Decimal(str(max(0.05, upload))), 2)


def _random_latency(profile, connection_type):
    """Generate latency in ms."""
    if connection_type == ConnectionType.FOUR_G:
        mean = profile["latency_4g_mean"]
    elif connection_type == ConnectionType.THREE_G:
        mean = profile["latency_3g_mean"]
    elif connection_type == ConnectionType.FIVE_G:
        mean = max(10, profile["latency_4g_mean"] * 0.5)
    else:
        mean = profile["latency_2g_mean"]

    return max(5, round(random.gauss(mean, mean * 0.3)))


def _random_connection_type(district_code):
    """Choose connection type based on district urbanization."""
    if district_code in URBAN_DISTRICTS:
        weights = [5, 15, 65, 15]  # 2G, 3G, 4G, 5G
    elif district_code in SEMI_URBAN_DISTRICTS:
        weights = [10, 30, 55, 5]
    else:
        weights = [20, 45, 30, 5]

    return random.choices(
        [ConnectionType.TWO_G, ConnectionType.THREE_G,
         ConnectionType.FOUR_G, ConnectionType.FIVE_G],
        weights=weights,
        k=1,
    )[0]


def _random_coords(district):
    """
    Generate random coordinates within district bounding box.
    Returns (lat, lng) rounded to 3 decimal places for privacy.
    """
    boundary = district.boundary_geojson
    if not boundary or not boundary.get("coordinates"):
        return None, None

    coords = boundary["coordinates"]
    ring = coords[0] if boundary["type"] == "Polygon" else coords[0][0]
    if not ring:
        return None, None

    lngs = [p[0] for p in ring]
    lats = [p[1] for p in ring]

    lat = round(random.uniform(min(lats), max(lats)), 3)
    lng = round(random.uniform(min(lngs), max(lngs)), 3)
    return Decimal(str(lat)), Decimal(str(lng))


def _random_datetime():
    """Random datetime between DATE_START and DATE_END."""
    delta = DATE_END - DATE_START
    random_seconds = random.randint(0, int(delta.total_seconds()))
    dt = DATE_START + timedelta(seconds=random_seconds)
    # Add realistic hour distribution (more reports 7am-10pm)
    hour = random.choices(
        range(24),
        weights=[1, 1, 1, 1, 1, 2, 3, 5, 6, 7, 7, 6, 6, 6, 6, 6, 7, 7, 6, 5, 4, 3, 2, 1],
        k=1,
    )[0]
    return dt.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


class Command(BaseCommand):
    help = "Seed QoE reports with realistic Botswana network experience data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing QoE reports before seeding.",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=5000,
            help="Number of QoE reports to create (default: 5000).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        clear = options["clear"]
        count = options["count"]

        if clear:
            deleted, _ = QoEReport.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing QoE reports.")

        # Load operators
        operators = {}
        for code in OPERATOR_PROFILES:
            try:
                operators[code] = NetworkOperator.objects.get(code=code)
            except NetworkOperator.DoesNotExist:
                self.stderr.write(f"WARNING: Operator {code} not found. Skipping.")
        if not operators:
            self.stderr.write("ERROR: No operators found. Run seed_analytics first.")
            return

        # Load districts
        districts = list(District.objects.filter(is_active=True, is_deleted=False))
        if not districts:
            self.stderr.write("ERROR: No districts found. Run seed_coverages first.")
            return

        district_by_code = {d.code: d for d in districts}

        # Build weighted district list
        weighted_districts = []
        for d in districts:
            weight = DISTRICT_WEIGHTS.get(d.code, 1)
            weighted_districts.extend([d] * weight)

        # Build weighted operator list
        operator_codes = list(operators.keys())
        operator_weights = [OPERATOR_PROFILES[c]["market_share"] for c in operator_codes]

        # Build weighted service type list
        service_types = list(SERVICE_TYPE_WEIGHTS.keys())
        service_weights = list(SERVICE_TYPE_WEIGHTS.values())

        self.stdout.write(f"Generating {count} QoE reports...")

        reports = []
        batch_size = 500
        fake_ips_used = set()

        for i in range(count):
            # Pick district (population-weighted)
            district = random.choice(weighted_districts)

            # Pick operator (market-share-weighted)
            op_code = random.choices(operator_codes, weights=operator_weights, k=1)[0]
            operator = operators[op_code]
            profile = OPERATOR_PROFILES[op_code]

            # Connection type (urbanization-dependent)
            conn_type = _random_connection_type(district.code)

            # Service type
            svc_type = random.choices(service_types, weights=service_weights, k=1)[0]

            # Rating (operator quality + district factor)
            # Rural districts get slightly lower ratings
            district_penalty = 0
            if district.code not in URBAN_DISTRICTS and district.code not in SEMI_URBAN_DISTRICTS:
                district_penalty = -0.3
            rating = _random_rating(
                profile["rating_mean"] + district_penalty,
                profile["rating_std"],
            )

            # Speed test (60% include it)
            has_speed = random.random() < 0.60
            download_speed = None
            upload_speed = None
            latency_ms = None
            if has_speed:
                download_speed = _random_download(profile, conn_type)
                upload_speed = _random_upload(download_speed, profile["upload_factor"])
                latency_ms = _random_latency(profile, conn_type)

            # Location (80% GPS, 20% manual district only)
            has_gps = random.random() < 0.80
            latitude = None
            longitude = None
            if has_gps:
                latitude, longitude = _random_coords(district)

            # Timestamp
            submitted_at = _random_datetime()

            # IP hash (fake, but consistent per "session")
            fake_ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
            ip_hash = hashlib.sha256(fake_ip.encode()).hexdigest()

            # Description (10% have a text description)
            description = ""
            if random.random() < 0.10:
                descriptions = [
                    "Network is very slow in my area.",
                    "Calls keep dropping.",
                    "Internet speed is acceptable but could be better.",
                    "No signal indoors, have to go outside.",
                    "Streaming works fine most of the time.",
                    "Data is expensive for the quality we get.",
                    "Coverage has improved recently.",
                    "Cannot load websites during peak hours.",
                    "Good signal but slow data speeds.",
                    "Voice quality is poor, lots of static.",
                    "Switched from another provider, much better now.",
                    "Upload speed is terrible for video calls.",
                    "Mobile banking apps timeout frequently.",
                    "Signal drops when moving between areas.",
                    "Happy with the service overall.",
                ]
                description = random.choice(descriptions)

            # Flag suspicious (1% auto-flagged)
            is_flagged = random.random() < 0.01

            report = QoEReport(
                operator=operator,
                service_type=svc_type,
                connection_type=conn_type,
                rating=rating,
                download_speed=download_speed,
                upload_speed=upload_speed,
                latency_ms=latency_ms,
                latitude=latitude,
                longitude=longitude,
                district=district,
                description=description,
                submitted_by=None,  # All seed reports are anonymous
                ip_hash=ip_hash,
                is_verified=False,
                is_flagged=is_flagged,
            )
            reports.append(report)

            if len(reports) >= batch_size:
                QoEReport.objects.bulk_create(reports)
                self.stdout.write(f"  ... created {i + 1}/{count} reports")
                reports = []

        # Final batch
        if reports:
            QoEReport.objects.bulk_create(reports)

        # Fix submitted_at timestamps (bulk_create uses auto_now_add,
        # so we update them to spread across the date range)
        self.stdout.write("Applying realistic timestamps...")
        all_reports = list(
            QoEReport.objects.order_by("created_at").values_list("id", flat=True)
        )
        batch = []
        for report_id in all_reports:
            ts = _random_datetime()
            batch.append((report_id, ts))

        # Bulk update timestamps in batches
        for start in range(0, len(batch), batch_size):
            chunk = batch[start:start + batch_size]
            ids = [r[0] for r in chunk]
            reports_to_update = QoEReport.objects.filter(id__in=ids)
            for report_id, ts in chunk:
                QoEReport.objects.filter(id=report_id).update(submitted_at=ts)

        total = QoEReport.objects.filter(is_deleted=False).count()
        with_speed = QoEReport.objects.filter(
            is_deleted=False, download_speed__isnull=False,
        ).count()
        with_gps = QoEReport.objects.filter(
            is_deleted=False, latitude__isnull=False,
        ).count()

        self.stdout.write(self.style.SUCCESS(
            f"\nQoE seed complete!\n"
            f"  Total reports:     {total}\n"
            f"  With speed test:   {with_speed} ({with_speed * 100 // max(total, 1)}%)\n"
            f"  With GPS coords:   {with_gps} ({with_gps * 100 // max(total, 1)}%)\n"
            f"  Operators:         {', '.join(operators.keys())}\n"
            f"  Districts:         {len(districts)}\n"
            f"  Date range:        {DATE_START.date()} to {DATE_END.date()}"
        ))

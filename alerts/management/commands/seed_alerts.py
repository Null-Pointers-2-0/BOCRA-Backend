"""
Seed alert subscription data.

Creates:
- 8 AlertCategory entries
- 200 AlertSubscription entries with M2M categories
- 500 AlertLog entries
"""
import random
import secrets
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from alerts.models import AlertCategory, AlertLog, AlertStatus, AlertSubscription


CATEGORIES = [
    {
        "name": "Network Outages",
        "code": "NETWORK_OUTAGE",
        "description": "Notifications about planned and unplanned network outages affecting telecom operators.",
        "icon": "wifi-off",
        "sort_order": 1,
    },
    {
        "name": "Service Quality Drops",
        "code": "QOE_DROP",
        "description": "Alerts when quality of experience scores drop below acceptable thresholds.",
        "icon": "trending-down",
        "sort_order": 2,
    },
    {
        "name": "Coverage Changes",
        "code": "COVERAGE_CHANGE",
        "description": "Updates when network coverage areas expand, shrink, or change technology type.",
        "icon": "map-pin",
        "sort_order": 3,
    },
    {
        "name": "Licensing Updates",
        "code": "LICENSE_UPDATE",
        "description": "Notifications about new licence approvals, renewals, and regulatory changes.",
        "icon": "file-text",
        "sort_order": 4,
    },
    {
        "name": "Complaint Resolutions",
        "code": "COMPLAINT_RESOLVED",
        "description": "Alerts when complaints filed with BOCRA are resolved or updated.",
        "icon": "check-circle",
        "sort_order": 5,
    },
    {
        "name": "Regulatory Announcements",
        "code": "REGULATORY",
        "description": "Official BOCRA regulatory announcements, consultations, and policy changes.",
        "icon": "megaphone",
        "sort_order": 6,
    },
    {
        "name": "Tender Notices",
        "code": "TENDER_NOTICE",
        "description": "New tender publications and procurement opportunities from BOCRA.",
        "icon": "briefcase",
        "sort_order": 7,
    },
    {
        "name": "Scorecard Updates",
        "code": "SCORECARD_UPDATE",
        "description": "Monthly operator scorecard results and ranking changes.",
        "icon": "bar-chart",
        "sort_order": 8,
    },
]

OPERATORS = ["MASCOM", "ORANGE", "BTCL"]

SUBJECT_TEMPLATES = {
    "NETWORK_OUTAGE": [
        "{op} network outage reported in {loc}",
        "Planned maintenance: {op} services in {loc}",
        "{op} connectivity restored in {loc}",
    ],
    "QOE_DROP": [
        "{op} QoE score dropped below threshold in {loc}",
        "Quality degradation detected for {op} in {loc}",
        "{op} download speeds below average in {loc}",
    ],
    "COVERAGE_CHANGE": [
        "{op} 4G coverage expanded in {loc}",
        "New {op} tower commissioned in {loc}",
        "{op} coverage area updated for {loc}",
    ],
    "LICENSE_UPDATE": [
        "{op} licence renewal approved",
        "New spectrum allocation for {op}",
        "{op} compliance status updated",
    ],
    "COMPLAINT_RESOLVED": [
        "Complaint #{num} against {op} resolved",
        "BOCRA ruling on complaint #{num}",
        "Complaint #{num} status updated to resolved",
    ],
    "REGULATORY": [
        "BOCRA issues new regulatory framework update",
        "Public consultation on telecom tariff guidelines",
        "New BOCRA directive on data protection compliance",
    ],
    "TENDER_NOTICE": [
        "New BOCRA tender: Network monitoring equipment",
        "Tender deadline extended: Infrastructure audit",
        "BOCRA procurement: QoS measurement tools",
    ],
    "SCORECARD_UPDATE": [
        "Monthly scorecard: {op} ranked #{rank}",
        "{op} scorecard score improved by {pct}%",
        "Q{q} operator rankings published",
    ],
}

LOCATIONS = [
    "Gaborone", "Francistown", "Maun", "Kasane", "Palapye",
    "Serowe", "Molepolole", "Kanye", "Lobatse", "Selebi-Phikwe",
    "Jwaneng", "Orapa", "Letlhakane", "Nata", "Ghanzi",
    "Tsabong",
]

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "bw.co", "gov.bw", "ub.ac.bw", "company.co.bw",
]

FIRST_NAMES = [
    "thabo", "mpho", "kago", "neo", "tumi", "lebo", "katlego",
    "bontle", "oratile", "phenyo", "tshepo", "kagiso", "lesedi",
    "onkabetse", "refilwe", "boitumelo", "gorata", "keabetswe",
    "motheo", "amantle",
]

LAST_NAMES = [
    "moeti", "kgosi", "molefe", "modise", "tau", "phiri", "sechele",
    "masire", "mogae", "khama", "seretse", "pilane", "molefhi",
    "magang", "motswagole", "marumo", "leburu", "rapoo", "ditlhogo",
    "molefi",
]


def _random_email():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    num = random.randint(1, 999)
    domain = random.choice(EMAIL_DOMAINS)
    return f"{first}.{last}{num}@{domain}"


def _random_subject(category_code, operator):
    templates = SUBJECT_TEMPLATES.get(category_code, ["{op} alert notification"])
    template = random.choice(templates)
    return template.format(
        op=operator,
        loc=random.choice(LOCATIONS),
        num=random.randint(1000, 9999),
        rank=random.randint(1, 3),
        pct=random.randint(1, 15),
        q=random.randint(1, 4),
    )


class Command(BaseCommand):
    help = "Seed alert categories, subscriptions, and logs"

    def handle(self, *args, **options):
        self.stdout.write("Seeding alert categories...")
        categories = []
        for cat_data in CATEGORIES:
            cat, created = AlertCategory.objects.get_or_create(
                code=cat_data["code"],
                defaults=cat_data,
            )
            categories.append(cat)
            status_msg = "created" if created else "exists"
            self.stdout.write(f"  {cat.name} ({status_msg})")

        self.stdout.write(f"\nSeeding 200 alert subscriptions...")
        subscriptions = []
        used_emails = set()

        for i in range(200):
            email = _random_email()
            while email in used_emails:
                email = _random_email()
            used_emails.add(email)

            # 80% confirmed, 20% pending
            is_confirmed = random.random() < 0.80
            # 90% active if confirmed
            is_active = is_confirmed and random.random() < 0.90
            operator_filter = random.choice(OPERATORS + [""])

            created_at = timezone.now() - timedelta(days=random.randint(1, 180))
            confirmed_at = created_at + timedelta(hours=random.randint(1, 48)) if is_confirmed else None

            sub = AlertSubscription(
                email=email,
                operator_filter=operator_filter,
                is_confirmed=is_confirmed,
                confirmed_at=confirmed_at,
                is_active=is_active,
                confirm_token=secrets.token_hex(32),
                unsubscribe_token=secrets.token_hex(32),
            )
            subscriptions.append(sub)

        AlertSubscription.objects.bulk_create(subscriptions, ignore_conflicts=True)

        # Refresh from DB to get IDs for M2M
        all_subs = list(AlertSubscription.objects.filter(is_deleted=False))
        for sub in all_subs:
            num_cats = random.randint(1, min(5, len(categories)))
            chosen = random.sample(categories, num_cats)
            sub.categories.set(chosen)

        self.stdout.write(f"  Created {len(all_subs)} subscriptions")

        self.stdout.write(f"\nSeeding 500 alert logs...")
        confirmed_subs = [s for s in all_subs if s.is_confirmed]
        if not confirmed_subs:
            confirmed_subs = all_subs[:10]

        logs = []
        for _ in range(500):
            sub = random.choice(confirmed_subs)
            cat = random.choice(categories)
            operator = sub.operator_filter or random.choice(OPERATORS)
            subject = _random_subject(cat.code, operator)

            # Status distribution: 85% SENT, 10% FAILED, 5% PENDING
            roll = random.random()
            if roll < 0.85:
                log_status = AlertStatus.SENT
            elif roll < 0.95:
                log_status = AlertStatus.FAILED
            else:
                log_status = AlertStatus.PENDING

            sent_at = None
            error_message = ""
            created_at = timezone.now() - timedelta(days=random.randint(0, 90))

            if log_status == AlertStatus.SENT:
                sent_at = created_at + timedelta(seconds=random.randint(1, 30))
            elif log_status == AlertStatus.FAILED:
                error_message = random.choice([
                    "SMTP connection timeout",
                    "Recipient mailbox full",
                    "DNS lookup failed for domain",
                    "Rate limit exceeded on email provider",
                    "Invalid recipient address",
                ])

            logs.append(AlertLog(
                subscription=sub,
                category=cat,
                subject=subject,
                body_preview=f"Alert regarding {cat.name.lower()} for {operator}.",
                related_object_type=cat.code.lower(),
                status=log_status,
                sent_at=sent_at,
                error_message=error_message,
            ))

        AlertLog.objects.bulk_create(logs)
        self.stdout.write(f"  Created {len(logs)} alert logs")

        self.stdout.write(self.style.SUCCESS(
            "\nDone! Seeded 8 categories, 200 subscriptions, 500 logs."
        ))

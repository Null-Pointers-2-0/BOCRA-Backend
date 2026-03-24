"""
Management command to seed BOCRA tenders data.

Usage:
    python manage.py seed_tenders          # Create tenders
    python manage.py seed_tenders --clear  # Delete existing and recreate
"""
import random
from datetime import timedelta, date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserRole
from tenders.models import (
    Tender,
    TenderAddendum,
    TenderAward,
    TenderCategory,
    TenderDocument,
    TenderStatus,
)


# ─── SEED DATA ────────────────────────────────────────────────────────────────

TENDERS = [
    # ── IT SERVICES ───────────────────────────────────────────────────────────
    {
        "title": "Supply and Implementation of Spectrum Monitoring System",
        "reference_number": "BOCRA/TENDER/2026/001",
        "category": TenderCategory.IT_SERVICES,
        "description": (
            "BOCRA invites sealed bids from qualified suppliers for the supply, "
            "installation, and commissioning of an automated radio frequency "
            "spectrum monitoring system. The system shall cover the frequency range "
            "9 kHz to 6 GHz and include fixed monitoring stations in Gaborone, "
            "Francistown, and Maun, as well as a mobile monitoring unit.\n\n"
            "Scope of Work:\n"
            "1. Supply of spectrum monitoring receivers and antennas\n"
            "2. Installation at three fixed locations\n"
            "3. Configuration of mobile monitoring vehicle\n"
            "4. Integration with existing BOCRA spectrum management database\n"
            "5. Training of BOCRA technical staff (minimum 10 personnel)\n"
            "6. 3-year maintenance and support contract\n\n"
            "The system must comply with ITU-R recommendations for spectrum monitoring "
            "and meet international standards for measurement accuracy."
        ),
        "status": TenderStatus.OPEN,
        "budget_range": "BWP 8,000,000 – 15,000,000",
        "contact_name": "Thabo Mosimanyana",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 45,
        "days_until_close": 30,
        "addenda": [
            {
                "title": "Clarification on Technical Specifications",
                "content": (
                    "In response to bidder queries, BOCRA clarifies that the spectrum "
                    "monitoring receivers must support both amplitude and phase measurements. "
                    "The minimum sensitivity requirement is -165 dBm/Hz. Bidders should "
                    "include spectrum of all proposed equipment in their technical submissions."
                ),
            },
        ],
        "documents": [
            "Request for Proposal (RFP) Document",
            "Technical Specifications",
            "Terms of Reference",
            "Evaluation Criteria",
        ],
    },
    {
        "title": "Development of BOCRA Online Licensing Portal",
        "reference_number": "BOCRA/TENDER/2026/002",
        "category": TenderCategory.IT_SERVICES,
        "description": (
            "BOCRA seeks proposals from experienced software development firms for "
            "the design, development, and deployment of a comprehensive online "
            "licensing portal. The portal will enable operators to apply for, renew, "
            "and manage their telecommunications, broadcasting, and postal licences "
            "electronically.\n\n"
            "Key Requirements:\n"
            "1. User registration and authentication system\n"
            "2. Online licence application with document upload\n"
            "3. Application status tracking and notifications\n"
            "4. Online payment gateway integration\n"
            "5. Admin dashboard for BOCRA staff\n"
            "6. Reporting and analytics module\n"
            "7. Mobile-responsive design\n"
            "8. Integration with existing BOCRA systems"
        ),
        "status": TenderStatus.OPEN,
        "budget_range": "BWP 3,000,000 – 6,000,000",
        "contact_name": "Kelebogile Ramotswa",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 30,
        "days_until_close": 15,
        "addenda": [],
        "documents": [
            "Request for Proposal (RFP) Document",
            "System Requirements Specification",
            "Terms of Reference",
        ],
    },
    {
        "title": "Provision of Managed IT Infrastructure Services",
        "reference_number": "BOCRA/TENDER/2026/003",
        "category": TenderCategory.IT_SERVICES,
        "description": (
            "BOCRA invites proposals for the provision of managed IT infrastructure "
            "services including server hosting, network management, cybersecurity "
            "monitoring, and disaster recovery solutions.\n\n"
            "The contract period is 3 years with an option to extend for an "
            "additional 2 years subject to satisfactory performance."
        ),
        "status": TenderStatus.CLOSING_SOON,
        "budget_range": "BWP 2,000,000 – 4,000,000",
        "contact_name": "David Ntshekisang",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 55,
        "days_until_close": 3,
        "addenda": [
            {
                "title": "Extension of Closing Date",
                "content": (
                    "The closing date for this tender has been extended by 7 days to "
                    "allow bidders additional time to prepare comprehensive proposals. "
                    "The new closing date is reflected in the updated tender notice."
                ),
            },
            {
                "title": "Addendum 2: Pre-Bid Meeting Minutes",
                "content": (
                    "Minutes of the pre-bid meeting held on 15 February 2026 are now "
                    "available. Key points discussed include: minimum uptime SLA of 99.9%, "
                    "data sovereignty requirements (all data must be hosted in SADC region), "
                    "and ISO 27001 certification requirement for the service provider."
                ),
            },
        ],
        "documents": [
            "Request for Proposal (RFP) Document",
            "Service Level Agreement Template",
            "Technical Requirements",
            "Pre-Bid Meeting Minutes",
        ],
    },

    # ── CONSULTING ────────────────────────────────────────────────────────────
    {
        "title": "Consultancy: Telecommunications Market Study 2026",
        "reference_number": "BOCRA/TENDER/2026/004",
        "category": TenderCategory.CONSULTING,
        "description": (
            "BOCRA seeks the services of a qualified consulting firm to conduct "
            "a comprehensive study of the Botswana telecommunications market. The "
            "study shall cover market structure, competition dynamics, pricing "
            "analysis, quality of service evaluation, and international benchmarking.\n\n"
            "Deliverables:\n"
            "1. Inception report\n"
            "2. Data collection and survey instruments\n"
            "3. Draft market study report\n"
            "4. Final market study report\n"
            "5. Executive summary and policy recommendations\n"
            "6. Presentation to BOCRA Board"
        ),
        "status": TenderStatus.OPEN,
        "budget_range": "BWP 1,500,000 – 3,000,000",
        "contact_name": "Thabo Mosimanyana",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 20,
        "days_until_close": 25,
        "addenda": [],
        "documents": [
            "Terms of Reference",
            "Expression of Interest Form",
            "Evaluation Criteria",
        ],
    },
    {
        "title": "Consultancy: Review of Universal Access and Service Fund",
        "reference_number": "BOCRA/TENDER/2026/005",
        "category": TenderCategory.CONSULTING,
        "description": (
            "BOCRA invites proposals from qualified consultants to review the "
            "effectiveness of the Universal Access and Service Fund (UASF) in "
            "achieving its mandate of extending ICT services to underserved areas "
            "of Botswana.\n\n"
            "The review should cover:\n"
            "1. Assessment of UASF fund utilisation over the past 5 years\n"
            "2. Impact evaluation of funded projects\n"
            "3. Benchmarking against similar funds in SADC region\n"
            "4. Recommendations for improved fund management\n"
            "5. Proposed project prioritisation framework"
        ),
        "status": TenderStatus.CLOSED,
        "budget_range": "BWP 800,000 – 1,500,000",
        "contact_name": "Kelebogile Ramotswa",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 40,
        "days_until_close": -10,
        "addenda": [],
        "documents": [
            "Terms of Reference",
            "Expression of Interest Form",
        ],
    },

    # ── EQUIPMENT ─────────────────────────────────────────────────────────────
    {
        "title": "Supply of Network Testing and Measurement Equipment",
        "reference_number": "BOCRA/TENDER/2026/006",
        "category": TenderCategory.EQUIPMENT,
        "description": (
            "BOCRA invites sealed bids for the supply and delivery of network "
            "testing and measurement equipment for use in quality of service "
            "monitoring and compliance verification.\n\n"
            "Equipment Required:\n"
            "1. Drive test kits for mobile network QoS measurement (5 units)\n"
            "2. Broadband speed testing devices (10 units)\n"
            "3. Signal strength measurement tools (8 units)\n"
            "4. Network protocol analysers (3 units)\n"
            "5. Supporting software licences and training"
        ),
        "status": TenderStatus.AWARDED,
        "budget_range": "BWP 2,500,000 – 4,000,000",
        "contact_name": "David Ntshekisang",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 60,
        "days_until_close": -30,
        "award": {
            "awardee_name": "TelcoTest Botswana Pty Ltd",
            "award_amount": Decimal("3250000.00"),
            "summary": (
                "After evaluation of 7 compliant bids, TelcoTest Botswana Pty Ltd "
                "was awarded the tender based on best value for money, technical "
                "compliance, and demonstrated after-sales support capability. "
                "Delivery is expected within 90 days of contract signing."
            ),
        },
        "addenda": [],
        "documents": [
            "Invitation to Bid",
            "Technical Specifications",
            "Bid Evaluation Criteria",
        ],
    },
    {
        "title": "Supply of Broadcasting Signal Monitoring Equipment",
        "reference_number": "BOCRA/TENDER/2026/007",
        "category": TenderCategory.EQUIPMENT,
        "description": (
            "BOCRA requires broadcasting signal monitoring equipment for continuous "
            "monitoring of radio and television broadcast signals in Botswana.\n\n"
            "The equipment shall include:\n"
            "1. FM/AM broadcast signal analysers (4 units)\n"
            "2. DVB-T2 digital television signal monitoring receivers (4 units)\n"
            "3. Remote monitoring probes for deployment in regional centres\n"
            "4. Centralised monitoring software with alerting capability"
        ),
        "status": TenderStatus.CLOSED,
        "budget_range": "BWP 1,200,000 – 2,000,000",
        "contact_name": "Thabo Mosimanyana",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 45,
        "days_until_close": -15,
        "addenda": [],
        "documents": [
            "Invitation to Bid",
            "Technical Specifications",
        ],
    },

    # ── PROFESSIONAL SERVICES ─────────────────────────────────────────────────
    {
        "title": "External Audit Services for Financial Year 2025/2026",
        "reference_number": "BOCRA/TENDER/2026/008",
        "category": TenderCategory.PROFESSIONAL,
        "description": (
            "BOCRA invites proposals from registered audit firms for the provision "
            "of external audit services for the financial year ending 31 March 2026.\n\n"
            "Scope:\n"
            "1. Statutory audit of BOCRA financial statements\n"
            "2. Audit of Universal Access and Service Fund\n"
            "3. Management letter and recommendations\n"
            "4. Presentation of findings to the BOCRA Audit Committee"
        ),
        "status": TenderStatus.AWARDED,
        "budget_range": "BWP 400,000 – 800,000",
        "contact_name": "Kelebogile Ramotswa",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 30,
        "days_until_close": -45,
        "award": {
            "awardee_name": "Deloitte & Touche Botswana",
            "award_amount": Decimal("620000.00"),
            "summary": (
                "Deloitte & Touche Botswana was the successful bidder, demonstrating "
                "extensive experience in public sector auditing and regulatory bodies. "
                "The firm has previously audited similar entities in the SADC region."
            ),
        },
        "addenda": [],
        "documents": [
            "Request for Proposal (RFP) Document",
            "Terms of Reference",
        ],
    },
    {
        "title": "Legal Advisory Services for Regulatory Matters",
        "reference_number": "BOCRA/TENDER/2026/009",
        "category": TenderCategory.PROFESSIONAL,
        "description": (
            "BOCRA seeks expressions of interest from law firms to provide legal "
            "advisory services on telecommunications regulatory matters, including "
            "licence enforcement, dispute resolution, and legislative drafting.\n\n"
            "The appointment will be on a retainer basis for a period of 2 years."
        ),
        "status": TenderStatus.OPEN,
        "budget_range": "BWP 500,000 – 1,000,000 per annum",
        "contact_name": "Thabo Mosimanyana",
        "contact_email": "legal@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 15,
        "days_until_close": 20,
        "addenda": [],
        "documents": [
            "Expression of Interest Document",
            "Terms of Reference",
            "Evaluation Criteria",
        ],
    },

    # ── CONSTRUCTION ──────────────────────────────────────────────────────────
    {
        "title": "Construction of Regional Office in Francistown",
        "reference_number": "BOCRA/TENDER/2026/010",
        "category": TenderCategory.CONSTRUCTION,
        "description": (
            "BOCRA invites bids from registered contractors for the construction "
            "of a regional office building in Francistown. The building shall "
            "accommodate approximately 30 staff members and include:\n\n"
            "1. Office spaces (open plan and individual offices)\n"
            "2. Conference room (40-person capacity)\n"
            "3. ICT server room and network infrastructure\n"
            "4. Customer service area\n"
            "5. Parking for 25 vehicles\n"
            "6. Solar power backup system\n\n"
            "The building must comply with Botswana Building Regulations and "
            "achieve a minimum green building rating."
        ),
        "status": TenderStatus.DRAFT,
        "budget_range": "BWP 15,000,000 – 25,000,000",
        "contact_name": "David Ntshekisang",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 0,
        "days_until_close": 60,
        "addenda": [],
        "documents": [
            "Architectural Drawings",
            "Bill of Quantities",
            "Construction Specifications",
        ],
    },

    # ── MAINTENANCE ───────────────────────────────────────────────────────────
    {
        "title": "Annual Maintenance of BOCRA Head Office Building",
        "reference_number": "BOCRA/TENDER/2026/011",
        "category": TenderCategory.MAINTENANCE,
        "description": (
            "BOCRA invites bids for the provision of annual building maintenance "
            "services at the BOCRA Head Office in Gaborone.\n\n"
            "Services Required:\n"
            "1. HVAC system maintenance and servicing\n"
            "2. Electrical systems maintenance\n"
            "3. Plumbing maintenance\n"
            "4. Elevator maintenance and certification\n"
            "5. Fire detection and suppression system maintenance\n"
            "6. General building repairs and upkeep"
        ),
        "status": TenderStatus.CLOSED,
        "budget_range": "BWP 300,000 – 500,000 per annum",
        "contact_name": "Kelebogile Ramotswa",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 30,
        "days_until_close": -20,
        "addenda": [],
        "documents": [
            "Invitation to Bid",
            "Scope of Work",
        ],
    },

    # ── CANCELLED ─────────────────────────────────────────────────────────────
    {
        "title": "Supply of Office Furniture and Equipment",
        "reference_number": "BOCRA/TENDER/2026/012",
        "category": TenderCategory.OTHER,
        "description": (
            "BOCRA invited bids for the supply and delivery of office furniture "
            "and equipment for the newly renovated second floor.\n\n"
            "This tender has been cancelled due to a change in project scope. "
            "A revised tender will be issued in due course."
        ),
        "status": TenderStatus.CANCELLED,
        "budget_range": "BWP 800,000 – 1,200,000",
        "contact_name": "David Ntshekisang",
        "contact_email": "procurement@bocra.org.bw",
        "contact_phone": "+26736 00 400",
        "days_open": 25,
        "days_until_close": -5,
        "addenda": [],
        "documents": [
            "Cancellation Notice",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed BOCRA tenders with realistic procurement data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing tender data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing tender data...")
            TenderAward.objects.all().delete()
            TenderAddendum.objects.all().delete()
            TenderDocument.objects.all().delete()
            Tender.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Cleared."))

        # Get a staff/admin user
        staff_user = User.objects.filter(
            role__in=[UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN],
            is_active=True,
        ).first()

        now = timezone.now()
        tender_count = 0
        award_count = 0

        self.stdout.write("\nSeeding tenders...")

        for data in TENDERS:
            # Skip if tender with same reference already exists
            if Tender.objects.filter(reference_number=data["reference_number"]).exists():
                self.stdout.write(f"  Skipped (exists): {data['reference_number']}")
                continue

            days_open = data["days_open"]
            days_until_close = data["days_until_close"]

            opening_date = now - timedelta(days=days_open) if days_open > 0 else None
            closing_date = now + timedelta(days=days_until_close)

            tender = Tender(
                title=data["title"],
                reference_number=data["reference_number"],
                description=data["description"],
                category=data["category"],
                status=data["status"],
                opening_date=opening_date,
                closing_date=closing_date,
                budget_range=data["budget_range"],
                contact_name=data["contact_name"],
                contact_email=data["contact_email"],
                contact_phone=data["contact_phone"],
                created_by=staff_user,
            )
            tender.save()

            # Backdate created_at
            if opening_date:
                Tender.objects.filter(pk=tender.pk).update(
                    created_at=opening_date - timedelta(days=random.randint(1, 7))
                )

            # Note: TenderDocument requires actual files, so we skip seeding
            # document records. Titles are listed in the tender data for reference.

            # Create addenda
            for addendum_data in data.get("addenda", []):
                TenderAddendum.objects.create(
                    tender=tender,
                    title=addendum_data["title"],
                    content=addendum_data["content"],
                    author=staff_user,
                )

            # Create award if applicable
            award_data = data.get("award")
            if award_data and data["status"] == TenderStatus.AWARDED:
                award_date = (closing_date + timedelta(days=random.randint(14, 45))).date()
                TenderAward.objects.create(
                    tender=tender,
                    awardee_name=award_data["awardee_name"],
                    award_date=award_date,
                    award_amount=award_data["award_amount"],
                    summary=award_data["summary"],
                    awarded_by=staff_user,
                )
                award_count += 1

            status_label = data["status"]
            self.stdout.write(
                f"  Created {status_label}: {data['reference_number']} — "
                f"{data['title'][:50]}"
            )
            tender_count += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Tender seeding complete!"))
        self.stdout.write(f"  Total tenders:   {Tender.objects.count()}")
        self.stdout.write(f"  Documents:       {TenderDocument.objects.count()}")
        self.stdout.write(f"  Addenda:         {TenderAddendum.objects.count()}")
        self.stdout.write(f"  Awards:          {TenderAward.objects.count()}")
        counts = {}
        for stat_val, stat_label in TenderStatus.choices:
            c = Tender.objects.filter(status=stat_val).count()
            if c:
                counts[stat_label] = c
        for label, c in counts.items():
            self.stdout.write(f"    {label}: {c}")
        self.stdout.write(self.style.SUCCESS("=" * 50))

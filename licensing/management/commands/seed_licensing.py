"""
Management command to seed all BOCRA licence sectors, types, and sample applications.

Usage:
    python manage.py seed_licensing          # Create sectors + types
    python manage.py seed_licensing --clear  # Delete existing and recreate
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserRole
from licensing.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusLog,
    Licence,
    LicenceSector,
    LicenceStatus,
    LicenceType,
)
from licensing.utils import generate_licence_number, generate_licence_reference


# ─── SEED DATA ────────────────────────────────────────────────────────────────

SECTORS = [
    {
        "name": "Information & Communications Technology (ICT)",
        "code": "ICT",
        "description": (
            "Licences governing telecommunications, internet services, "
            "and network infrastructure within Botswana."
        ),
        "icon": "radio-tower",
        "sort_order": 1,
    },
    {
        "name": "Postal Services",
        "code": "POSTAL",
        "description": (
            "Licences for postal operators including designated public "
            "postal operators and commercial courier services."
        ),
        "icon": "mail",
        "sort_order": 2,
    },
    {
        "name": "Broadcasting",
        "code": "BROADCASTING",
        "description": (
            "Licences for radio stations, television stations, and "
            "subscription management services in Botswana."
        ),
        "icon": "tv",
        "sort_order": 3,
    },
    {
        "name": "General / Other",
        "code": "GENERAL",
        "description": (
            "Other regulatory licences issued by BOCRA including radio "
            "dealer and value-added network services licences."
        ),
        "icon": "shield",
        "sort_order": 4,
    },
]


LICENCE_TYPES = [
    # ── ICT Sector ────────────────────────────────────────────────────────────
    {
        "name": "Services & Applications Provider Licence (SAP)",
        "code": "SAP",
        "sector_code": "ICT",
        "description": (
            "Authorises operators to offer internet services using "
            "third-party infrastructure. This includes ISPs, VoIP providers, "
            "cloud service providers, and value-added service operators."
        ),
        "requirements": (
            "1. Certified copy of certificate of incorporation\n"
            "2. Complete ownership profile listing all shareholders\n"
            "3. 3-year business plan with financial projections\n"
            "4. Technical network description and configuration\n"
            "5. CVs of key technical and managerial personnel\n"
            "6. Proof of funding"
        ),
        "eligibility_criteria": (
            "Must be a registered company in Botswana with a registered office. "
            "Applicant must demonstrate technical capability and financial capacity "
            "to provide the proposed services."
        ),
        "required_documents": [
            {"name": "Certificate of Incorporation (certified copy)", "required": True},
            {"name": "Shareholders Register (Form 2C/2D)", "required": True},
            {"name": "Directors Register (Form 2A/2B)", "required": True},
            {"name": "3-Year Business Plan", "required": True},
            {"name": "Network Diagram / Technical Description", "required": True},
            {"name": "CVs of Technical Staff", "required": True},
            {"name": "Proof of Funding", "required": True},
            {"name": "Tax Clearance Certificate", "required": False},
        ],
        "fee_amount": 10000,
        "annual_fee": 5000,
        "renewal_fee": 8000,
        "validity_period_months": 180,  # 15 years
        "is_domain_applicable": True,
        "sort_order": 1,
    },
    {
        "name": "Network Facilities Provider Licence (NFP)",
        "code": "NFP",
        "sector_code": "ICT",
        "description": (
            "Authorises operators to establish and operate infrastructure "
            "necessary for the provision of internet and telecommunication "
            "services. This includes backbone network operators, tower companies, "
            "and fibre optic infrastructure providers."
        ),
        "requirements": (
            "1. Certified copy of certificate of incorporation\n"
            "2. Complete ownership profile listing all shareholders\n"
            "3. Detailed network architecture and infrastructure plan\n"
            "4. 3-year business plan with financial projections\n"
            "5. Environmental impact assessment (where applicable)\n"
            "6. Proof of funding and technical capability"
        ),
        "eligibility_criteria": (
            "Must be a registered company in Botswana. Applicant must demonstrate "
            "significant technical expertise and financial resources necessary to build "
            "and maintain telecommunications infrastructure."
        ),
        "required_documents": [
            {"name": "Certificate of Incorporation (certified copy)", "required": True},
            {"name": "Shareholders Register (Form 2C/2D)", "required": True},
            {"name": "Directors Register (Form 2A/2B)", "required": True},
            {"name": "3-Year Business Plan", "required": True},
            {"name": "Network Architecture Plan", "required": True},
            {"name": "Environmental Impact Assessment", "required": False},
            {"name": "Proof of Funding", "required": True},
            {"name": "Technical Staff CVs", "required": True},
        ],
        "fee_amount": 25000,
        "annual_fee": 10000,
        "renewal_fee": 20000,
        "validity_period_months": 180,  # 15 years
        "is_domain_applicable": True,
        "sort_order": 2,
    },
    {
        "name": "Radio/Spectrum Licence",
        "code": "RSL",
        "sector_code": "ICT",
        "description": (
            "A licence issued to a service provider to use a specific set of radio "
            "frequencies for a defined period in a specific geographic location. "
            "Required for wireless communication systems, microwave links, and "
            "satellite communications."
        ),
        "requirements": (
            "1. Completed spectrum application form\n"
            "2. Technical specifications of radio equipment\n"
            "3. Frequency coordination analysis\n"
            "4. Site information and coverage maps\n"
            "5. Equipment type approval certificates"
        ),
        "eligibility_criteria": (
            "Open to any registered entity requiring radio spectrum. "
            "Spectrum fees are based on requirements and considered case-by-case."
        ),
        "required_documents": [
            {"name": "Spectrum Application Form", "required": True},
            {"name": "Equipment Technical Specifications", "required": True},
            {"name": "Frequency Coordination Analysis", "required": True},
            {"name": "Site Information & Coverage Maps", "required": True},
            {"name": "Equipment Type Approval Certificate", "required": True},
        ],
        "fee_amount": 5000,
        "annual_fee": 3000,
        "renewal_fee": 4000,
        "validity_period_months": 60,  # 5 years
        "is_domain_applicable": False,
        "sort_order": 3,
    },

    # ── Postal Sector ─────────────────────────────────────────────────────────
    {
        "name": "Designated Public Postal Operator (DPPO)",
        "code": "DPPO",
        "sector_code": "POSTAL",
        "description": (
            "Appointed by the Minister, with a statutory obligation to provide "
            "universal postal services to all citizens and residents of Botswana, "
            "regardless of geographical location or commercial viability."
        ),
        "requirements": (
            "1. Ministerial appointment letter\n"
            "2. Universal service obligation compliance plan\n"
            "3. Network coverage plan (nationwide)\n"
            "4. Quality of service standards commitment\n"
            "5. Financial sustainability plan"
        ),
        "eligibility_criteria": (
            "Must be appointed by the Minister responsible for communications. "
            "Only one DPPO is designated at any time. Must demonstrate ability to "
            "provide universal postal service across Botswana."
        ),
        "required_documents": [
            {"name": "Ministerial Appointment Letter", "required": True},
            {"name": "Universal Service Plan", "required": True},
            {"name": "Network Coverage Plan", "required": True},
            {"name": "Financial Sustainability Plan", "required": True},
        ],
        "fee_amount": 0,
        "annual_fee": 0,
        "renewal_fee": 0,
        "validity_period_months": 240,  # 20 years
        "is_domain_applicable": False,
        "sort_order": 1,
    },
    {
        "name": "Commercial Postal Operator (CPO)",
        "code": "CPO",
        "sector_code": "POSTAL",
        "description": (
            "Licensed to provide postal and courier services on a commercial basis, "
            "including value-added services such as express delivery, parcel tracking, "
            "and international courier operations."
        ),
        "requirements": (
            "1. Certified copy of certificate of incorporation\n"
            "2. Complete ownership profile\n"
            "3. Business plan with service coverage areas\n"
            "4. Vehicle fleet and logistics capability\n"
            "5. Customer service and complaints handling procedures"
        ),
        "eligibility_criteria": (
            "Must be a registered company in Botswana with demonstrated capability "
            "to provide postal or courier services commercially."
        ),
        "required_documents": [
            {"name": "Certificate of Incorporation (certified copy)", "required": True},
            {"name": "Shareholders Register", "required": True},
            {"name": "Business Plan", "required": True},
            {"name": "Fleet & Logistics Plan", "required": True},
            {"name": "Customer Service Procedures", "required": False},
        ],
        "fee_amount": 5000,
        "annual_fee": 2000,
        "renewal_fee": 4000,
        "validity_period_months": 120,  # 10 years
        "is_domain_applicable": False,
        "sort_order": 2,
    },

    # ── Broadcasting Sector ───────────────────────────────────────────────────
    {
        "name": "Commercial Radio Station Licence",
        "code": "CRS",
        "sector_code": "BROADCASTING",
        "description": (
            "Licence for operating a commercial radio broadcasting station in "
            "Botswana. Covers FM, AM, and digital radio broadcasting for commercial "
            "purposes including advertising revenue."
        ),
        "requirements": (
            "1. Broadcasting content plan and programming schedule\n"
            "2. Technical transmission specifications\n"
            "3. Frequency allocation request\n"
            "4. Studio and transmission site details\n"
            "5. 3-year financial projections\n"
            "6. Local content compliance plan"
        ),
        "eligibility_criteria": (
            "Must be a registered company in Botswana. Must comply with local "
            "content requirements and BOCRA broadcasting regulations."
        ),
        "required_documents": [
            {"name": "Certificate of Incorporation (certified copy)", "required": True},
            {"name": "Broadcasting Content Plan", "required": True},
            {"name": "Technical Transmission Specifications", "required": True},
            {"name": "Studio & Site Details", "required": True},
            {"name": "3-Year Financial Projections", "required": True},
            {"name": "Local Content Compliance Plan", "required": True},
        ],
        "fee_amount": 15000,
        "annual_fee": 8000,
        "renewal_fee": 12000,
        "validity_period_months": 120,  # 10 years
        "is_domain_applicable": False,
        "sort_order": 1,
    },
    {
        "name": "Commercial Television Station Licence",
        "code": "CTS",
        "sector_code": "BROADCASTING",
        "description": (
            "Licence for operating a commercial television broadcasting station. "
            "Covers terrestrial, satellite, and digital TV broadcasting for "
            "commercial purposes."
        ),
        "requirements": (
            "1. Broadcasting content plan and programming schedule\n"
            "2. Technical transmission specifications (including DTT)\n"
            "3. Studio and transmission infrastructure plan\n"
            "4. 3-year financial and business plan\n"
            "5. Local content compliance plan\n"
            "6. Advertising and commercial arrangements"
        ),
        "eligibility_criteria": (
            "Must be a registered company in Botswana with significant capital for "
            "TV infrastructure. Must comply with BOCRA broadcasting content regulations."
        ),
        "required_documents": [
            {"name": "Certificate of Incorporation (certified copy)", "required": True},
            {"name": "Broadcasting Content Plan", "required": True},
            {"name": "Transmission Infrastructure Plan", "required": True},
            {"name": "3-Year Business Plan", "required": True},
            {"name": "Local Content Compliance Plan", "required": True},
            {"name": "Proof of Funding", "required": True},
        ],
        "fee_amount": 25000,
        "annual_fee": 15000,
        "renewal_fee": 20000,
        "validity_period_months": 120,  # 10 years
        "is_domain_applicable": False,
        "sort_order": 2,
    },
    {
        "name": "Non-Commercial Radio Station Licence",
        "code": "NCRS",
        "sector_code": "BROADCASTING",
        "description": (
            "Licence for operating a non-commercial radio station such as community "
            "radio, educational radio, or religious broadcasting. Not permitted to "
            "generate advertising revenue."
        ),
        "requirements": (
            "1. Community or institutional mandate documentation\n"
            "2. Broadcasting content plan\n"
            "3. Technical specifications\n"
            "4. Governance structure and editorial policy\n"
            "5. Funding sources (no commercial advertising)"
        ),
        "eligibility_criteria": (
            "Open to community organisations, educational institutions, religious "
            "bodies, and NGOs. Must not engage in commercial broadcasting activities."
        ),
        "required_documents": [
            {"name": "Organisational Constitution / Charter", "required": True},
            {"name": "Broadcasting Content Plan", "required": True},
            {"name": "Technical Specifications", "required": True},
            {"name": "Governance & Editorial Policy", "required": True},
            {"name": "Funding Sources Declaration", "required": True},
        ],
        "fee_amount": 2000,
        "annual_fee": 1000,
        "renewal_fee": 1500,
        "validity_period_months": 60,  # 5 years
        "is_domain_applicable": False,
        "sort_order": 3,
    },
    {
        "name": "Subscription Management Services Licence",
        "code": "SMS",
        "sector_code": "BROADCASTING",
        "description": (
            "Licence for providing subscription-based content management services. "
            "Covers pay-TV operators, streaming content aggregators, and conditional "
            "access system operators."
        ),
        "requirements": (
            "1. Service description and content catalogue\n"
            "2. Technical platform infrastructure plan\n"
            "3. Content acquisition and licensing agreements\n"
            "4. Subscriber management system details\n"
            "5. 3-year business plan"
        ),
        "eligibility_criteria": (
            "Must be a registered company in Botswana with content distribution "
            "capabilities and subscriber management systems."
        ),
        "required_documents": [
            {"name": "Certificate of Incorporation (certified copy)", "required": True},
            {"name": "Service & Content Description", "required": True},
            {"name": "Platform Infrastructure Plan", "required": True},
            {"name": "Content Licensing Agreements", "required": True},
            {"name": "3-Year Business Plan", "required": True},
        ],
        "fee_amount": 20000,
        "annual_fee": 10000,
        "renewal_fee": 15000,
        "validity_period_months": 120,  # 10 years
        "is_domain_applicable": False,
        "sort_order": 4,
    },

    # ── General / Other ───────────────────────────────────────────────────────
    {
        "name": "Radio Dealer's Licence",
        "code": "RDL",
        "sector_code": "GENERAL",
        "description": (
            "Licence to trade in, install, and maintain radio communication equipment. "
            "Required for businesses dealing in two-way radios, radio transceivers, "
            "and similar radio communication apparatus."
        ),
        "requirements": (
            "OWNERSHIP INFORMATION:\n"
            "1. Complete ownership profile listing all directors and equity holding in Pula\n"
            "2. Group membership details with ownership from ultimate parent to applicant\n"
            "3. Nature of juristic person (private/public company, close corporation, trust, partnership)\n\n"
            "TECHNICAL INFORMATION:\n"
            "1. Detailed technical experience and capability assessment\n"
            "2. List of all test instruments for installation and maintenance\n"
            "3. Profile of technical staff\n\n"
            "FINANCIAL INFORMATION:\n"
            "1. Capacity and resources available to trade on radio equipment\n"
            "2. Written proof may be requested for any disclosed particulars"
        ),
        "eligibility_criteria": (
            "Must be a registered juristic person (company, close corporation, trust, or partnership). "
            "Must demonstrate sufficient technical experience and capability to deal in radio equipment."
        ),
        "required_documents": [
            {"name": "Company Registration Documents", "required": True},
            {"name": "Ownership Profile (directors & equity)", "required": True},
            {"name": "Group Structure Documentation (if applicable)", "required": False},
            {"name": "Technical Experience Statement", "required": True},
            {"name": "Test Instruments Inventory", "required": True},
            {"name": "Technical Staff Profiles", "required": True},
            {"name": "Financial Capacity Statement", "required": True},
        ],
        "fee_amount": 3000,
        "annual_fee": 1500,
        "renewal_fee": 2500,
        "validity_period_months": 60,  # 5 years
        "is_domain_applicable": False,
        "sort_order": 1,
    },
    {
        "name": "Value Added Network Services Licence (VANS)",
        "code": "VANS",
        "sector_code": "GENERAL",
        "description": (
            "Licence for providing value-added network services such as data "
            "processing, email hosting, web hosting, e-commerce platforms, and "
            "other enhanced network services built on top of basic telecommunications "
            "infrastructure."
        ),
        "requirements": (
            "CORPORATE INFORMATION:\n"
            "1. Certified copy of certificate of incorporation or registration\n"
            "2. Complete ownership profile with nationalities, addresses, and shareholding\n"
            "3. Directorship disclosure (Form 2A, 2B, 2E if close company)\n"
            "4. Group membership details if applicable\n"
            "5. Nature of company disclosure (private/public per Companies Act)\n"
            "6. Registered office in Botswana (certified Form 2)\n"
            "7. Contact details of registered office\n\n"
            "BUSINESS PLAN (3 years):\n"
            "1. Market differentiation statement\n"
            "2. Services description and market benefit\n"
            "3. After-sales support structures\n"
            "4. Target market analysis\n"
            "5. Service pricing\n"
            "6. 3-year Cash Flows and Income Statement projections\n"
            "7. Date of commencement commitment\n"
            "8. Proof of funding\n\n"
            "TECHNICAL INFORMATION:\n"
            "1. Network diagram/configuration\n"
            "2. Description of all network interfaces\n"
            "3. Major equipment and core network components\n"
            "4. Resource requirements from BOCRA (numbers, spectrum, etc.)\n"
            "5. CVs of technical and managerial personnel\n"
            "6. Job creation and skills transfer plan"
        ),
        "eligibility_criteria": (
            "Must be a company registered under the Companies Act with a registered "
            "office in Botswana. Must demonstrate technical capability, financial "
            "capacity, and a viable 3-year business plan."
        ),
        "required_documents": [
            {"name": "Certificate of Incorporation/Registration (certified)", "required": True},
            {"name": "Shareholders Register with certified shareholding certificates", "required": True},
            {"name": "Directors Register (Form 2A/2B, Form 2E if close company)", "required": True},
            {"name": "Registered Office Details (certified Form 2)", "required": True},
            {"name": "3-Year Business Plan", "required": True},
            {"name": "3-Year Financial Projections (Cash Flows & Income Statement)", "required": True},
            {"name": "Network Diagram & Technical Description", "required": True},
            {"name": "Equipment & Core Network Description", "required": True},
            {"name": "CVs of Technical & Managerial Staff", "required": True},
            {"name": "Proof of Funding", "required": True},
            {"name": "Job Creation & Skills Transfer Plan", "required": False},
        ],
        "fee_amount": 10000,
        "annual_fee": 3000,
        "renewal_fee": 8000,
        "validity_period_months": 180,  # 15 years
        "is_domain_applicable": True,
        "sort_order": 2,
    },
]


SAMPLE_APPLICANTS = [
    {
        "email": "applicant1@example.bw",
        "first_name": "Tebogo",
        "last_name": "Mosweu",
        "username": "tebogo.mosweu",
        "organisation": "Botswana Fibre Networks (Pty) Ltd",
        "registration": "BW00012345",
    },
    {
        "email": "applicant2@example.bw",
        "first_name": "Kagiso",
        "last_name": "Matlho",
        "username": "kagiso.matlho",
        "organisation": "Kalahari Connect ISP",
        "registration": "BW00023456",
    },
    {
        "email": "applicant3@example.bw",
        "first_name": "Mpho",
        "last_name": "Ramotswe",
        "username": "mpho.ramotswe",
        "organisation": "Delta Broadcasting Corporation",
        "registration": "BW00034567",
    },
    {
        "email": "applicant4@example.bw",
        "first_name": "Naledi",
        "last_name": "Kgosi",
        "username": "naledi.kgosi",
        "organisation": "Swift Courier Services (Pty) Ltd",
        "registration": "BW00045678",
    },
    {
        "email": "applicant5@example.bw",
        "first_name": "Lesego",
        "last_name": "Tladi",
        "username": "lesego.tladi",
        "organisation": "Marang Radio FM",
        "registration": "BW00056789",
    },
    {
        "email": "applicant6@example.bw",
        "first_name": "Onalenna",
        "last_name": "Setlhare",
        "username": "onalenna.setlhare",
        "organisation": "TechVision Botswana",
        "registration": "BW00067890",
    },
    {
        "email": "applicant7@example.bw",
        "first_name": "Keabetswe",
        "last_name": "Modise",
        "username": "keabetswe.modise",
        "organisation": "Savanna Wireless (Pty) Ltd",
        "registration": "BW00078901",
    },
    {
        "email": "applicant8@example.bw",
        "first_name": "Boitumelo",
        "last_name": "Phiri",
        "username": "boitumelo.phiri",
        "organisation": "DigiPost Botswana",
        "registration": "BW00089012",
    },
]

# Each entry: (licence_type_code, applicant_index, status, description)
SAMPLE_APPLICATIONS = [
    # Approved → licence issued
    ("SAP", 0, "APPROVED", "Application for ISP services covering Gaborone metropolitan area."),
    ("NFP", 0, "APPROVED", "Fibre optic infrastructure deployment along A1 highway corridor."),
    ("SAP", 1, "APPROVED", "Cloud hosting and internet services for SMEs in Francistown."),
    ("VANS", 5, "APPROVED", "Web hosting and e-commerce platform services."),
    ("CRS", 4, "APPROVED", "Community FM radio station broadcasting in Maun area."),
    ("CPO", 3, "APPROVED", "Express courier services between major cities in Botswana."),
    # Under review
    ("NFP", 6, "UNDER_REVIEW", "Wireless broadband infrastructure in North-West district."),
    ("CTS", 2, "UNDER_REVIEW", "Digital terrestrial television broadcasting for Southern region."),
    ("SMS", 2, "UNDER_REVIEW", "Pay-TV subscription management platform launch."),
    ("RDL", 5, "UNDER_REVIEW", "Radio equipment dealership and maintenance services."),
    # Info requested
    ("SAP", 7, "INFO_REQUESTED", "VoIP telephony services for corporate clients."),
    ("RSL", 6, "INFO_REQUESTED", "Microwave link spectrum allocation for rural connectivity."),
    # Submitted
    ("VANS", 1, "SUBMITTED", "Data processing and hosted email services for government agencies."),
    ("CRS", 2, "SUBMITTED", "Commercial FM radio station for Gaborone CBD."),
    ("CPO", 7, "SUBMITTED", "Parcel delivery and logistics services nationwide."),
    ("NCRS", 4, "SUBMITTED", "Community radio for Boteti sub-district."),
    # Rejected
    ("NFP", 5, "REJECTED", "Mobile tower infrastructure — application lacked financial proof."),
    ("CTS", 6, "REJECTED", "Television broadcasting — did not meet local content requirements."),
    # Draft
    ("SAP", 3, "DRAFT", "Internet cafe and public WiFi hotspot services."),
    ("RDL", 7, "DRAFT", "Two-way radio equipment sales and installation."),
]


class Command(BaseCommand):
    help = "Seed BOCRA licence sectors, types, and sample applications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing sectors, types, applications, and licences before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing licensing data...")
            Licence.objects.all().delete()
            ApplicationStatusLog.objects.all().delete()
            Application.objects.all().delete()
            LicenceType.objects.all().delete()
            LicenceSector.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Cleared."))

        # ── Create sectors ────────────────────────────────────────────────
        sector_map = {}
        for s_data in SECTORS:
            sector, created = LicenceSector.objects.update_or_create(
                code=s_data["code"],
                defaults={
                    "name": s_data["name"],
                    "description": s_data["description"],
                    "icon": s_data["icon"],
                    "sort_order": s_data["sort_order"],
                    "is_active": True,
                    "is_deleted": False,
                },
            )
            sector_map[s_data["code"]] = sector
            verb = "Created" if created else "Updated"
            self.stdout.write(f"  {verb} sector: {sector.name}")

        # ── Create licence types ──────────────────────────────────────────
        type_map = {}
        for lt_data in LICENCE_TYPES:
            sector = sector_map[lt_data.pop("sector_code")]
            code = lt_data["code"]
            lt, created = LicenceType.objects.update_or_create(
                code=code,
                defaults={
                    "sector": sector,
                    "is_active": True,
                    "is_deleted": False,
                    **{k: v for k, v in lt_data.items() if k != "code"},
                },
            )
            type_map[code] = lt
            verb = "Created" if created else "Updated"
            self.stdout.write(f"  {verb} type: {lt.name} ({lt.code}) → {sector.code}")

        self.stdout.write(self.style.SUCCESS(
            f"\n  {len(SECTORS)} sectors, {len(LICENCE_TYPES)} licence types seeded."
        ))

        # ── Create sample applicant users ─────────────────────────────────
        self.stdout.write("\nSeeding sample applicant users...")
        applicant_users = []
        for a_data in SAMPLE_APPLICANTS:
            user, created = User.objects.get_or_create(
                email=a_data["email"],
                defaults={
                    "username": a_data["username"],
                    "first_name": a_data["first_name"],
                    "last_name": a_data["last_name"],
                    "role": UserRole.REGISTERED,
                    "is_active": True,
                    "email_verified": True,
                },
            )
            if created:
                user.set_password("TestPass123!")
                user.save(update_fields=["password"])
            applicant_users.append(user)
            verb = "Created" if created else "Exists"
            self.stdout.write(f"  {verb}: {user.get_full_name()} ({user.email})")

        # Get a staff user for review actions
        staff_user = User.objects.filter(
            role__in=[UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN],
            is_active=True,
        ).first()

        # ── Create sample applications ────────────────────────────────────
        self.stdout.write("\nSeeding sample applications...")
        app_count = 0
        licence_count = 0
        now = timezone.now()

        for lt_code, applicant_idx, target_status, description in SAMPLE_APPLICATIONS:
            licence_type = type_map.get(lt_code)
            if not licence_type:
                continue
            applicant = applicant_users[applicant_idx]
            org_data = SAMPLE_APPLICANTS[applicant_idx]

            # Skip if a similar application already exists
            if Application.objects.filter(
                applicant=applicant,
                licence_type=licence_type,
                is_deleted=False,
            ).exists():
                self.stdout.write(f"  Skipped (exists): {lt_code} for {applicant.email}")
                continue

            ref = generate_licence_reference()
            days_ago = random.randint(5, 90)
            created_at = now - timedelta(days=days_ago)

            app = Application.objects.create(
                applicant=applicant,
                licence_type=licence_type,
                reference_number=ref,
                organisation_name=org_data["organisation"],
                organisation_registration=org_data["registration"],
                contact_person=f"{org_data['first_name']} {org_data['last_name']}",
                contact_email=org_data["email"],
                contact_phone=f"+2677{random.randint(1000000, 9999999)}",
                description=description,
                status=ApplicationStatus.DRAFT,
            )
            # Backdate created_at
            Application.objects.filter(pk=app.pk).update(created_at=created_at)

            if target_status == "DRAFT":
                self.stdout.write(f"  Created DRAFT: {ref} ({lt_code})")
                app_count += 1
                continue

            # Submit
            submitted_at = created_at + timedelta(hours=random.randint(1, 48))
            app.status = ApplicationStatus.SUBMITTED
            app.submitted_at = submitted_at
            app.save(update_fields=["status", "submitted_at"])
            ApplicationStatusLog.objects.create(
                application=app,
                from_status=ApplicationStatus.DRAFT,
                to_status=ApplicationStatus.SUBMITTED,
                changed_by=applicant,
                reason="Application submitted by applicant.",
            )

            if target_status == "SUBMITTED":
                self.stdout.write(f"  Created SUBMITTED: {ref} ({lt_code})")
                app_count += 1
                continue

            # Under review
            review_at = submitted_at + timedelta(days=random.randint(1, 5))
            app.status = ApplicationStatus.UNDER_REVIEW
            app.save(update_fields=["status"])
            ApplicationStatusLog.objects.create(
                application=app,
                from_status=ApplicationStatus.SUBMITTED,
                to_status=ApplicationStatus.UNDER_REVIEW,
                changed_by=staff_user,
                reason="Application taken under review.",
            )

            if target_status == "UNDER_REVIEW":
                self.stdout.write(f"  Created UNDER_REVIEW: {ref} ({lt_code})")
                app_count += 1
                continue

            if target_status == "INFO_REQUESTED":
                info_at = review_at + timedelta(days=random.randint(1, 3))
                app.status = ApplicationStatus.INFO_REQUESTED
                app.info_request_message = "Please provide additional financial documentation and updated business plan."
                app.save(update_fields=["status", "info_request_message"])
                ApplicationStatusLog.objects.create(
                    application=app,
                    from_status=ApplicationStatus.UNDER_REVIEW,
                    to_status=ApplicationStatus.INFO_REQUESTED,
                    changed_by=staff_user,
                    reason="Additional documentation required.",
                )
                self.stdout.write(f"  Created INFO_REQUESTED: {ref} ({lt_code})")
                app_count += 1
                continue

            if target_status == "APPROVED":
                decision_at = review_at + timedelta(days=random.randint(3, 14))
                app.status = ApplicationStatus.APPROVED
                app.reviewed_by = staff_user
                app.decision_date = decision_at
                app.save(update_fields=["status", "reviewed_by", "decision_date"])
                ApplicationStatusLog.objects.create(
                    application=app,
                    from_status=ApplicationStatus.UNDER_REVIEW,
                    to_status=ApplicationStatus.APPROVED,
                    changed_by=staff_user,
                    reason="Application meets all requirements. Approved.",
                )
                # Create issued licence
                issued_date = decision_at.date()
                expiry_date = issued_date + timedelta(days=licence_type.validity_period_months * 30)
                licence_number = generate_licence_number(licence_type.code)
                Licence.objects.create(
                    application=app,
                    licence_type=licence_type,
                    holder=applicant,
                    licence_number=licence_number,
                    organisation_name=org_data["organisation"],
                    issued_date=issued_date,
                    expiry_date=expiry_date,
                    status=LicenceStatus.ACTIVE,
                    conditions="Standard conditions apply as per the BOCRA licensing framework.",
                )
                licence_count += 1
                self.stdout.write(f"  Created APPROVED + Licence: {ref} ({lt_code}) → {licence_number}")
                app_count += 1
                continue

            if target_status == "REJECTED":
                decision_at = review_at + timedelta(days=random.randint(3, 10))
                app.status = ApplicationStatus.REJECTED
                app.reviewed_by = staff_user
                app.decision_date = decision_at
                app.decision_reason = "Application did not meet the minimum requirements for this licence type."
                app.save(update_fields=["status", "reviewed_by", "decision_date", "decision_reason"])
                ApplicationStatusLog.objects.create(
                    application=app,
                    from_status=ApplicationStatus.UNDER_REVIEW,
                    to_status=ApplicationStatus.REJECTED,
                    changed_by=staff_user,
                    reason="Application did not meet requirements.",
                )
                self.stdout.write(f"  Created REJECTED: {ref} ({lt_code})")
                app_count += 1
                continue

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {len(SECTORS)} sectors, {len(LICENCE_TYPES)} types, "
            f"{app_count} applications, {licence_count} licences seeded."
        ))

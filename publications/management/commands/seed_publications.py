"""
Management command to seed BOCRA publications data.

Usage:
    python manage.py seed_publications          # Create publications
    python manage.py seed_publications --clear  # Delete existing and recreate
"""
import random
from datetime import timedelta, date

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserRole
from publications.models import (
    Publication,
    PublicationAttachment,
    PublicationCategory,
    PublicationStatus,
)


# ─── SEED DATA ────────────────────────────────────────────────────────────────

PUBLICATIONS = [
    # ── REGULATIONS ───────────────────────────────────────────────────────────
    {
        "title": "Telecommunications Licensing Regulations 2026",
        "category": PublicationCategory.REGULATION,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": True,
        "version": "3.0",
        "summary": (
            "Comprehensive regulations governing the licensing of telecommunications "
            "service providers in Botswana, including application procedures, licence "
            "conditions, and compliance requirements."
        ),
        "published_date": date(2026, 1, 15),
        "download_count": 2345,
    },
    {
        "title": "Radio Frequency Spectrum Management Regulations",
        "category": PublicationCategory.REGULATION,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "2.1",
        "summary": (
            "Regulations governing the allocation, assignment, and management of "
            "radio frequency spectrum in Botswana, including technical standards "
            "and interference management procedures."
        ),
        "published_date": date(2025, 9, 1),
        "download_count": 1567,
    },
    {
        "title": "Botswana Domain Name System Regulations",
        "category": PublicationCategory.REGULATION,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "2.0",
        "summary": (
            "Regulations governing the registration and management of .bw domain "
            "names, including registration procedures, dispute resolution, and "
            "registrar accreditation requirements."
        ),
        "published_date": date(2025, 6, 15),
        "download_count": 890,
    },
    {
        "title": "Type Approval Regulations for Communications Equipment",
        "category": PublicationCategory.REGULATION,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.2",
        "summary": (
            "Regulations specifying the type approval requirements for "
            "telecommunications and broadcasting equipment imported into or "
            "manufactured in Botswana."
        ),
        "published_date": date(2025, 3, 20),
        "download_count": 456,
    },

    # ── POLICIES ──────────────────────────────────────────────────────────────
    {
        "title": "National Broadband Strategy 2026-2030",
        "category": PublicationCategory.POLICY,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": True,
        "version": "1.0",
        "summary": (
            "Botswana's strategic roadmap for achieving universal broadband access "
            "by 2030, outlining infrastructure investment priorities, regulatory "
            "enablers, and public-private partnership models."
        ),
        "published_date": date(2026, 2, 1),
        "download_count": 3210,
    },
    {
        "title": "BOCRA Consumer Protection Policy",
        "category": PublicationCategory.POLICY,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "2.0",
        "summary": (
            "Policy framework for the protection of consumers of telecommunications, "
            "broadcasting, and postal services in Botswana, including complaint "
            "handling procedures and service quality standards."
        ),
        "published_date": date(2025, 11, 10),
        "download_count": 1876,
    },
    {
        "title": "Cybersecurity Policy for Licensed Operators",
        "category": PublicationCategory.POLICY,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "Minimum cybersecurity requirements and incident reporting obligations "
            "for all licensed telecommunications and broadcasting operators in Botswana."
        ),
        "published_date": date(2025, 8, 5),
        "download_count": 1234,
    },

    # ── REPORTS ───────────────────────────────────────────────────────────────
    {
        "title": "Telecommunications Market Report Q4 2025",
        "category": PublicationCategory.REPORT,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "Quarterly market monitoring report covering mobile subscriptions, "
            "broadband penetration, revenue analysis, and competitive landscape "
            "for Q4 2025."
        ),
        "published_date": date(2026, 2, 15),
        "download_count": 2567,
    },
    {
        "title": "Quality of Service Monitoring Report 2025",
        "category": PublicationCategory.REPORT,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "Annual report on the quality of service delivered by licensed "
            "telecommunications operators in Botswana, including network "
            "performance metrics and consumer satisfaction surveys."
        ),
        "published_date": date(2026, 1, 30),
        "download_count": 1890,
    },
    {
        "title": "Postal Sector Performance Report 2025",
        "category": PublicationCategory.REPORT,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "Annual performance review of the postal sector, covering mail "
            "volumes, delivery timelines, universal service compliance, and the "
            "growth of e-commerce parcel delivery."
        ),
        "published_date": date(2025, 12, 20),
        "download_count": 678,
    },
    {
        "title": "Broadcasting Sector Analysis 2025",
        "category": PublicationCategory.REPORT,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "Comprehensive analysis of the broadcasting sector in Botswana, "
            "including television and radio audience metrics, local content "
            "compliance, and digital migration progress."
        ),
        "published_date": date(2025, 11, 15),
        "download_count": 543,
    },

    # ── GUIDELINES ────────────────────────────────────────────────────────────
    {
        "title": "Guidelines for Telecommunications Infrastructure Sharing",
        "category": PublicationCategory.GUIDELINE,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "Guidelines for mandated infrastructure sharing between licensed "
            "operators, covering tower sharing, duct access, fibre sharing, "
            "and national roaming arrangements."
        ),
        "published_date": date(2025, 10, 1),
        "download_count": 987,
    },
    {
        "title": "Guidelines for Licence Application Submission",
        "category": PublicationCategory.GUIDELINE,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": True,
        "version": "2.0",
        "summary": (
            "Step-by-step guide for applicants seeking telecommunications, "
            "broadcasting, or postal service licences from BOCRA, including "
            "required documentation and evaluation criteria."
        ),
        "published_date": date(2025, 7, 15),
        "download_count": 4567,
    },
    {
        "title": "Consumer Complaint Filing Guidelines",
        "category": PublicationCategory.GUIDELINE,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "A guide for consumers on how to file complaints against "
            "telecommunications, broadcasting, and postal service providers "
            "through BOCRA's complaints portal."
        ),
        "published_date": date(2025, 5, 20),
        "download_count": 2345,
    },

    # ── CONSULTATION PAPERS ───────────────────────────────────────────────────
    {
        "title": "Consultation Paper: Net Neutrality Framework for Botswana",
        "category": PublicationCategory.CONSULTATION,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "BOCRA invites public comment on the proposed net neutrality framework "
            "for Botswana, addressing traffic management practices, zero-rating, "
            "and the principles of open internet access."
        ),
        "published_date": date(2026, 3, 1),
        "download_count": 789,
    },
    {
        "title": "Consultation Paper: Over-the-Top (OTT) Services Regulation",
        "category": PublicationCategory.CONSULTATION,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "Discussion paper on the regulatory treatment of over-the-top (OTT) "
            "communication services such as WhatsApp, Zoom, and Skype, and their "
            "impact on traditional telecom revenues."
        ),
        "published_date": date(2025, 12, 1),
        "download_count": 1123,
    },

    # ── ANNUAL REPORTS ────────────────────────────────────────────────────────
    {
        "title": "BOCRA Annual Report 2024/2025",
        "category": PublicationCategory.ANNUAL_REPORT,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": True,
        "version": "1.0",
        "summary": (
            "BOCRA's comprehensive annual report for the 2024/2025 financial year, "
            "covering regulatory activities, market developments, financial statements, "
            "and strategic outlook."
        ),
        "published_date": date(2025, 10, 15),
        "download_count": 5678,
    },
    {
        "title": "BOCRA Annual Report 2023/2024",
        "category": PublicationCategory.ANNUAL_REPORT,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "BOCRA's annual report for the 2023/2024 financial year, documenting "
            "key regulatory achievements, sector performance, and the Authority's "
            "financial position."
        ),
        "published_date": date(2024, 10, 20),
        "download_count": 3210,
    },

    # ── STRATEGY DOCUMENTS ────────────────────────────────────────────────────
    {
        "title": "BOCRA Strategic Plan 2024-2029",
        "category": PublicationCategory.STRATEGY,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "BOCRA's five-year strategic plan outlining regulatory priorities, "
            "institutional capacity building, and the Authority's vision for a "
            "digitally connected Botswana."
        ),
        "published_date": date(2024, 4, 1),
        "download_count": 2890,
    },
    {
        "title": "Digital Transformation Roadmap for Botswana's ICT Sector",
        "category": PublicationCategory.STRATEGY,
        "status": PublicationStatus.PUBLISHED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "A comprehensive roadmap for digital transformation in Botswana's ICT "
            "sector, covering infrastructure modernisation, digital skills development, "
            "and innovation ecosystem building."
        ),
        "published_date": date(2025, 1, 15),
        "download_count": 1456,
    },

    # ── DRAFT PUBLICATIONS ────────────────────────────────────────────────────
    {
        "title": "Draft: Data Protection Guidelines for Operators",
        "category": PublicationCategory.GUIDELINE,
        "status": PublicationStatus.DRAFT,
        "is_featured": False,
        "version": "0.1",
        "summary": (
            "Draft guidelines for licensed operators on data protection "
            "obligations, data breach notification procedures, and customer "
            "data handling best practices."
        ),
        "published_date": None,
        "download_count": 0,
    },
    {
        "title": "Draft: Telecommunications Market Report Q1 2026",
        "category": PublicationCategory.REPORT,
        "status": PublicationStatus.DRAFT,
        "is_featured": False,
        "version": "0.1",
        "summary": (
            "Preliminary data for the Q1 2026 telecommunications market report. "
            "Pending final verification and editorial review."
        ),
        "published_date": None,
        "download_count": 0,
    },

    # ── ARCHIVED ──────────────────────────────────────────────────────────────
    {
        "title": "Telecommunications Licensing Regulations 2022 (Superseded)",
        "category": PublicationCategory.REGULATION,
        "status": PublicationStatus.ARCHIVED,
        "is_featured": False,
        "version": "2.0",
        "summary": (
            "Previous version of the telecommunications licensing regulations, "
            "now superseded by the 2026 edition. Retained for reference purposes."
        ),
        "published_date": date(2022, 3, 15),
        "download_count": 8901,
    },
    {
        "title": "BOCRA Annual Report 2022/2023",
        "category": PublicationCategory.ANNUAL_REPORT,
        "status": PublicationStatus.ARCHIVED,
        "is_featured": False,
        "version": "1.0",
        "summary": (
            "BOCRA's annual report for the 2022/2023 financial year. "
            "Archived following publication of the 2023/2024 report."
        ),
        "published_date": date(2023, 10, 15),
        "download_count": 4567,
    },
]

class Command(BaseCommand):
    help = "Seed BOCRA publications with realistic regulatory documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing publications before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing publications...")
            PublicationAttachment.objects.all().delete()
            Publication.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Cleared."))

        # Get a staff/admin user
        author = User.objects.filter(
            role__in=[UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN],
            is_active=True,
        ).first()

        pub_count = 0

        self.stdout.write("\nSeeding publications...")

        for data in PUBLICATIONS:
            # Skip if publication with same title already exists
            if Publication.objects.filter(title=data["title"]).exists():
                self.stdout.write(f"  Skipped (exists): {data['title'][:60]}")
                continue

            pub = Publication(
                title=data["title"],
                summary=data["summary"],
                category=data["category"],
                status=data["status"],
                published_date=data["published_date"],
                version=data["version"],
                is_featured=data["is_featured"],
                download_count=data["download_count"],
                created_by=author,
            )
            pub.save()

            status_label = data["status"]
            featured = " [FEATURED]" if data["is_featured"] else ""
            self.stdout.write(f"  Created {status_label}{featured}: {data['title'][:60]}")
            pub_count += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Publications seeding complete!"))
        self.stdout.write(f"  Total publications: {Publication.objects.count()}")
        counts = {}
        for cat_val, cat_label in PublicationCategory.choices:
            c = Publication.objects.filter(category=cat_val).count()
            if c:
                counts[cat_label] = c
        for label, c in counts.items():
            self.stdout.write(f"    {label}: {c}")
        self.stdout.write(self.style.SUCCESS("=" * 50))

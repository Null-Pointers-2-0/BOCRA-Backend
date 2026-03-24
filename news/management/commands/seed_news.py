"""
Management command to seed BOCRA news articles.

Usage:
    python manage.py seed_news          # Create articles
    python manage.py seed_news --clear  # Delete existing and recreate
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserRole
from news.models import Article, ArticleStatus, NewsCategory


# ─── SEED DATA ────────────────────────────────────────────────────────────────

ARTICLES = [
    # ── PRESS RELEASES ────────────────────────────────────────────────────────
    {
        "title": "BOCRA Launches New Consumer Complaints Portal",
        "category": NewsCategory.PRESS_RELEASE,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": True,
        "excerpt": (
            "BOCRA has launched a modern online portal enabling Batswana to file "
            "regulatory complaints against telecommunications and postal operators."
        ),
        "content": (
            "<p>The Botswana Communications Regulatory Authority (BOCRA) is pleased to "
            "announce the launch of its new Consumer Complaints Portal, a digital platform "
            "designed to make it easier for Batswana to file and track complaints against "
            "telecommunications, broadcasting, and postal service providers.</p>"
            "<p>The portal allows citizens to submit complaints online, upload supporting "
            "evidence, and track the progress of their cases in real-time. Anonymous "
            "submissions are also supported to encourage reporting of regulatory violations.</p>"
            "<h3>Key Features</h3>"
            "<ul>"
            "<li>Online complaint submission with file attachments</li>"
            "<li>Real-time complaint tracking via reference number</li>"
            "<li>Email notifications at every status change</li>"
            "<li>Anonymous complaint submission option</li>"
            "<li>Mobile-responsive design for smartphone access</li>"
            "</ul>"
            "<p>\"This portal represents a significant step forward in our commitment to "
            "protecting consumer rights in the communications sector,\" said the BOCRA "
            "Chief Executive. \"We encourage all Batswana to use this platform to report "
            "any service quality issues they experience.\"</p>"
        ),
        "view_count": 1245,
    },
    {
        "title": "BOCRA Awards New Telecommunications Licences for 2026",
        "category": NewsCategory.PRESS_RELEASE,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": True,
        "excerpt": (
            "BOCRA has approved five new telecommunications licences as part of "
            "its initiative to increase competition and improve service delivery."
        ),
        "content": (
            "<p>BOCRA has approved five new telecommunications licences following a "
            "rigorous evaluation process. The newly licensed operators will provide "
            "services across various segments including internet service provision, "
            "network infrastructure, and value-added services.</p>"
            "<p>The licensing decisions are part of BOCRA's strategic initiative to "
            "increase competition in the telecommunications market, drive down prices, "
            "and improve service quality for consumers across Botswana.</p>"
            "<h3>Newly Licensed Operators</h3>"
            "<p>The five new licensees include three Services & Applications Provider "
            "(SAP) licence holders and two Network Facilities Provider (NFP) licence "
            "holders. These operators are expected to commence services within six months "
            "of licence issuance.</p>"
            "<p>BOCRA will continue to monitor compliance with licence conditions and "
            "service quality standards to ensure Batswana receive the best possible "
            "telecommunications services.</p>"
        ),
        "view_count": 892,
    },
    {
        "title": "BOCRA Partners with BTCL on Universal Access Initiative",
        "category": NewsCategory.PRESS_RELEASE,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "A new partnership between BOCRA and BTCL aims to extend broadband "
            "connectivity to underserved rural communities across Botswana."
        ),
        "content": (
            "<p>BOCRA and the Botswana Telecommunications Corporation Limited (BTCL) "
            "have signed a memorandum of understanding to jointly implement a Universal "
            "Access initiative that will bring broadband internet connectivity to 50 "
            "underserved rural communities by the end of 2027.</p>"
            "<p>The initiative, funded through the Universal Access and Service Fund "
            "(UASF), will deploy a combination of fibre optic and wireless technologies "
            "to connect schools, clinics, and community centres in remote areas.</p>"
            "<p>\"Access to affordable broadband is no longer a luxury — it is a "
            "necessity for economic participation and social inclusion,\" said the "
            "BOCRA Board Chairperson at the signing ceremony held in Gaborone.</p>"
        ),
        "view_count": 654,
    },
    {
        "title": "BOCRA Fines Operator P2.5 Million for Licence Violations",
        "category": NewsCategory.PRESS_RELEASE,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "BOCRA has imposed a P2.5 million fine on a telecommunications operator "
            "for persistent breach of licence conditions."
        ),
        "content": (
            "<p>Following a comprehensive investigation, BOCRA has imposed a fine of "
            "P2,500,000 (Two Million Five Hundred Thousand Pula) on a major "
            "telecommunications operator for persistent violations of its licence "
            "conditions, including failure to meet quality of service standards and "
            "inadequate consumer complaint resolution processes.</p>"
            "<p>The investigation, which spanned six months, found that the operator "
            "had consistently failed to meet the minimum service quality benchmarks "
            "set by BOCRA, particularly in areas of network availability, call drop "
            "rates, and broadband speed delivery.</p>"
            "<p>The operator has been given 60 days to submit a remediation plan and "
            "demonstrate compliance with all licence conditions. Failure to comply may "
            "result in further penalties including possible licence suspension.</p>"
        ),
        "view_count": 2103,
    },

    # ── ANNOUNCEMENTS ─────────────────────────────────────────────────────────
    {
        "title": "Public Notice: Spectrum Allocation for 5G Services",
        "category": NewsCategory.ANNOUNCEMENT,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": True,
        "excerpt": (
            "BOCRA invites expressions of interest from operators seeking 5G "
            "spectrum allocation in the 3.5 GHz and 26 GHz bands."
        ),
        "content": (
            "<p>BOCRA hereby invites expressions of interest from licensed "
            "telecommunications operators for the allocation of radio frequency "
            "spectrum for 5G mobile services in Botswana.</p>"
            "<h3>Available Spectrum Bands</h3>"
            "<ul>"
            "<li>3.5 GHz band (3400-3600 MHz) — mid-band for urban/suburban coverage</li>"
            "<li>26 GHz band (24.25-27.5 GHz) — mmWave for high-capacity areas</li>"
            "</ul>"
            "<h3>Key Dates</h3>"
            "<ul>"
            "<li>Expression of Interest deadline: 30 April 2026</li>"
            "<li>Pre-qualification results: 31 May 2026</li>"
            "<li>Spectrum auction: Q3 2026 (date to be confirmed)</li>"
            "</ul>"
            "<p>Interested parties should submit their expressions of interest to "
            "BOCRA's Spectrum Management Division. Full guidelines are available on "
            "the BOCRA website.</p>"
        ),
        "view_count": 1567,
    },
    {
        "title": "Notice of Proposed Domain Name Regulation Amendments",
        "category": NewsCategory.ANNOUNCEMENT,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "BOCRA proposes amendments to the .bw domain name registration "
            "regulations and invites public comment."
        ),
        "content": (
            "<p>BOCRA has published proposed amendments to the Botswana Domain Name "
            "System (DNS) Regulations. The proposed changes aim to streamline the "
            "domain registration process, introduce new second-level domains, and "
            "strengthen dispute resolution mechanisms.</p>"
            "<h3>Key Proposed Changes</h3>"
            "<ul>"
            "<li>Introduction of .health.bw domain for healthcare providers</li>"
            "<li>Simplified online registration and renewal process</li>"
            "<li>Enhanced WHOIS privacy protections</li>"
            "<li>New expedited dispute resolution procedures</li>"
            "<li>Reduced registration fees for .org.bw and .ac.bw domains</li>"
            "</ul>"
            "<p>The public comment period is open from 1 March 2026 to 30 April 2026. "
            "Submissions can be made electronically via the BOCRA consultation portal "
            "or in writing to the BOCRA offices in Gaborone.</p>"
        ),
        "view_count": 432,
    },
    {
        "title": "BOCRA Offices Closed for Public Holiday — 30 September",
        "category": NewsCategory.ANNOUNCEMENT,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "BOCRA offices will be closed on 30 September 2026 in observance of "
            "Botswana Independence Day."
        ),
        "content": (
            "<p>Please be advised that BOCRA offices will be closed on Monday, "
            "30 September 2026 in observance of Botswana Independence Day.</p>"
            "<p>Normal operations will resume on Tuesday, 1 October 2026.</p>"
            "<p>For urgent matters during the closure, please email "
            "info@bocra.org.bw or call our 24-hour helpline.</p>"
        ),
        "view_count": 187,
    },

    # ── EVENTS ────────────────────────────────────────────────────────────────
    {
        "title": "BOCRA Annual Consumer Forum 2026",
        "category": NewsCategory.EVENT,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "Join BOCRA's Annual Consumer Forum on 15 May 2026 at GICC, Gaborone — "
            "a platform for dialogue between regulators, operators, and consumers."
        ),
        "content": (
            "<p>BOCRA invites all stakeholders to the Annual Consumer Forum 2026, "
            "themed \"Digital Rights in a Connected Botswana.\"</p>"
            "<h3>Event Details</h3>"
            "<ul>"
            "<li><strong>Date:</strong> 15 May 2026</li>"
            "<li><strong>Venue:</strong> Gaborone International Convention Centre (GICC)</li>"
            "<li><strong>Time:</strong> 08:30 – 16:30</li>"
            "<li><strong>Registration:</strong> Free (pre-registration required)</li>"
            "</ul>"
            "<h3>Programme Highlights</h3>"
            "<ul>"
            "<li>Keynote: The State of Digital Rights in Southern Africa</li>"
            "<li>Panel: Quality of Service — Are Consumers Getting What They Pay For?</li>"
            "<li>Panel: Cybersecurity and Data Protection in Botswana</li>"
            "<li>Workshop: How to File Effective Regulatory Complaints</li>"
            "<li>Operator Exhibition and Consumer Engagement Booths</li>"
            "</ul>"
            "<p>Pre-registration is now open on the BOCRA website.</p>"
        ),
        "view_count": 756,
    },
    {
        "title": "ICT Industry Awards Gala Dinner 2026",
        "category": NewsCategory.EVENT,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "BOCRA hosts the 2026 ICT Industry Awards recognising innovation and "
            "excellence in Botswana's ICT sector."
        ),
        "content": (
            "<p>BOCRA is proud to announce the 2026 ICT Industry Awards Gala Dinner, "
            "an annual event celebrating innovation, excellence, and outstanding "
            "contributions to Botswana's ICT sector.</p>"
            "<h3>Event Details</h3>"
            "<ul>"
            "<li><strong>Date:</strong> 20 June 2026</li>"
            "<li><strong>Venue:</strong> Phakalane Golf Estate, Gaborone</li>"
            "<li><strong>Dress Code:</strong> Black Tie</li>"
            "</ul>"
            "<h3>Award Categories</h3>"
            "<ul>"
            "<li>Best Telecommunications Operator</li>"
            "<li>Best ISP / Broadband Provider</li>"
            "<li>ICT Innovation of the Year</li>"
            "<li>Digital Inclusion Champion</li>"
            "<li>Cybersecurity Excellence Award</li>"
            "<li>Best New Entrant</li>"
            "</ul>"
            "<p>Nominations are open until 15 May 2026. All licensed operators and "
            "ICT companies are eligible for nomination.</p>"
        ),
        "view_count": 523,
    },

    # ── REGULATORY UPDATES ────────────────────────────────────────────────────
    {
        "title": "Updated Quality of Service Standards for Mobile Networks",
        "category": NewsCategory.REGULATORY_UPDATE,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "BOCRA has published updated QoS standards for mobile network operators, "
            "effective 1 July 2026."
        ),
        "content": (
            "<p>BOCRA has published updated Quality of Service (QoS) standards for "
            "mobile network operators in Botswana. The new standards come into effect "
            "on 1 July 2026 and reflect advancements in network technology and "
            "increased consumer expectations.</p>"
            "<h3>Key Changes</h3>"
            "<ul>"
            "<li>Minimum download speed for 4G: increased from 5 Mbps to 10 Mbps</li>"
            "<li>Maximum call drop rate: reduced from 2% to 1%</li>"
            "<li>Network availability: increased from 99% to 99.5%</li>"
            "<li>Complaint resolution timeline: reduced from 30 to 14 days</li>"
            "<li>New metrics for 5G where applicable</li>"
            "</ul>"
            "<p>Operators have been given a six-month transition period to achieve "
            "compliance. BOCRA will conduct quarterly monitoring and publish "
            "comparative QoS reports.</p>"
        ),
        "view_count": 934,
    },
    {
        "title": "New SIM Registration Requirements Take Effect",
        "category": NewsCategory.REGULATORY_UPDATE,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "Enhanced SIM card registration requirements under the revised RICA "
            "framework are now in effect."
        ),
        "content": (
            "<p>BOCRA reminds all mobile network operators and their agents that "
            "the enhanced SIM card registration requirements under the revised "
            "Regulation of Interception of Communications Act (RICA) framework "
            "are now in effect.</p>"
            "<h3>New Requirements</h3>"
            "<ul>"
            "<li>Biometric verification (fingerprint) required for all new SIM registrations</li>"
            "<li>Maximum of 3 SIM cards per individual per network</li>"
            "<li>Corporate SIM registrations require company authorisation letter</li>"
            "<li>Existing unregistered SIMs will be deactivated after 31 March 2026</li>"
            "</ul>"
            "<p>Operators found non-compliant may face penalties of up to P1,000,000 "
            "per violation. BOCRA's compliance team will conduct regular audits at "
            "operator outlets and agent locations.</p>"
        ),
        "view_count": 1876,
    },
    {
        "title": "Postal Sector Regulatory Framework Review",
        "category": NewsCategory.REGULATORY_UPDATE,
        "status": ArticleStatus.PUBLISHED,
        "is_featured": False,
        "excerpt": (
            "BOCRA initiates a comprehensive review of the postal sector regulatory "
            "framework to address e-commerce growth."
        ),
        "content": (
            "<p>In response to the rapid growth of e-commerce in Botswana and the "
            "evolving postal sector landscape, BOCRA has initiated a comprehensive "
            "review of the Postal Services Regulatory Framework.</p>"
            "<p>The review will examine:</p>"
            "<ul>"
            "<li>Universal postal service obligations in the digital age</li>"
            "<li>E-commerce delivery service regulation</li>"
            "<li>Cross-border parcel handling and customs integration</li>"
            "<li>Last-mile delivery standards</li>"
            "<li>Consumer protection for online purchases</li>"
            "</ul>"
            "<p>A consultative paper will be published in Q2 2026. Stakeholders "
            "are encouraged to participate in the consultation process.</p>"
        ),
        "view_count": 312,
    },

    # ── DRAFT ARTICLES ────────────────────────────────────────────────────────
    {
        "title": "BOCRA Q1 2026 Telecommunications Market Report",
        "category": NewsCategory.REGULATORY_UPDATE,
        "status": ArticleStatus.DRAFT,
        "is_featured": False,
        "excerpt": (
            "Key findings from BOCRA's first quarter market monitoring report "
            "on the telecommunications sector."
        ),
        "content": (
            "<p>BOCRA's Q1 2026 market report shows continued growth in the "
            "telecommunications sector, with mobile subscriptions reaching 3.8 million "
            "and broadband penetration increasing to 45%.</p>"
            "<p>[Draft — pending final data verification and approval]</p>"
        ),
        "view_count": 0,
    },
    {
        "title": "Upcoming Changes to Broadcasting Licence Conditions",
        "category": NewsCategory.REGULATORY_UPDATE,
        "status": ArticleStatus.DRAFT,
        "is_featured": False,
        "excerpt": (
            "BOCRA outlines proposed changes to local content requirements for "
            "broadcasting licence holders."
        ),
        "content": (
            "<p>BOCRA is considering amendments to broadcasting licence conditions "
            "that would increase the minimum local content requirement from 20% to 40% "
            "for television broadcasters and from 30% to 50% for radio stations.</p>"
            "<p>[Draft — pending Board discussion and public consultation]</p>"
        ),
        "view_count": 0,
    },

    # ── ARCHIVED ARTICLES ─────────────────────────────────────────────────────
    {
        "title": "BOCRA 2025 Annual Report Published",
        "category": NewsCategory.PRESS_RELEASE,
        "status": ArticleStatus.ARCHIVED,
        "is_featured": False,
        "excerpt": (
            "BOCRA's 2025 Annual Report highlights key achievements in regulatory "
            "oversight and consumer protection."
        ),
        "content": (
            "<p>BOCRA has published its 2025 Annual Report, highlighting key "
            "achievements including the licensing of 12 new operators, resolution "
            "of over 3,000 consumer complaints, and a 15% increase in broadband "
            "penetration across Botswana.</p>"
            "<p>The full report is available for download on the BOCRA publications page.</p>"
        ),
        "view_count": 3421,
    },
    {
        "title": "2025 World Telecommunications Day Celebrations",
        "category": NewsCategory.EVENT,
        "status": ArticleStatus.ARCHIVED,
        "is_featured": False,
        "excerpt": (
            "BOCRA celebrates World Telecommunications Day 2025 with industry "
            "stakeholders and the public."
        ),
        "content": (
            "<p>BOCRA celebrated World Telecommunications Day 2025 under the theme "
            "\"Digital Technologies for Older Persons and Healthy Ageing.\" The event "
            "brought together industry leaders, government officials, and the public "
            "to discuss the role of ICT in improving the lives of all Batswana.</p>"
        ),
        "view_count": 567,
    },
]

class Command(BaseCommand):
    help = "Seed BOCRA news articles with realistic content."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing articles before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing articles...")
            Article.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Cleared."))

        # Get a staff/admin user for author
        author = User.objects.filter(
            role__in=[UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN],
            is_active=True,
        ).first()

        now = timezone.now()
        article_count = 0

        self.stdout.write("\nSeeding news articles...")

        for idx, data in enumerate(ARTICLES):
            # Skip if article with same title already exists
            if Article.objects.filter(title=data["title"]).exists():
                self.stdout.write(f"  Skipped (exists): {data['title'][:60]}")
                continue

            days_ago = random.randint(1, 180)
            created_at = now - timedelta(days=days_ago)

            published_at = None
            if data["status"] == ArticleStatus.PUBLISHED:
                published_at = created_at + timedelta(hours=random.randint(1, 24))
            elif data["status"] == ArticleStatus.ARCHIVED:
                published_at = created_at

            article = Article(
                title=data["title"],
                excerpt=data["excerpt"],
                content=data["content"],
                category=data["category"],
                status=data["status"],
                author=author,
                published_at=published_at,
                is_featured=data["is_featured"],
                view_count=data["view_count"],
            )
            article.save()

            # Backdate created_at
            Article.objects.filter(pk=article.pk).update(created_at=created_at)

            status_label = data["status"]
            featured = " [FEATURED]" if data["is_featured"] else ""
            self.stdout.write(f"  Created {status_label}{featured}: {data['title'][:60]}")
            article_count += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("News seeding complete!"))
        self.stdout.write(f"  Total articles: {Article.objects.count()}")
        counts = {}
        for cat_val, cat_label in NewsCategory.choices:
            c = Article.objects.filter(category=cat_val).count()
            if c:
                counts[cat_label] = c
        for label, c in counts.items():
            self.stdout.write(f"    {label}: {c}")
        self.stdout.write(self.style.SUCCESS("=" * 50))

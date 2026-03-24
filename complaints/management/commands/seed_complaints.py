"""
Management command to seed realistic BOCRA complaints data.

Usage:
    python manage.py seed_complaints          # Create complaints
    python manage.py seed_complaints --clear  # Delete existing and recreate
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserRole
from complaints.models import (
    CaseNote,
    Complaint,
    ComplaintCategory,
    ComplaintDocument,
    ComplaintPriority,
    ComplaintStatus,
    ComplaintStatusLog,
    SLA_DAYS_BY_PRIORITY,
)
from complaints.utils import generate_complaint_reference
from licensing.models import Licence


# ─── SEED DATA ────────────────────────────────────────────────────────────────

COMPLAINANTS = [
    {
        "name": "Keabetswe Mokhutshwane",
        "email": "keabetswe.m@gmail.com",
        "phone": "+26774501234",
    },
    {
        "name": "Mothusi Kgosidintsi",
        "email": "mothusi.k@yahoo.com",
        "phone": "+26771234567",
    },
    {
        "name": "Boitumelo Seretse",
        "email": "boitumelo.seretse@outlook.com",
        "phone": "+26776001122",
    },
    {
        "name": "Lesego Tau",
        "email": "lesego.tau@hotmail.com",
        "phone": "+26772345678",
    },
    {
        "name": "Mpho Radikolo",
        "email": "mpho.radikolo@gmail.com",
        "phone": "+26773456789",
    },
    {
        "name": "Naledi Gabatshwane",
        "email": "naledi.g@gmail.com",
        "phone": "+26775678901",
    },
    {
        "name": "Tebogo Molefhe",
        "email": "tebogo.molefhe@gmail.com",
        "phone": "+26776789012",
    },
    {
        "name": "Kagiso Phiri",
        "email": "kagiso.phiri@yahoo.com",
        "phone": "+26777890123",
    },
    {
        "name": "Oratile Motswagole",
        "email": "oratile.m@gmail.com",
        "phone": "+26778901234",
    },
    {
        "name": "Refilwe Kgomotso",
        "email": "refilwe.k@outlook.com",
        "phone": "+26779012345",
    },
]

OPERATORS = [
    "Mascom Wireless",
    "Orange Botswana",
    "BTC (be Mobile)",
    "Liquid Intelligent Technologies",
    "BoFiNet",
    "Paratus Botswana",
    "Dyntec Consulting",
    "MultiChoice Botswana",
    "GBC (Gabz FM / RB2)",
    "Botswana Post",
    "DHL Botswana",
    "FedEx Botswana",
]

# (category, subject, description, operator_name, priority)
COMPLAINT_SCENARIOS = [
    # ── SERVICE_QUALITY ───────────────────────────────────────────────────────
    (
        ComplaintCategory.SERVICE_QUALITY,
        "Frequent network outages in Gaborone West",
        (
            "I have been experiencing frequent network outages on my Mascom line "
            "for the past three weeks. The service drops at least 4-5 times daily, "
            "each lasting 30 minutes to 2 hours. This is severely affecting my "
            "ability to work from home. I have reported the issue to the operator's "
            "call centre multiple times (Ref: MSC-2026-4412, MSC-2026-4489) but "
            "nothing has been done. The area affected is Extension 12, Gaborone West."
        ),
        "Mascom Wireless",
        ComplaintPriority.HIGH,
    ),
    (
        ComplaintCategory.SERVICE_QUALITY,
        "Poor voice call quality on Orange network in Francistown",
        (
            "Calls on my Orange line constantly drop and have static/echo issues "
            "especially between 8am-6pm in the Francistown CBD area. This has been "
            "ongoing for over a month. Other Orange users in my office confirm "
            "similar issues. Orange customer care acknowledged the problem but "
            "provided no timeline for resolution."
        ),
        "Orange Botswana",
        ComplaintPriority.MEDIUM,
    ),
    (
        ComplaintCategory.SERVICE_QUALITY,
        "Slow internet speeds on fibre connection",
        (
            "My Liquid Telecom fibre connection consistently delivers only 5-10 Mbps "
            "despite paying for a 50 Mbps package. Speed tests at different times of "
            "day confirm the issue. I have a business account and this is impacting "
            "our operations. The issue has persisted for 6 weeks."
        ),
        "Liquid Intelligent Technologies",
        ComplaintPriority.HIGH,
    ),
    (
        ComplaintCategory.SERVICE_QUALITY,
        "Internet service not available in Maun area",
        (
            "We subscribed to Paratus internet service for our lodge in the Maun "
            "area. The connection has been down for the past 10 days with no "
            "communication from the provider. We rely on internet for guest bookings "
            "and credit card processing."
        ),
        "Paratus Botswana",
        ComplaintPriority.URGENT,
    ),

    # ── BILLING ───────────────────────────────────────────────────────────────
    (
        ComplaintCategory.BILLING,
        "Overcharged on monthly postpaid bill",
        (
            "My February 2026 Mascom postpaid bill is P2,340 when it is normally "
            "around P450. The bill includes P1,800 in data charges I did not incur. "
            "I have a 10GB monthly bundle and my phone shows only 6GB used. I have "
            "been to the Mascom shop at Riverwalk twice but was told to 'wait for "
            "investigation' with no reference number or timeline."
        ),
        "Mascom Wireless",
        ComplaintPriority.MEDIUM,
    ),
    (
        ComplaintCategory.BILLING,
        "Unauthorised premium SMS charges on Orange line",
        (
            "I noticed recurring charges of P5.00 per day from a premium SMS "
            "service I never subscribed to. These charges have been accumulating "
            "for 3 months, totalling approximately P450. Orange says I must contact "
            "the content provider directly, which I believe is unfair."
        ),
        "Orange Botswana",
        ComplaintPriority.MEDIUM,
    ),
    (
        ComplaintCategory.BILLING,
        "Double billing after plan migration",
        (
            "I migrated from a BTC prepaid plan to postpaid in January 2026. Since "
            "then I have been billed on both the old prepaid and new postpaid account. "
            "Total overcharge is approximately P1,200 over two months. Multiple visits "
            "to BTC offices have not resolved the issue."
        ),
        "BTC (be Mobile)",
        ComplaintPriority.HIGH,
    ),

    # ── COVERAGE ──────────────────────────────────────────────────────────────
    (
        ComplaintCategory.COVERAGE,
        "No mobile coverage in Letlhakane village",
        (
            "There is absolutely no mobile coverage from any operator in parts of "
            "Letlhakane village, specifically the new extension areas near the "
            "primary school. Residents have to walk 2km to get signal. This is a "
            "safety concern as emergency calls cannot be made."
        ),
        "Mascom Wireless",
        ComplaintPriority.HIGH,
    ),
    (
        ComplaintCategory.COVERAGE,
        "Network coverage gaps along A1 highway",
        (
            "There are significant dead zones along the A1 highway between Gaborone "
            "and Francistown, particularly the Palapye-Serowe stretch. This is "
            "dangerous as motorists cannot call for help in case of emergencies. "
            "All three mobile operators have gaps in this corridor."
        ),
        "BTC (be Mobile)",
        ComplaintPriority.MEDIUM,
    ),

    # ── CONDUCT ───────────────────────────────────────────────────────────────
    (
        ComplaintCategory.CONDUCT,
        "Misleading advertising of data bundle speeds",
        (
            "Orange Botswana is advertising '4G LTE speeds up to 150 Mbps' in their "
            "current campaign, but independent tests in Gaborone, where they claim full "
            "4G coverage, consistently show speeds of 5-15 Mbps. This constitutes "
            "misleading advertising under the Consumer Protection Act."
        ),
        "Orange Botswana",
        ComplaintPriority.MEDIUM,
    ),
    (
        ComplaintCategory.CONDUCT,
        "Operator refusing to release number for porting",
        (
            "I have been trying to port my number from Mascom to Orange for the past "
            "3 weeks. Mascom keeps finding reasons to delay — first they said the form "
            "was wrong, then that there was a 'system issue,' then that I need to clear "
            "a P0.00 balance. This is clear anti-competitive behaviour."
        ),
        "Mascom Wireless",
        ComplaintPriority.LOW,
    ),
    (
        ComplaintCategory.CONDUCT,
        "Unfair contract termination penalty",
        (
            "BTC is demanding P4,500 early termination fee for a 24-month contract, "
            "despite the fact that they have failed to deliver the promised speeds for "
            "over 6 months. I believe the penalty should be waived given their breach "
            "of the service level agreement."
        ),
        "BTC (be Mobile)",
        ComplaintPriority.LOW,
    ),

    # ── INTERNET ──────────────────────────────────────────────────────────────
    (
        ComplaintCategory.INTERNET,
        "ISP throttling specific websites and services",
        (
            "My ISP Dyntec appears to be throttling access to specific streaming "
            "services (Netflix, Showmax) and VoIP services (WhatsApp calls, Zoom). "
            "Regular speed tests show 40 Mbps but these services barely work. Using "
            "a VPN resolves the issue, confirming deliberate throttling."
        ),
        "Dyntec Consulting",
        ComplaintPriority.MEDIUM,
    ),
    (
        ComplaintCategory.INTERNET,
        "Data cap applied without notification",
        (
            "Mascom applied a 50GB fair usage policy cap on my 'unlimited' data "
            "package without any prior notification. After 50GB, speeds are reduced "
            "to 256 Kbps which is unusable. The term 'unlimited' is clearly misleading "
            "when such a severe cap exists."
        ),
        "Mascom Wireless",
        ComplaintPriority.MEDIUM,
    ),

    # ── BROADCASTING ──────────────────────────────────────────────────────────
    (
        ComplaintCategory.BROADCASTING,
        "DStv signal loss and poor customer service",
        (
            "My DStv service has had persistent signal issues for over a month. The "
            "decoder shows E48-32 error codes daily. MultiChoice sent a technician "
            "who said the dish is fine, but the issue persists. I am still being "
            "charged full subscription despite the poor service."
        ),
        "MultiChoice Botswana",
        ComplaintPriority.LOW,
    ),
    (
        ComplaintCategory.BROADCASTING,
        "Radio station broadcasting beyond licensed area",
        (
            "A local radio station (Gabz FM) appears to be broadcasting on frequencies "
            "that interfere with my VSAT internet equipment. The interference occurs "
            "during peak broadcast hours and disrupts our satellite communications "
            "at our farm in Tlokweng."
        ),
        "GBC (Gabz FM / RB2)",
        ComplaintPriority.MEDIUM,
    ),

    # ── POSTAL ────────────────────────────────────────────────────────────────
    (
        ComplaintCategory.POSTAL,
        "Lost registered mail package",
        (
            "A registered mail package sent from Johannesburg to Gaborone via "
            "Botswana Post (tracking: BP-REG-2026-88421) has been missing for 6 weeks. "
            "The package contained important legal documents. Botswana Post's tracking "
            "system shows it arrived in Gaborone but it was never delivered or made "
            "available for collection."
        ),
        "Botswana Post",
        ComplaintPriority.HIGH,
    ),
    (
        ComplaintCategory.POSTAL,
        "Courier service delivery delays",
        (
            "DHL Botswana has been consistently delivering packages 5-7 days late for "
            "the past 2 months. We are a business that relies on timely deliveries of "
            "medical supplies. Three shipments (AWB: 1234567890, 1234567891, 1234567892) "
            "were all significantly delayed without explanation."
        ),
        "DHL Botswana",
        ComplaintPriority.HIGH,
    ),

    # ── OTHER ─────────────────────────────────────────────────────────────────
    (
        ComplaintCategory.OTHER,
        "Unlicensed operator selling airtime in Mahalapye",
        (
            "There is a dealer in Mahalapye Mall selling Mascom and Orange airtime "
            "and SIM cards without any visible licence or authorisation. They are also "
            "registering SIMs without proper RICA documentation. This poses a security "
            "concern and undermines BOCRA regulations."
        ),
        "Mascom Wireless",
        ComplaintPriority.MEDIUM,
    ),
    (
        ComplaintCategory.OTHER,
        "Telecom tower construction without community consultation",
        (
            "Mascom is constructing a telecommunications tower in our residential area "
            "(Block 8, Gaborone) without any community consultation or visible planning "
            "permission. Residents are concerned about potential health effects and the "
            "impact on property values. We request BOCRA intervene."
        ),
        "Mascom Wireless",
        ComplaintPriority.LOW,
    ),
]

# Target statuses for complaints: maps to the states we want in the DB
# (scenario_index, complainant_index, target_status, is_anonymous)
COMPLAINT_ASSIGNMENTS = [
    # Submitted — just filed, not yet assigned
    (0, 0, ComplaintStatus.SUBMITTED, False),
    (1, 1, ComplaintStatus.SUBMITTED, True),

    # Assigned — assigned to a staff member
    (2, 2, ComplaintStatus.ASSIGNED, False),
    (3, 3, ComplaintStatus.ASSIGNED, False),

    # Investigating — actively being looked into
    (4, 4, ComplaintStatus.INVESTIGATING, False),
    (5, 5, ComplaintStatus.INVESTIGATING, True),
    (6, 6, ComplaintStatus.INVESTIGATING, False),

    # Awaiting response — waiting for operator reply
    (7, 7, ComplaintStatus.AWAITING_RESPONSE, False),
    (8, 8, ComplaintStatus.AWAITING_RESPONSE, True),

    # Resolved
    (9, 9, ComplaintStatus.RESOLVED, False),
    (10, 0, ComplaintStatus.RESOLVED, False),
    (11, 1, ComplaintStatus.RESOLVED, True),

    # Closed
    (12, 2, ComplaintStatus.CLOSED, False),
    (13, 3, ComplaintStatus.CLOSED, False),

    # Reopened
    (14, 4, ComplaintStatus.REOPENED, False),

    # Additional variety
    (15, 5, ComplaintStatus.SUBMITTED, False),
    (16, 6, ComplaintStatus.INVESTIGATING, True),
    (17, 7, ComplaintStatus.ASSIGNED, False),
    (18, 8, ComplaintStatus.RESOLVED, False),
    (19, 9, ComplaintStatus.CLOSED, True),
]

CASE_NOTE_TEMPLATES = [
    "Initial assessment complete. Complaint falls under {category} category.",
    "Contacted operator ({operator}) for their response. Reference provided.",
    "Operator response received. Reviewing against regulatory framework.",
    "Follow-up call with complainant to gather additional details.",
    "Escalated to senior regulatory officer due to SLA approaching.",
    "Documentation reviewed. Preparing formal response to complainant.",
    "Site inspection scheduled for {operator} network in the affected area.",
    "Operator has acknowledged the issue and provided a remediation timeline.",
    "Mediation session scheduled between complainant and {operator}.",
    "Final resolution drafted. Awaiting approval from department head.",
]


class Command(BaseCommand):
    help = "Seed BOCRA complaints with realistic Botswana telecom complaint data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing complaint data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing complaint data...")
            ComplaintStatusLog.objects.all().delete()
            CaseNote.objects.all().delete()
            ComplaintDocument.objects.all().delete()
            Complaint.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Cleared."))

        # Get or create staff user for assignments
        staff_user = User.objects.filter(
            role__in=[UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN],
            is_active=True,
        ).first()

        # Get some active licences to link complaints to
        active_licences = list(Licence.objects.filter(status="ACTIVE")[:10])
        licence_map = {}
        for lic in active_licences:
            licence_map[lic.organisation_name] = lic

        now = timezone.now()
        complaint_count = 0

        self.stdout.write("\nSeeding complaints...")

        for scenario_idx, complainant_idx, target_status, is_anonymous in COMPLAINT_ASSIGNMENTS:
            scenario = COMPLAINT_SCENARIOS[scenario_idx]
            category, subject, description, operator_name, priority = scenario
            complainant_data = COMPLAINANTS[complainant_idx]

            # Generate reference
            ref = generate_complaint_reference()

            # Check for duplicate
            if Complaint.objects.filter(
                complainant_name=complainant_data["name"],
                subject=subject,
                is_deleted=False,
            ).exists():
                self.stdout.write(f"  Skipped (exists): {subject[:50]}")
                continue

            days_ago = random.randint(5, 120)
            created_at = now - timedelta(days=days_ago)
            sla_days = SLA_DAYS_BY_PRIORITY.get(priority, 14)
            sla_deadline = created_at + timedelta(days=sla_days)

            # Try to find a matching licence
            against_licence = None
            for lic_name, lic in licence_map.items():
                if operator_name.lower() in lic_name.lower() or lic_name.lower() in operator_name.lower():
                    against_licence = lic
                    break

            complaint = Complaint.objects.create(
                reference_number=ref,
                complainant=None if is_anonymous else staff_user,  # use staff as placeholder
                complainant_name=complainant_data["name"],
                complainant_email=complainant_data["email"],
                complainant_phone=complainant_data["phone"] if not is_anonymous else "",
                against_licensee=against_licence,
                against_operator_name=operator_name,
                category=category,
                subject=subject,
                description=description,
                status=ComplaintStatus.SUBMITTED,
                priority=priority,
                sla_deadline=sla_deadline,
            )
            # Backdate created_at
            Complaint.objects.filter(pk=complaint.pk).update(created_at=created_at)

            # Initial status log
            ComplaintStatusLog.objects.create(
                complaint=complaint,
                from_status="",
                to_status=ComplaintStatus.SUBMITTED,
                changed_by=None if is_anonymous else staff_user,
                reason="Complaint submitted.",
            )

            if target_status == ComplaintStatus.SUBMITTED:
                self.stdout.write(f"  Created SUBMITTED: {ref} — {subject[:50]}")
                complaint_count += 1
                self._add_case_notes(complaint, staff_user, category, operator_name, count=1)
                continue

            # Assign
            assigned_at = created_at + timedelta(hours=random.randint(2, 48))
            complaint.status = ComplaintStatus.ASSIGNED
            complaint.assigned_to = staff_user
            complaint.save(update_fields=["status", "assigned_to"])
            ComplaintStatusLog.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.SUBMITTED,
                to_status=ComplaintStatus.ASSIGNED,
                changed_by=staff_user,
                reason="Complaint assigned for investigation.",
            )

            if target_status == ComplaintStatus.ASSIGNED:
                self.stdout.write(f"  Created ASSIGNED: {ref} — {subject[:50]}")
                complaint_count += 1
                self._add_case_notes(complaint, staff_user, category, operator_name, count=2)
                continue

            # Investigating
            invest_at = assigned_at + timedelta(days=random.randint(1, 5))
            complaint.status = ComplaintStatus.INVESTIGATING
            complaint.save(update_fields=["status"])
            ComplaintStatusLog.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.ASSIGNED,
                to_status=ComplaintStatus.INVESTIGATING,
                changed_by=staff_user,
                reason="Investigation commenced. Operator contacted for response.",
            )

            if target_status == ComplaintStatus.INVESTIGATING:
                self.stdout.write(f"  Created INVESTIGATING: {ref} — {subject[:50]}")
                complaint_count += 1
                self._add_case_notes(complaint, staff_user, category, operator_name, count=3)
                continue

            # Awaiting response
            if target_status == ComplaintStatus.AWAITING_RESPONSE:
                await_at = invest_at + timedelta(days=random.randint(2, 7))
                complaint.status = ComplaintStatus.AWAITING_RESPONSE
                complaint.save(update_fields=["status"])
                ComplaintStatusLog.objects.create(
                    complaint=complaint,
                    from_status=ComplaintStatus.INVESTIGATING,
                    to_status=ComplaintStatus.AWAITING_RESPONSE,
                    changed_by=staff_user,
                    reason="Formal inquiry sent to operator. Awaiting response within 14 days.",
                )
                self.stdout.write(f"  Created AWAITING_RESPONSE: {ref} — {subject[:50]}")
                complaint_count += 1
                self._add_case_notes(complaint, staff_user, category, operator_name, count=3)
                continue

            # Resolved
            resolve_at = invest_at + timedelta(days=random.randint(5, 25))
            complaint.status = ComplaintStatus.RESOLVED
            complaint.resolved_at = resolve_at
            complaint.resolution = self._get_resolution(category, operator_name)
            complaint.save(update_fields=["status", "resolved_at", "resolution"])
            ComplaintStatusLog.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.INVESTIGATING,
                to_status=ComplaintStatus.RESOLVED,
                changed_by=staff_user,
                reason="Complaint resolved following operator remediation.",
            )

            if target_status == ComplaintStatus.RESOLVED:
                self.stdout.write(f"  Created RESOLVED: {ref} — {subject[:50]}")
                complaint_count += 1
                self._add_case_notes(complaint, staff_user, category, operator_name, count=4)
                continue

            # Closed
            close_at = resolve_at + timedelta(days=random.randint(3, 14))
            complaint.status = ComplaintStatus.CLOSED
            complaint.save(update_fields=["status"])
            ComplaintStatusLog.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.RESOLVED,
                to_status=ComplaintStatus.CLOSED,
                changed_by=staff_user,
                reason="Case closed. Complainant satisfied with resolution.",
            )

            if target_status == ComplaintStatus.CLOSED:
                self.stdout.write(f"  Created CLOSED: {ref} — {subject[:50]}")
                complaint_count += 1
                self._add_case_notes(complaint, staff_user, category, operator_name, count=5)
                continue

            # Reopened
            if target_status == ComplaintStatus.REOPENED:
                reopen_at = close_at + timedelta(days=random.randint(5, 20))
                complaint.status = ComplaintStatus.REOPENED
                complaint.resolved_at = None
                complaint.save(update_fields=["status", "resolved_at"])
                ComplaintStatusLog.objects.create(
                    complaint=complaint,
                    from_status=ComplaintStatus.CLOSED,
                    to_status=ComplaintStatus.REOPENED,
                    changed_by=staff_user,
                    reason="Complainant reports issue has recurred. Reopening investigation.",
                )
                self.stdout.write(f"  Created REOPENED: {ref} — {subject[:50]}")
                complaint_count += 1
                self._add_case_notes(complaint, staff_user, category, operator_name, count=4)
                continue

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Complaint seeding complete!"))
        self.stdout.write(f"  Complaints:   {Complaint.objects.count()}")
        self.stdout.write(f"  Status logs:  {ComplaintStatusLog.objects.count()}")
        self.stdout.write(f"  Case notes:   {CaseNote.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 50))

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _add_case_notes(self, complaint, staff_user, category, operator_name, count=2):
        """Add realistic case notes to a complaint."""
        templates = random.sample(CASE_NOTE_TEMPLATES, min(count, len(CASE_NOTE_TEMPLATES)))
        for tmpl in templates:
            content = tmpl.format(
                category=category,
                operator=operator_name,
            )
            CaseNote.objects.create(
                complaint=complaint,
                author=staff_user,
                content=content,
                is_internal=random.choice([True, True, False]),  # mostly internal
            )

    def _get_resolution(self, category, operator_name):
        """Return a realistic resolution text based on category."""
        resolutions = {
            ComplaintCategory.SERVICE_QUALITY: (
                f"Following BOCRA's intervention, {operator_name} has acknowledged the "
                f"service quality issues and has committed to upgrading infrastructure "
                f"in the affected area within 30 days. A service credit of P200 has been "
                f"issued to the complainant's account."
            ),
            ComplaintCategory.BILLING: (
                f"{operator_name} has reviewed the billing records and confirmed an error. "
                f"A refund of the overcharged amount has been processed and will reflect "
                f"within 5 business days. {operator_name} has been directed to review their "
                f"billing systems to prevent recurrence."
            ),
            ComplaintCategory.COVERAGE: (
                f"BOCRA has directed {operator_name} to submit a network expansion plan "
                f"for the affected area within 60 days. A temporary mobile base station "
                f"has been deployed as an interim measure."
            ),
            ComplaintCategory.CONDUCT: (
                f"The matter has been investigated and {operator_name} has been formally "
                f"cautioned regarding their conduct. The operator has agreed to comply "
                f"with the relevant provisions of the Communications Regulatory Authority "
                f"Act and applicable licence conditions."
            ),
            ComplaintCategory.INTERNET: (
                f"BOCRA has confirmed that the practice contravenes net neutrality "
                f"principles. {operator_name} has been directed to cease the practice "
                f"immediately and provide full speeds as advertised in the service package."
            ),
            ComplaintCategory.BROADCASTING: (
                f"A technical inspection has been conducted. {operator_name} has been "
                f"directed to adjust their equipment to comply with licensed parameters. "
                f"A follow-up inspection will be conducted within 14 days."
            ),
            ComplaintCategory.POSTAL: (
                f"{operator_name} has located the item and arranged for immediate delivery. "
                f"Compensation has been offered to the complainant for the delay. "
                f"BOCRA has directed the operator to improve tracking and handling procedures."
            ),
            ComplaintCategory.OTHER: (
                f"The matter has been investigated by BOCRA's compliance team. "
                f"Appropriate regulatory action has been taken against the implicated "
                f"party. The complainant has been notified of the outcome."
            ),
        }
        return resolutions.get(category, "Complaint resolved following BOCRA's intervention.")

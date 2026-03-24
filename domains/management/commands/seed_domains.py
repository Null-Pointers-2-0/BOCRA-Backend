"""
Management command: seed_domains

Populates the database with realistic .bw domain registry data.

Usage:
    python manage.py seed_domains          # Seed all data
    python manage.py seed_domains --clear  # Remove existing seeded data first

Creates:
    - 6 domain zones
    - ~500 registered domains across all zones
    - ~25 domain applications in various states
    - Domain events for each domain
"""
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from domains.models import (
    Domain,
    DomainApplication,
    DomainApplicationStatus,
    DomainApplicationStatusLog,
    DomainApplicationType,
    DomainEvent,
    DomainEventType,
    DomainStatus,
    DomainZone,
)


class Command(BaseCommand):
    help = "Seed the domains app with realistic .bw domain registry data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove all existing seeded domain data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing domain data...")
            DomainEvent.objects.all().delete()
            DomainApplicationStatusLog.objects.all().delete()
            DomainApplication.objects.all().delete()
            Domain.objects.all().delete()
            DomainZone.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared all domain data."))

        self.stdout.write("Seeding domain zones...")
        zones = self._seed_zones()

        self.stdout.write("Seeding registered domains...")
        domains = self._seed_domains(zones)

        self.stdout.write("Seeding domain events...")
        self._seed_events(domains)

        self.stdout.write("Seeding domain applications...")
        self._seed_applications(zones)

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("═" * 50))
        self.stdout.write(self.style.SUCCESS("Domain seeding complete!"))
        self.stdout.write(f"  Zones:        {DomainZone.objects.count()}")
        self.stdout.write(f"  Domains:      {Domain.objects.count()}")
        self.stdout.write(f"  Applications: {DomainApplication.objects.count()}")
        self.stdout.write(f"  Events:       {DomainEvent.objects.count()}")
        self.stdout.write(self.style.SUCCESS("═" * 50))

    # ─── ZONES ────────────────────────────────────────────────────────────────

    def _seed_zones(self):
        zone_data = [
            {
                "name": ".co.bw",
                "code": "CO_BW",
                "description": "Commercial entities — businesses, companies, and commercial organisations registered in Botswana.",
                "registration_fee": Decimal("250.00"),
                "renewal_fee": Decimal("250.00"),
                "is_restricted": False,
            },
            {
                "name": ".org.bw",
                "code": "ORG_BW",
                "description": "Non-profit organisations, NGOs, charities, industry bodies, and associations.",
                "registration_fee": Decimal("200.00"),
                "renewal_fee": Decimal("200.00"),
                "is_restricted": False,
            },
            {
                "name": ".ac.bw",
                "code": "AC_BW",
                "description": "Academic and educational institutions — universities, colleges, schools, and training centres.",
                "registration_fee": Decimal("150.00"),
                "renewal_fee": Decimal("150.00"),
                "is_restricted": True,
                "eligibility_criteria": "Must be a registered academic or educational institution in Botswana.",
            },
            {
                "name": ".gov.bw",
                "code": "GOV_BW",
                "description": "Government agencies — ministries, departments, parastatals, and local councils.",
                "registration_fee": Decimal("0.00"),
                "renewal_fee": Decimal("0.00"),
                "is_restricted": True,
                "eligibility_criteria": "Must be a Botswana government ministry, department, parastatal, or local authority.",
            },
            {
                "name": ".net.bw",
                "code": "NET_BW",
                "description": "Network and internet service providers, hosting companies, and tech infrastructure operators.",
                "registration_fee": Decimal("250.00"),
                "renewal_fee": Decimal("250.00"),
                "is_restricted": False,
            },
            {
                "name": ".bw",
                "code": "BW",
                "description": "Direct .bw registration — premium namespace for well-known Botswana brands and entities. Reviewed case-by-case.",
                "registration_fee": Decimal("500.00"),
                "renewal_fee": Decimal("500.00"),
                "is_restricted": True,
                "eligibility_criteria": "Applications reviewed case-by-case. Must demonstrate strong association with Botswana.",
            },
        ]

        zones = {}
        for data in zone_data:
            zone, created = DomainZone.objects.update_or_create(
                code=data["code"],
                defaults=data,
            )
            zones[data["code"]] = zone
            status = "created" if created else "updated"
            self.stdout.write(f"  {zone.name} — {status}")

        return zones

    # ─── DOMAINS ──────────────────────────────────────────────────────────────

    def _seed_domains(self, zones):
        all_domains = []

        # ── .co.bw domains (~280) ────────────────────────────────────────────
        co_bw_entries = [
            # Telecoms
            ("btc.co.bw", "Botswana Telecommunications Corporation", "BTC Limited"),
            ("mascom.co.bw", "Mascom Wireless", "Mascom Wireless Pty Ltd"),
            ("orange.co.bw", "Orange Botswana", "Orange Botswana Pty Ltd"),
            ("bofinet.co.bw", "Botswana Fibre Networks", "BoFiNet"),
            ("liquid.co.bw", "Liquid Intelligent Technologies", "Liquid Telecom Botswana"),
            ("paratus.co.bw", "Paratus Botswana", "Paratus Telecommunications"),
            ("microtech.co.bw", "Microtech Communications", "Microtech Pty Ltd"),
            ("dyntec.co.bw", "Dyntec Consulting", "Dyntec Pty Ltd"),
            ("atvantage.co.bw", "Atvantage Broadband", "Atvantage Pty Ltd"),
            ("wiless.co.bw", "Wiless Networks", "Wiless Communications Ltd"),
            # Banks & Finance
            ("fnb.co.bw", "First National Bank Botswana", "FNB Botswana Ltd"),
            ("stanbic.co.bw", "Stanbic Bank Botswana", "Stanbic Bank Botswana Ltd"),
            ("absa.co.bw", "Absa Bank Botswana", "Absa Bank Botswana Ltd"),
            ("standardchartered.co.bw", "Standard Chartered Botswana", "Standard Chartered Bank Botswana"),
            ("bankgaborone.co.bw", "Bank Gaborone", "Bank Gaborone Ltd"),
            ("bankabc.co.bw", "BancABC Botswana", "African Banking Corporation Botswana"),
            ("bsb.co.bw", "Botswana Savings Bank", "BSB Ltd"),
            ("bbs.co.bw", "Botswana Building Society", "BBS Ltd"),
            ("letshego.co.bw", "Letshego Holdings", "Letshego Holdings Ltd"),
            ("bayport.co.bw", "Bayport Financial Services", "Bayport Botswana"),
            ("micropay.co.bw", "MicroPay Solutions", "MicroPay Pty Ltd"),
            ("myzaka.co.bw", "MyZaka Mobile Money", "MyZaka Pty Ltd"),
            ("bse.co.bw", "Botswana Stock Exchange", "BSE Ltd"),
            ("csdb.co.bw", "Central Securities Depository", "CSDB Botswana"),
            ("nbfira.co.bw", "NBFIRA", "Non-Bank Financial Institutions Regulatory Authority"),
            # Insurance
            ("hollard.co.bw", "Hollard Insurance Botswana", "Hollard Insurance Co Botswana"),
            ("botswanalife.co.bw", "Botswana Life Insurance", "Botswana Life Insurance Ltd"),
            ("botswanainsurance.co.bw", "Botswana Insurance Company", "BIHL Group"),
            ("metropolitan.co.bw", "Metropolitan Botswana", "Metropolitan Life Botswana"),
            ("zurich.co.bw", "Zurich Insurance Botswana", "Zurich Insurance Pty Ltd"),
            # Retail & Commerce
            ("choppies.co.bw", "Choppies Enterprises", "Choppies Enterprises Ltd"),
            ("sefalana.co.bw", "Sefalana Group", "Sefalana Holding Company Ltd"),
            ("payless.co.bw", "Pay Less Supermarkets", "Pay Less Stores Pty Ltd"),
            ("spar.co.bw", "SPAR Botswana", "SPAR Group Botswana"),
            ("shoprite.co.bw", "Shoprite Botswana", "Shoprite Holdings Botswana"),
            ("picknpay.co.bw", "Pick n Pay Botswana", "Pick n Pay Stores Botswana"),
            ("woolworths.co.bw", "Woolworths Botswana", "Woolworths Holdings Botswana"),
            ("game.co.bw", "Game Stores Botswana", "Massmart Botswana"),
            ("builders.co.bw", "Builders Warehouse Botswana", "Builders Express Botswana"),
            ("cashbuild.co.bw", "Cashbuild Botswana", "Cashbuild Pty Ltd"),
            ("furnmart.co.bw", "Furnmart", "Furnmart Pty Ltd"),
            ("russells.co.bw", "Russells Furnishers", "Russells Botswana Pty Ltd"),
            ("ellerines.co.bw", "Ellerines Holdings", "Ellerines Botswana"),
            # Mining & Resources
            ("debswana.co.bw", "Debswana Diamond Company", "Debswana Diamond Company Pty Ltd"),
            ("debeers.co.bw", "De Beers Botswana", "De Beers Holdings Botswana"),
            ("bcl.co.bw", "BCL Limited", "Bamangwato Concessions Ltd"),
            ("morupule.co.bw", "Morupule Coal Mine", "Morupule Coal Mine Ltd"),
            ("lucara.co.bw", "Lucara Diamond Corp", "Lucara Botswana Pty Ltd"),
            ("minergy.co.bw", "Minergy Limited", "Minergy Ltd"),
            ("gem.co.bw", "Gem Diamonds Botswana", "Gem Diamonds Botswana Pty Ltd"),
            ("sandfire.co.bw", "Sandfire Resources Botswana", "Sandfire Resources Pty Ltd"),
            ("tlou.co.bw", "Tlou Energy", "Tlou Energy Botswana"),
            ("botash.co.bw", "Botswana Ash", "Botash Pty Ltd"),
            # Tourism & Hospitality
            ("belmond.co.bw", "Belmond Safaris Botswana", "Belmond Ltd Botswana"),
            ("andBeyond.co.bw", "andBeyond Botswana", "andBeyond Expeditions Pty Ltd"),
            ("desertdelta.co.bw", "Desert & Delta Safaris", "Desert & Delta Safaris Pty Ltd"),
            ("wilderness.co.bw", "Wilderness Safaris Botswana", "Wilderness Safaris Pty Ltd"),
            ("orient.co.bw", "Orient Express Safaris", "Orient Safaris Pty Ltd"),
            ("sanctuary.co.bw", "Sanctuary Retreats Botswana", "Sanctuary Retreats"),
            ("kwando.co.bw", "Kwando Safaris", "Kwando Safaris Pty Ltd"),
            ("undercanvas.co.bw", "Under Canvas Botswana", "Under Canvas Safaris"),
            ("okavangodelta.co.bw", "Okavango Delta Safaris", "OD Safaris Pty Ltd"),
            ("makgadikgadi.co.bw", "Makgadikgadi Adventures", "Makgadikgadi Tours Pty Ltd"),
            ("sunsetlodge.co.bw", "Sunset Lodge Gaborone", "Sunset Hospitality Pty Ltd"),
            ("crecsenthotel.co.bw", "Crescent Hotel Francistown", "Crescent Hotels BW"),
            ("gaboronehotel.co.bw", "Gaborone Hotel", "Gaborone Hotel Ltd"),
            ("grandpalm.co.bw", "Grand Palm Hotel", "Peermont Botswana"),
            ("avanihotel.co.bw", "Avani Gaborone", "Minor Hotels Botswana"),
            ("travelwise.co.bw", "Travelwise Botswana", "Travelwise Pty Ltd"),
            # Agriculture & Food
            ("bmc.co.bw", "Botswana Meat Commission", "BMC"),
            ("senn.co.bw", "Senn Foods", "Senn Holdings Pty Ltd"),
            ("farmfresh.co.bw", "Farm Fresh Botswana", "Farm Fresh Produce Pty Ltd"),
            ("kalaharibrew.co.bw", "Kalahari Brew", "Kalahari Brewing Co"),
            ("botswanacreameries.co.bw", "Botswana Creameries", "Botswana Dairy"),
            ("bolux.co.bw", "Bolux Milling", "Bolux Group Pty Ltd"),
            ("seedco.co.bw", "SeedCo Botswana", "SeedCo International BW"),
            ("stc.co.bw", "STC Botswana", "Steel and Timber Construction"),
            # Automotive
            ("toyota.co.bw", "Toyota Botswana", "Toyota Botswana Pty Ltd"),
            ("ford.co.bw", "Ford Botswana", "Ford Motor Company Botswana"),
            ("nissan.co.bw", "Nissan Botswana", "Nissan SA Botswana"),
            ("hyundai.co.bw", "Hyundai Botswana", "Hyundai Automotive Botswana"),
            ("bmw.co.bw", "BMW Botswana", "BMW Group Botswana Pty Ltd"),
            ("mercedes.co.bw", "Mercedes-Benz Botswana", "Mercedes-Benz SA Botswana"),
            ("motovac.co.bw", "Motovac Botswana", "Motovac"),
            ("autoworld.co.bw", "Auto World", "Auto World Pty Ltd"),
            # Construction & Property
            ("wbho.co.bw", "WBHO Botswana", "WBHO Construction Botswana"),
            ("ccc.co.bw", "China Civil Construction", "CCC Botswana"),
            ("mota.co.bw", "Mota-Engil Botswana", "Mota-Engil Africa BW"),
            ("realestate.co.bw", "Real Estate Botswana", "RE Botswana Holdings"),
            ("knightfrank.co.bw", "Knight Frank Botswana", "Knight Frank Pty Ltd"),
            ("pamgolding.co.bw", "Pam Golding Botswana", "Pam Golding Properties BW"),
            ("landboard.co.bw", "Land Board Services", "Land Board Services Pty Ltd"),
            ("propconsult.co.bw", "Property Consultants", "ProConsult BW Pty Ltd"),
            # Legal
            ("armstrongs.co.bw", "Armstrongs Attorneys", "Armstrongs Attorneys"),
            ("collins.co.bw", "Collins Newman & Co", "Collins Newman Attorneys"),
            ("akhilmohan.co.bw", "Akhil Mohan Attorneys", "Akhil Mohan & Associates"),
            ("bogopa.co.bw", "Bogopa Manewe & Associates", "Bogopa Manewe Attorneys"),
            ("desai.co.bw", "Desai Law Group", "Desai Law Group Botswana"),
            ("luke.co.bw", "Luke & Associates", "Luke & Associates"),
            # IT & Tech
            ("ict.co.bw", "ICT Solutions Botswana", "ICT Solutions Pty Ltd"),
            ("xpert.co.bw", "Xpert Technologies", "Xpert Tech Solutions"),
            ("nimbus.co.bw", "Nimbus Technologies", "Nimbus Infrastructure BW"),
            ("compu.co.bw", "CompuTech Botswana", "CompuTech Pty Ltd"),
            ("techbw.co.bw", "TechBW Services", "TechBW Pty Ltd"),
            ("bytes.co.bw", "Bytes Technology", "Bytes Technology Group BW"),
            ("cloudbw.co.bw", "CloudBW Solutions", "CloudBW Pty Ltd"),
            ("digital.co.bw", "Digital Botswana", "Digital Innovations Pty Ltd"),
            ("bitri.co.bw", "BITRI Technologies", "BITRI Commercial Arm"),
            ("innobw.co.bw", "Innovation Hub BW", "InNovaBW Pty Ltd"),
            # Logistics & Transport
            ("airbtw.co.bw", "Air Botswana", "Air Botswana Pty Ltd"),
            ("worldfreight.co.bw", "World Freight Botswana", "World Freight BW Pty Ltd"),
            ("unitrans.co.bw", "Unitrans Botswana", "Unitrans Supply Chain Solutions"),
            ("dhl.co.bw", "DHL Botswana", "DHL Express Botswana"),
            ("fedex.co.bw", "FedEx Botswana", "FedEx Africa Botswana"),
            ("bollore.co.bw", "Bollore Transport Botswana", "Bollore Africa Logistics"),
            # Health & Pharma
            ("medrescue.co.bw", "Medical Rescue International", "MRI Botswana"),
            ("gphl.co.bw", "Gaborone Private Hospital", "Life Healthcare Botswana"),
            ("bokamoso.co.bw", "Bokamoso Private Hospital", "Bokamoso Holdings"),
            ("clicks.co.bw", "Clicks Botswana", "Clicks Group Botswana"),
            ("dischempharmacy.co.bw", "Dis-Chem Botswana", "Dis-Chem Pharmacies BW"),
            ("healthwise.co.bw", "HealthWise Pharmacy", "HealthWise Pty Ltd"),
            # Media & Advertising
            ("btv.co.bw", "Botswana Television", "BTV Commercial"),
            ("yarona.co.bw", "Yarona FM", "Yarona Broadcasting"),
            ("duma.co.bw", "Duma FM", "Duma Broadcasting Pty Ltd"),
            ("gabz.co.bw", "Gabz FM", "Gabz Broadcasting Pty Ltd"),
            ("mmegi.co.bw", "Mmegi Newspaper", "Dikgang Publishing Company"),
            ("thepatriot.co.bw", "The Patriot Newspaper", "Patriot Media Pty Ltd"),
            ("sundaystandard.co.bw", "Sunday Standard", "Botswana Standard Media"),
            ("monitor.co.bw", "The Monitor", "Monitor Media Botswana"),
            ("voice.co.bw", "The Voice Newspaper", "The Voice Media Group"),
            ("advertise.co.bw", "Advertise Botswana", "Ad Solutions Pty Ltd"),
            ("multichoice.co.bw", "MultiChoice Botswana", "MultiChoice Botswana Pty Ltd"),
            # Energy & Utilities
            ("bpc.co.bw", "Botswana Power Corporation", "BPC"),
            ("wuc.co.bw", "Water Utilities Corporation", "WUC"),
            ("solarbw.co.bw", "Solar Botswana", "Solar Energy Solutions BW"),
            ("engen.co.bw", "Engen Botswana", "Engen Botswana Pty Ltd"),
            ("puma.co.bw", "Puma Energy Botswana", "Puma Energy BW"),
            ("shell.co.bw", "Shell Botswana", "Shell Botswana BV"),
            ("galp.co.bw", "Galp Energy Botswana", "Galp Energia Botswana"),
            # Education (commercial)
            ("gips.co.bw", "Gaborone International Private School", "GIPS Ltd"),
            ("maru.co.bw", "Maru-a-Pula School", "Maru-a-Pula Trust"),
            ("legae.co.bw", "Legae Academy", "Legae Academy Trust"),
            ("westwood.co.bw", "Westwood International", "Westwood International School"),
            # Manufacturing
            ("kgalagadi.co.bw", "Kgalagadi Breweries", "Kgalagadi Breweries Ltd"),
            ("ppc.co.bw", "PPC Botswana", "PPC Cement Botswana"),
            ("coca-cola.co.bw", "Coca-Cola Botswana", "Coca-Cola Beverages Botswana"),
            ("natfood.co.bw", "National Foods Botswana", "NatFoods BW Pty Ltd"),
            # Consulting
            ("kpmg.co.bw", "KPMG Botswana", "KPMG Advisory Services"),
            ("deloitte.co.bw", "Deloitte Botswana", "Deloitte & Touche Botswana"),
            ("ey.co.bw", "Ernst & Young Botswana", "EY Botswana"),
            ("pwc.co.bw", "PwC Botswana", "PricewaterhouseCoopers Botswana"),
            ("grantthornton.co.bw", "Grant Thornton Botswana", "Grant Thornton BW"),
            ("mazars.co.bw", "Mazars Botswana", "Mazars Advisory BW"),
            # Various commercial
            ("rangelands.co.bw", "Rangelands Trading", "Rangelands Pty Ltd"),
            ("tshipidi.co.bw", "Tshipidi Group", "Tshipidi Investments Pty Ltd"),
            ("bwi.co.bw", "Botswana Insurance Holdings", "BWI Group"),
            ("tati.co.bw", "Tati Nickel Mining", "Tati Nickel Mining Company"),
            ("marumo.co.bw", "Marumo Investments", "Marumo Capital"),
            ("motswedi.co.bw", "Motswedi Securities", "Motswedi Securities Pty Ltd"),
            ("imara.co.bw", "Imara Capital", "Imara Capital Botswana"),
            ("afroasia.co.bw", "AfroAsia Bank", "AfroAsia Botswana"),
            ("dentist.co.bw", "Gaborone Dental Clinic", "GDC Pty Ltd"),
            ("optibw.co.bw", "Opti Botswana", "Opti Health BW"),
            ("netcare.co.bw", "Netcare Botswana", "Netcare Group BW"),
            ("safari.co.bw", "Safari Centre Mall", "Safari Centre Properties"),
            ("riverwalk.co.bw", "Riverwalk Mall", "Riverwalk Properties"),
            ("gamecentre.co.bw", "Game City Mall", "Game City Properties"),
            ("railpark.co.bw", "Rail Park Mall", "Rail Park Properties"),
            ("airport.co.bw", "Airport Junction Mall", "Airport Junction Properties"),
            ("molapo.co.bw", "Molapo Crossing Mall", "Molapo Properties BW"),
            ("setlhoa.co.bw", "Setlhoa Village", "Setlhoa Dev Pty Ltd"),
            ("tlokweng.co.bw", "Tlokweng Properties", "Tlokweng Dev Pty Ltd"),
            ("phakalane.co.bw", "Phakalane Golf Estate", "Phakalane Property Developers"),
            ("parceldel.co.bw", "Parcel Delivery BW", "ParcelDel Pty Ltd"),
            ("hirecar.co.bw", "Hire Car Botswana", "HireCar BW Pty Ltd"),
            ("budget.co.bw", "Budget Car Rental BW", "Budget Rent A Car BW"),
            ("avis.co.bw", "Avis Botswana", "Avis Rent A Car Botswana"),
            ("europcar.co.bw", "Europcar Botswana", "Europcar Botswana Pty Ltd"),
            ("hertz.co.bw", "Hertz Botswana", "Hertz Rent A Car BW"),
            ("totalenergy.co.bw", "TotalEnergies Botswana", "TotalEnergies Marketing BW"),
            ("caterplus.co.bw", "CaterPlus Catering Services", "CaterPlus Pty Ltd"),
            ("events.co.bw", "Events Botswana", "Events Management BW Pty Ltd"),
            ("prints.co.bw", "Print Solutions Botswana", "PrintSol Pty Ltd"),
            ("security.co.bw", "G4S Botswana", "G4S Security Services BW"),
            ("cleaning.co.bw", "CleanServe Botswana", "CleanServe Pty Ltd"),
            ("courier.co.bw", "Sprint Couriers", "Sprint Couriers Botswana"),
            ("waste.co.bw", "Waste Management BW", "WM Botswana Pty Ltd"),
            ("greentech.co.bw", "GreenTech Solutions", "GreenTech Environmental BW"),
            ("powergen.co.bw", "PowerGen Botswana", "PowerGen BW Pty Ltd"),
            ("jewel.co.bw", "Jewel of Africa", "Jewel Trading Pty Ltd"),
            ("diamond.co.bw", "Diamond Trading BW", "Diamond Hub Botswana"),
            ("okavango.co.bw", "Okavango Diamond Company", "ODC Pty Ltd"),
            ("fireblade.co.bw", "Fireblade Aviation", "Fireblade BW"),
            ("datamine.co.bw", "DataMine Analytics", "DataMine Pty Ltd"),
            ("agritech.co.bw", "AgriTech Botswana", "AgriTech Solutions BW"),
            ("sunpower.co.bw", "SunPower Botswana", "SunPower Solar BW"),
            ("motho.co.bw", "Motho Consulting", "Motho Consulting Pty Ltd"),
            ("thuso.co.bw", "Thuso HR Solutions", "Thuso Group Pty Ltd"),
            ("peo.co.bw", "Peo Micro Lending", "Peo Pty Ltd"),
            ("mhealth.co.bw", "mHealth Botswana", "mHealth Technologies BW"),
            ("fintech.co.bw", "FinTech Botswana", "FinTech Innovations Pty Ltd"),
            ("gasup.co.bw", "GasUp Botswana", "GasUp Pty Ltd"),
            ("housemart.co.bw", "HouseMart Hardware", "HouseMart Pty Ltd"),
            ("craftbw.co.bw", "CraftBW Artisans Market", "CraftBW Pty Ltd"),
            ("fashionbw.co.bw", "FashionBW", "FashionBW Pty Ltd"),
            ("mealmasters.co.bw", "Meal Masters Catering", "Meal Masters Pty Ltd"),
            ("fitnessfirst.co.bw", "Fitness First Gaborone", "Fitness First BW"),
            ("motse.co.bw", "Motse Marketing", "Motse Agency Pty Ltd"),
            ("tumo.co.bw", "Tumo Centre Botswana", "Tumo BW Trust"),
            ("nandos.co.bw", "Nando's Botswana", "Nandos Botswana Pty Ltd"),
            ("debonairs.co.bw", "Debonairs Pizza BW", "Debonairs BW Pty Ltd"),
            ("steers.co.bw", "Steers Botswana", "Steers BW Pty Ltd"),
            ("kfc.co.bw", "KFC Botswana", "Yum Brands Botswana"),
        ]

        # ── .org.bw domains (~80) ────────────────────────────────────────────
        org_bw_entries = [
            ("boccim.org.bw", "Botswana Confederation of Commerce", "BOCCIM"),
            ("bedia.org.bw", "Botswana Export Development", "BEDIA"),
            ("hatab.org.bw", "Hospitality & Tourism Association", "HATAB"),
            ("boccim.org.bw", "BOCCIM", "Botswana Confederation of Commerce Industry and Manpower"),
            ("botswanaredcross.org.bw", "Botswana Red Cross Society", "Red Cross BW"),
            ("cancerbw.org.bw", "Cancer Association of Botswana", "Cancer Association"),
            ("cwc.org.bw", "Council for Women of Botswana", "CWC"),
            ("stepsbw.org.bw", "STEPS Centre Botswana", "STEPS BW Trust"),
            ("ditshwanelo.org.bw", "Ditshwanelo Human Rights Centre", "Ditshwanelo"),
            ("bonela.org.bw", "Botswana Network on Ethics", "BONELA"),
            ("achap.org.bw", "African Comprehensive HIV Initiative", "ACHAP"),
            ("naca.org.bw", "National AIDS Coordinating Agency", "NACA"),
            ("bocongo.org.bw", "Botswana Council of NGOs", "BOCONGO"),
            ("youthbw.org.bw", "Botswana Youth Council", "NYC"),
            ("bfa.org.bw", "Botswana Football Association", "BFA"),
            ("bba.org.bw", "Botswana Basketball Association", "BBA"),
            ("cricket.org.bw", "Cricket Botswana", "BCB"),
            ("rugby.org.bw", "Botswana Rugby Union", "BRU"),
            ("athletics.org.bw", "Botswana Athletics Association", "BAA"),
            ("netball.org.bw", "Botswana Netball Association", "BNA"),
            ("chess.org.bw", "Botswana Chess Federation", "BCF"),
            ("karate.org.bw", "Botswana Karate Association", "BKA"),
            ("swimming.org.bw", "Aquatics Botswana", "Aquatics BW"),
            ("bnoc.org.bw", "Botswana National Olympic Committee", "BNOC"),
            ("bnsc.org.bw", "Botswana National Sports Council", "BNSC"),
            ("bpopf.org.bw", "Botswana Public Officers Pension Fund", "BPOPF"),
            ("debswanafund.org.bw", "Debswana Foundation", "Debswana Trust"),
            ("kwalabw.org.bw", "Kwala Foundation", "Kwala Foundation"),
            ("lichaba.org.bw", "Lichaba Foundation", "Lichaba Trust"),
            ("childline.org.bw", "Childline Botswana", "Childline BW"),
            ("ywca.org.bw", "YWCA Botswana", "YWCA BW"),
            ("botswanascouts.org.bw", "Botswana Scouts", "BSA"),
            ("girlguides.org.bw", "Girl Guides Botswana", "GG BW"),
            ("sosaids.org.bw", "SOS Children's Villages", "SOS BW"),
            ("habitat.org.bw", "Habitat for Humanity Botswana", "HFHB"),
            ("medicalaid.org.bw", "Medical Aid Botswana", "MABW Trust"),
            ("blindpeople.org.bw", "Botswana Council for the Blind", "BCB"),
            ("deafbw.org.bw", "Botswana Society for the Deaf", "BSD"),
            ("cheshirebw.org.bw", "Cheshire Foundation Botswana", "Cheshire BW"),
            ("wildlifebw.org.bw", "Wildlife Conservation BW", "WCB Trust"),
            ("elephants.org.bw", "Elephants Without Borders", "EWB"),
            ("rhinos.org.bw", "Rhino Conservation Botswana", "RCB"),
            ("birdlife.org.bw", "BirdLife Botswana", "BirdLife BW"),
            ("kalahari.org.bw", "Kalahari Conservation Society", "KCS"),
            ("mokolobw.org.bw", "Mokolo Trust", "Mokolo Conservation"),
            ("farmersunion.org.bw", "Botswana Farmers Union", "BFU"),
            ("pastors.org.bw", "Botswana Council of Churches", "BCC"),
            ("lutheran.org.bw", "Evangelical Lutheran Church", "ELCB"),
            ("methodist.org.bw", "Methodist Church Botswana", "MCB"),
            ("catholic.org.bw", "Catholic Diocese of Gaborone", "CDG"),
            ("uccsa.org.bw", "UCCSA Botswana", "UCCSA"),
            ("architects.org.bw", "Architects Association of Botswana", "AAB"),
            ("engineers.org.bw", "Botswana Institution of Engineers", "BIE"),
            ("accountants.org.bw", "Botswana Institute of Accountants", "BIA"),
            ("lawsociety.org.bw", "Law Society of Botswana", "LSB"),
            ("doctorsbw.org.bw", "Botswana Medical Association", "BMA"),
            ("nurses.org.bw", "Nurses Association of Botswana", "NAB"),
            ("teachers.org.bw", "Botswana Teachers Union", "BTU"),
            ("btu.org.bw", "BTU", "Botswana Teachers Union"),
            ("batu.org.bw", "Botswana Agricultural Workers", "BATU"),
            ("bomu.org.bw", "Botswana Mine Workers Union", "BMWU"),
            ("sewa.org.bw", "Self Employed Women Association", "SEWA BW"),
            ("transparency.org.bw", "Transparency International BW", "TI Botswana"),
            ("lssa.org.bw", "Legal Aid Botswana", "LSSA BW"),
            ("ngamiland.org.bw", "Ngamiland Council Trust", "NCT"),
            ("chobe.org.bw", "Chobe Wildlife Trust", "CWT"),
            ("mediacouncil.org.bw", "Press Council of Botswana", "MISA BW"),
            ("youthempowerment.org.bw", "Youth Empowerment BW", "YEBW"),
            ("greenaction.org.bw", "Green Action Botswana", "GABW"),
            ("womenempowerment.org.bw", "Women Empowerment Botswana", "WEBW"),
            ("humanrights.org.bw", "Human Rights BW", "HRBW"),
            ("literacy.org.bw", "Literacy Association BW", "LABW"),
            ("artsbw.org.bw", "National Arts Council", "NACBW"),
            ("heritage.org.bw", "Heritage Foundation BW", "HFBW"),
            ("sanitation.org.bw", "Sanitation & Water Botswana", "SWBW"),
            ("volunteer.org.bw", "Volunteer Botswana", "VBW"),
            ("disabilitybw.org.bw", "Disability Rights BW", "DRBW"),
        ]

        # ── .gov.bw domains (~60) ────────────────────────────────────────────
        gov_bw_entries = [
            ("gov.bw", "Government of Botswana Portal", "Republic of Botswana"),
            ("parliament.gov.bw", "Parliament of Botswana", "National Assembly"),
            ("president.gov.bw", "Office of the President", "OP"),
            ("mofed.gov.bw", "Ministry of Finance", "MOFED"),
            ("miti.gov.bw", "Ministry of Trade and Industry", "MITI"),
            ("mlgrd.gov.bw", "Ministry of Local Government", "MLGRD"),
            ("moe.gov.bw", "Ministry of Education", "MOE"),
            ("moh.gov.bw", "Ministry of Health", "MOH"),
            ("mod.gov.bw", "Ministry of Defence", "MOD"),
            ("mofa.gov.bw", "Ministry of Foreign Affairs", "MOFA"),
            ("mjds.gov.bw", "Ministry of Justice", "MJDS"),
            ("mlws.gov.bw", "Ministry of Lands and Water", "MLWS"),
            ("mmewa.gov.bw", "Ministry of Minerals and Water", "MMEWA"),
            ("moa.gov.bw", "Ministry of Agriculture", "MOA"),
            ("mysc.gov.bw", "Ministry of Youth & Sports", "MYSC"),
            ("met.gov.bw", "Ministry of Environment & Tourism", "MET"),
            ("mtc.gov.bw", "Ministry of Transport & Comms", "MTC"),
            ("mle.gov.bw", "Ministry of Labour", "MLE"),
            ("mee.gov.bw", "Ministry of Entrepreneurship", "MEE"),
            ("bocra.gov.bw", "BOCRA", "Botswana Communications Regulatory Authority"),
            ("bnpc.gov.bw", "Botswana National Productivity Centre", "BNPC"),
            ("cipa.gov.bw", "Companies & Intellectual Property Authority", "CIPA"),
            ("burs.gov.bw", "Botswana Unified Revenue Service", "BURS"),
            ("bobs.gov.bw", "Bank of Botswana", "Bank of Botswana"),
            ("cso.gov.bw", "Central Statistics Office", "CSO"),
            ("dpp.gov.bw", "Directorate of Public Prosecutions", "DPP"),
            ("dcec.gov.bw", "Directorate on Corruption", "DCEC"),
            ("dis.gov.bw", "Directorate of Intelligence & Security", "DIS"),
            ("bps.gov.bw", "Botswana Police Service", "BPS"),
            ("bdf.gov.bw", "Botswana Defence Force", "BDF"),
            ("prisons.gov.bw", "Botswana Prison Service", "BPS"),
            ("fire.gov.bw", "Botswana Fire Service", "BFS"),
            ("immigration.gov.bw", "Department of Immigration", "DOI"),
            ("civilaviation.gov.bw", "Civil Aviation Authority BW", "CAAB"),
            ("roads.gov.bw", "Department of Roads", "DOR"),
            ("bes.gov.bw", "Botswana Energy Sector", "BES"),
            ("ndb.gov.bw", "National Development Bank", "NDB"),
            ("bdc.gov.bw", "Botswana Development Corporation", "BDC"),
            ("bitc.gov.bw", "Botswana Investment & Trade Centre", "BITC"),
            ("lea.gov.bw", "Local Enterprise Authority", "LEA"),
            ("ceda.gov.bw", "Citizen Entrepreneurial Development Agency", "CEDA"),
            ("dbes.gov.bw", "Department of Broadcasting", "DBES"),
            ("bnm.gov.bw", "Botswana National Museum", "BNM"),
            ("bnl.gov.bw", "Botswana National Library", "BNL"),
            ("bnab.gov.bw", "Botswana National Archives", "BNAB"),
            ("gaboronecity.gov.bw", "Gaborone City Council", "GCC"),
            ("francistowncity.gov.bw", "Francistown City Council", "FCC"),
            ("selibephikwe.gov.bw", "Selebi-Phikwe Council", "SPC"),
            ("lobatse.gov.bw", "Lobatse Town Council", "LTC"),
            ("jwaneng.gov.bw", "Jwaneng Town Council", "JTC"),
            ("kasane.gov.bw", "Kasane Township Authority", "KTA"),
            ("maun.gov.bw", "Maun Admin Authority", "MAA"),
            ("letlhakane.gov.bw", "Letlhakane Sub District", "LSD"),
            ("kanye.gov.bw", "Kanye Admin Authority", "KAA"),
            ("molepolole.gov.bw", "Molepolole Admin Authority", "MAA"),
            ("palapye.gov.bw", "Palapye Admin Authority", "PAA"),
            ("serowe.gov.bw", "Serowe Admin Authority", "SAA"),
            ("elections.gov.bw", "Independent Electoral Commission", "IEC"),
            ("ombudsman.gov.bw", "Ombudsman Botswana", "OMB"),
        ]

        # ── .ac.bw domains (~30) ─────────────────────────────────────────────
        ac_bw_entries = [
            ("ub.ac.bw", "University of Botswana", "University of Botswana"),
            ("biust.ac.bw", "BIUST", "Botswana International Uni of Science & Technology"),
            ("bou.ac.bw", "Botswana Open University", "BOU"),
            ("buan.ac.bw", "Botswana University of Agriculture", "BUAN"),
            ("limkokwing.ac.bw", "Limkokwing University", "Limkokwing University Botswana"),
            ("abm.ac.bw", "ABM University College", "ABM University College"),
            ("baisago.ac.bw", "BA ISAGO University", "BA ISAGO University"),
            ("botho.ac.bw", "Botho University", "Botho University"),
            ("gips.ac.bw", "Gaborone Institute of Professional Studies", "GIPS"),
            ("bca.ac.bw", "Botswana College of Agriculture", "BCA"),
            ("idt.ac.bw", "Institute of Development Management", "IDM"),
            ("bac.ac.bw", "Botswana Accountancy College", "BAC"),
            ("bithc.ac.bw", "Baisago Institute of Health", "BITHC"),
            ("naca.ac.bw", "National Ambulance College", "NAC"),
            ("tvet.ac.bw", "TVET Botswana", "TVET Council"),
            ("madirelo.ac.bw", "Madirelo Training & Testing Centre", "MTTC"),
            ("oodi.ac.bw", "Oodi College of Applied Technology", "OCAT"),
            ("francistown.ac.bw", "Francistown College of Technology", "FCTE"),
            ("maun.ac.bw", "Maun Technical College", "MTC"),
            ("shashe.ac.bw", "Shashe River School", "SRS"),
            ("legae.ac.bw", "Legae Academy", "Legae Academy"),
            ("westwood.ac.bw", "Westwood International School", "WIS"),
            ("maru.ac.bw", "Maru-a-Pula School", "MAPS"),
            ("northside.ac.bw", "Northside Primary School", "NPS"),
            ("thornhill.ac.bw", "Thornhill Primary School", "TPS"),
            ("broadhurst.ac.bw", "Broadhurst Primary School", "BPS"),
            ("mcps.ac.bw", "Maun Community Primary School", "MCPS"),
            ("ghs.ac.bw", "Gaborone High School", "GHS"),
            ("moeding.ac.bw", "Moeding College", "Moeding College"),
            ("mater.ac.bw", "Mater Spei College", "Mater Spei"),
        ]

        # ── .net.bw domains (~30) ────────────────────────────────────────────
        net_bw_entries = [
            ("info.net.bw", "Information Systems BW", "InfoSys BW Pty Ltd"),
            ("mega.net.bw", "Mega Internet", "Mega Internet Services"),
            ("iway.net.bw", "iWay Africa Botswana", "iWay BW"),
            ("cafenet.net.bw", "CafeNet Botswana", "CafeNet BW"),
            ("opennet.net.bw", "OpenNet Botswana", "OpenNet Infrastructure"),
            ("datagrid.net.bw", "DataGrid Botswana", "DataGrid BW Pty Ltd"),
            ("fibre.net.bw", "Fibre Solutions BW", "FibreBW Pty Ltd"),
            ("netflow.net.bw", "NetFlow Botswana", "NetFlow Comms Pty Ltd"),
            ("skynet.net.bw", "SkyNet Wireless", "SkyNet BW Pty Ltd"),
            ("webhost.net.bw", "WebHost Botswana", "WebHost BW Pty Ltd"),
            ("hosting.net.bw", "Hosting Botswana", "Hosting BW Pty Ltd"),
            ("serverroom.net.bw", "ServerRoom BW", "ServerRoom Pty Ltd"),
            ("peering.net.bw", "BINX Peering Exchange", "BINX"),
            ("dns.net.bw", "DNS Botswana", "DNS Services BW"),
            ("vpn.net.bw", "VPN Solutions Botswana", "VPN BW Pty Ltd"),
            ("cloud.net.bw", "Cloud Services Botswana", "Cloud BW Pty Ltd"),
            ("connect.net.bw", "Connect Botswana", "Connect BW Pty Ltd"),
            ("wifizone.net.bw", "WiFi Zone BW", "WiFiZone Pty Ltd"),
            ("fastlink.net.bw", "FastLink Networks", "FastLink BW Pty Ltd"),
            ("gateway.net.bw", "Gateway Botswana", "Gateway Communications"),
            ("afrihost.net.bw", "Afrihost Botswana", "Afrihost BW"),
            ("cyberbw.net.bw", "CyberBW", "CyberBW Security"),
            ("technet.net.bw", "TechNet BW", "TechNet Pty Ltd"),
            ("broadband.net.bw", "Broadband Botswana", "Broadband BW Pty Ltd"),
            ("linkafrica.net.bw", "LinkAfrica BW", "LinkAfrica Pty Ltd"),
            ("netwise.net.bw", "NetWise Botswana", "NetWise Pty Ltd"),
            ("digilink.net.bw", "DigiLink BW", "DigiLink Pty Ltd"),
            ("pixelnet.net.bw", "PixelNet Botswana", "PixelNet BW"),
            ("securenet.net.bw", "SecureNet BW", "SecureNet Pty Ltd"),
            ("bitstream.net.bw", "BitStream Botswana", "BitStream BW Pty Ltd"),
        ]

        # ── .bw direct domains (~20) ─────────────────────────────────────────
        bw_direct_entries = [
            ("botswana.bw", "Botswana Portal", "Republic of Botswana"),
            ("diamond.bw", "Botswana Diamonds", "Botswana Diamond Hub"),
            ("safari.bw", "Safari Botswana", "Safari BW Brand"),
            ("kalahari.bw", "Kalahari Botswana", "Kalahari Brand BW"),
            ("okavango.bw", "Okavango Delta", "Okavango Brand BW"),
            ("chobe.bw", "Chobe National Park", "Chobe Brand BW"),
            ("mascom.bw", "Mascom Premium", "Mascom Wireless"),
            ("orange.bw", "Orange Premium", "Orange Botswana"),
            ("btc.bw", "BTC Premium", "BTC Limited"),
            ("fnb.bw", "FNB Premium", "FNB Botswana"),
            ("debswana.bw", "Debswana Premium", "Debswana"),
            ("sefalana.bw", "Sefalana Premium", "Sefalana Holdings"),
            ("choppies.bw", "Choppies Premium", "Choppies Enterprises"),
            ("letshego.bw", "Letshego Premium", "Letshego Holdings"),
            ("bocra.bw", "BOCRA Premium", "BOCRA"),
            ("invest.bw", "Invest Botswana", "Investment BW"),
            ("travel.bw", "Travel Botswana", "Travel BW Brand"),
            ("trade.bw", "Trade Botswana", "Trade BW Brand"),
            ("health.bw", "Health Botswana", "Health BW Brand"),
            ("edu.bw", "Education Botswana", "Education BW Brand"),
        ]

        # Map zone code to entries and zone suffix
        zone_entries = {
            "CO_BW":  (co_bw_entries, ".co.bw"),
            "ORG_BW": (org_bw_entries, ".org.bw"),
            "GOV_BW": (gov_bw_entries, ".gov.bw"),
            "AC_BW":  (ac_bw_entries, ".ac.bw"),
            "NET_BW": (net_bw_entries, ".net.bw"),
            "BW":     (bw_direct_entries, ".bw"),
        }

        now = timezone.now()
        nameservers = [
            ("ns1.bofinet.bw", "ns2.bofinet.bw"),
            ("ns1.mascom.bw", "ns2.mascom.bw"),
            ("ns1.orange.bw", "ns2.orange.bw"),
            ("dns1.liquid.bw", "dns2.liquid.bw"),
            ("ns1.cloudflare.com", "ns2.cloudflare.com"),
            ("ns-1.awsdns.com", "ns-2.awsdns.net"),
            ("ns1.google.com", "ns2.google.com"),
            ("ns1.digitalocean.com", "ns2.digitalocean.com"),
        ]

        cities = [
            "Gaborone", "Francistown", "Maun", "Kasane", "Palapye",
            "Serowe", "Molepolole", "Kanye", "Lobatse", "Jwaneng",
            "Selebi-Phikwe", "Mahalapye", "Mochudi", "Tlokweng",
        ]

        # Status distribution: ~90% ACTIVE, ~5% EXPIRED, ~3% SUSPENDED, ~2% PENDING_DELETE
        def pick_status():
            r = random.random()
            if r < 0.90:
                return DomainStatus.ACTIVE
            elif r < 0.95:
                return DomainStatus.EXPIRED
            elif r < 0.98:
                return DomainStatus.SUSPENDED
            else:
                return DomainStatus.PENDING_DELETE

        all_created = []

        for zone_code, (entries, suffix) in zone_entries.items():
            zone = zones[zone_code]
            seen = set()

            for domain_name, display_name, org_name in entries:
                if domain_name in seen:
                    continue
                seen.add(domain_name)

                if Domain.objects.filter(domain_name=domain_name).exists():
                    continue

                status = pick_status()

                # Registration date: random over the past 15 years
                days_ago = random.randint(30, 15 * 365)
                registered_at = now - timedelta(days=days_ago)

                # Expiry: 1-5 year registration periods
                period_years = random.randint(1, 5)
                expires_at = registered_at + timedelta(days=period_years * 365)

                # If domain status is EXPIRED, ensure expiry is in the past
                if status == DomainStatus.EXPIRED:
                    expires_at = now - timedelta(days=random.randint(1, 180))
                # If status is ACTIVE, ensure expiry is in the future
                elif status == DomainStatus.ACTIVE:
                    if expires_at < now:
                        expires_at = now + timedelta(days=random.randint(30, 3 * 365))

                ns1, ns2 = random.choice(nameservers)
                city = random.choice(cities)

                # Generate realistic contact info
                name_parts = org_name.split()
                contact_first = name_parts[0] if name_parts else "Admin"
                contact_last = name_parts[-1] if len(name_parts) > 1 else "Contact"
                slug = domain_name.split(".")[0]
                email = f"admin@{domain_name}"

                domain = Domain(
                    domain_name=domain_name,
                    zone=zone,
                    status=status,
                    registrant=None,  # seeded domains have no user link
                    registrant_name=f"{contact_first} {contact_last}",
                    registrant_email=email,
                    registrant_phone=f"+267 7{random.randint(1,9)}{random.randint(100000,999999)}",
                    registrant_address=f"Plot {random.randint(100,9999)}, {city}, Botswana",
                    organisation_name=org_name,
                    nameserver_1=ns1,
                    nameserver_2=ns2,
                    nameserver_3="" if random.random() < 0.7 else f"ns3.{slug}.{suffix.lstrip('.')}",
                    nameserver_4="",
                    tech_contact_name=f"{contact_first} IT Department",
                    tech_contact_email=f"tech@{domain_name}",
                    registered_at=registered_at,
                    expires_at=expires_at,
                    last_renewed_at=registered_at + timedelta(days=random.randint(365, days_ago)) if days_ago > 365 and random.random() < 0.5 else None,
                    is_seeded=True,
                )
                all_created.append(domain)

            self.stdout.write(f"  {zone.name}: {len(seen)} domains prepared")

        # Bulk create for performance
        Domain.objects.bulk_create(all_created, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"  Total domains created: {len(all_created)}"))

        return list(Domain.objects.filter(is_seeded=True))

    # ─── EVENTS ───────────────────────────────────────────────────────────────

    def _seed_events(self, domains):
        events = []

        for domain in domains:
            # Every domain gets a REGISTERED event
            events.append(DomainEvent(
                domain=domain,
                event_type=DomainEventType.REGISTERED,
                description=f"Domain {domain.domain_name} registered.",
                performed_by=None,
                metadata={"zone": domain.zone.code, "period_years": 1},
                created_at=domain.registered_at,
            ))

            # If renewed, add a renewal event
            if domain.last_renewed_at:
                events.append(DomainEvent(
                    domain=domain,
                    event_type=DomainEventType.RENEWED,
                    description=f"Domain {domain.domain_name} renewed.",
                    performed_by=None,
                    metadata={"renewed_until": str(domain.expires_at)},
                    created_at=domain.last_renewed_at,
                ))

            # If suspended, add a suspension event
            if domain.status == DomainStatus.SUSPENDED:
                events.append(DomainEvent(
                    domain=domain,
                    event_type=DomainEventType.SUSPENDED,
                    description=f"Domain {domain.domain_name} suspended due to policy violation.",
                    performed_by=None,
                    metadata={"reason": "Policy violation / dispute"},
                ))

            # If expired, add an expiry event
            if domain.status == DomainStatus.EXPIRED:
                events.append(DomainEvent(
                    domain=domain,
                    event_type=DomainEventType.EXPIRED,
                    description=f"Domain {domain.domain_name} expired.",
                    performed_by=None,
                    metadata={"expired_at": str(domain.expires_at)},
                ))

        DomainEvent.objects.bulk_create(events, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"  Total events created: {len(events)}"))

    # ─── APPLICATIONS ─────────────────────────────────────────────────────────

    def _seed_applications(self, zones):
        """Create ~25 domain applications in various statuses."""
        User = self._get_user_model()
        users = list(User.objects.filter(is_active=True)[:10])

        if not users:
            self.stdout.write(self.style.WARNING(
                "  No users found in the database. Skipping application seeding. "
                "Run seed_users first if you want sample applications."
            ))
            return

        staff_users = list(User.objects.filter(role__in=["STAFF", "ADMIN", "SUPERADMIN"])[:5])
        if not staff_users:
            staff_users = users[:1]

        now = timezone.now()
        co_zone = zones.get("CO_BW")
        org_zone = zones.get("ORG_BW")
        net_zone = zones.get("NET_BW")

        # Application templates
        application_data = [
            # DRAFT (4)
            {"domain_name": "startupbw.co.bw", "zone": co_zone, "status": DomainApplicationStatus.DRAFT, "org": "StartupBW Pty Ltd", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "innovate.co.bw", "zone": co_zone, "status": DomainApplicationStatus.DRAFT, "org": "Innovate Botswana", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "greenearth.org.bw", "zone": org_zone, "status": DomainApplicationStatus.DRAFT, "org": "Green Earth Foundation", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "cloudpro.net.bw", "zone": net_zone, "status": DomainApplicationStatus.DRAFT, "org": "CloudPro Networks", "type": DomainApplicationType.REGISTRATION},

            # SUBMITTED (6)
            {"domain_name": "botswanatech.co.bw", "zone": co_zone, "status": DomainApplicationStatus.SUBMITTED, "org": "Botswana Tech Hub", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "safewater.org.bw", "zone": org_zone, "status": DomainApplicationStatus.SUBMITTED, "org": "Safe Water Initiative", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "quicklink.net.bw", "zone": net_zone, "status": DomainApplicationStatus.SUBMITTED, "org": "QuickLink ISP", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "digifarm.co.bw", "zone": co_zone, "status": DomainApplicationStatus.SUBMITTED, "org": "DigiFarm Botswana", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "artscouncil.org.bw", "zone": org_zone, "status": DomainApplicationStatus.SUBMITTED, "org": "Arts Council BW", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "fastnet.net.bw", "zone": net_zone, "status": DomainApplicationStatus.SUBMITTED, "org": "FastNet Botswana", "type": DomainApplicationType.REGISTRATION},

            # UNDER_REVIEW (4)
            {"domain_name": "solarpanels.co.bw", "zone": co_zone, "status": DomainApplicationStatus.UNDER_REVIEW, "org": "Solar Panels BW", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "youthfund.org.bw", "zone": org_zone, "status": DomainApplicationStatus.UNDER_REVIEW, "org": "Youth Development Fund", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "datacenter.net.bw", "zone": net_zone, "status": DomainApplicationStatus.UNDER_REVIEW, "org": "DataCenter Botswana", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "petfood.co.bw", "zone": co_zone, "status": DomainApplicationStatus.UNDER_REVIEW, "org": "PetFood Botswana", "type": DomainApplicationType.REGISTRATION},

            # INFO_REQUESTED (2)
            {"domain_name": "evcharge.co.bw", "zone": co_zone, "status": DomainApplicationStatus.INFO_REQUESTED, "org": "EV Charging Network BW", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "medaid.org.bw", "zone": org_zone, "status": DomainApplicationStatus.INFO_REQUESTED, "org": "Medical Aid Society", "type": DomainApplicationType.REGISTRATION},

            # APPROVED (5)
            {"domain_name": "swiftpay.co.bw", "zone": co_zone, "status": DomainApplicationStatus.APPROVED, "org": "SwiftPay Solutions", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "wildguard.org.bw", "zone": org_zone, "status": DomainApplicationStatus.APPROVED, "org": "Wildlife Guardians BW", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "hostmaster.net.bw", "zone": net_zone, "status": DomainApplicationStatus.APPROVED, "org": "HostMaster BW", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "freshmart.co.bw", "zone": co_zone, "status": DomainApplicationStatus.APPROVED, "org": "FreshMart Stores", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "codebw.co.bw", "zone": co_zone, "status": DomainApplicationStatus.APPROVED, "org": "CodeBW Academy", "type": DomainApplicationType.REGISTRATION},

            # REJECTED (3)
            {"domain_name": "casino.co.bw", "zone": co_zone, "status": DomainApplicationStatus.REJECTED, "org": "CasinoBW Online", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "fakegov.co.bw", "zone": co_zone, "status": DomainApplicationStatus.REJECTED, "org": "FakeGov Services", "type": DomainApplicationType.REGISTRATION},
            {"domain_name": "spammail.net.bw", "zone": net_zone, "status": DomainApplicationStatus.REJECTED, "org": "SpamMail Services", "type": DomainApplicationType.REGISTRATION},

            # CANCELLED (1)
            {"domain_name": "oldproject.co.bw", "zone": co_zone, "status": DomainApplicationStatus.CANCELLED, "org": "Old Project Ventures", "type": DomainApplicationType.REGISTRATION},
        ]

        seq = 1
        year = now.year

        for data in application_data:
            applicant = random.choice(users)
            reviewer = random.choice(staff_users)
            ref = f"DOM-{year}-{seq:06d}"
            seq += 1

            submitted_at = None
            decision_date = None
            reviewed_by = None
            decision_reason = ""
            info_request_message = ""

            if data["status"] != DomainApplicationStatus.DRAFT:
                submitted_at = now - timedelta(days=random.randint(1, 60))

            if data["status"] in (DomainApplicationStatus.UNDER_REVIEW, DomainApplicationStatus.APPROVED, DomainApplicationStatus.REJECTED, DomainApplicationStatus.INFO_REQUESTED):
                reviewed_by = reviewer

            if data["status"] in (DomainApplicationStatus.APPROVED, DomainApplicationStatus.REJECTED):
                decision_date = now - timedelta(days=random.randint(0, 10))

            if data["status"] == DomainApplicationStatus.REJECTED:
                decision_reason = random.choice([
                    "Domain name conflicts with existing trademark.",
                    "Applicant failed to provide required documentation.",
                    "Domain name deemed misleading or inappropriate.",
                ])

            if data["status"] == DomainApplicationStatus.INFO_REQUESTED:
                info_request_message = random.choice([
                    "Please provide your CIPA business registration certificate.",
                    "Additional proof of eligibility for this zone is required.",
                    "Please clarify the intended use of this domain.",
                ])

            slug = data["domain_name"].split(".")[0]

            app = DomainApplication(
                reference_number=ref,
                application_type=data["type"],
                applicant=applicant,
                domain_name=data["domain_name"],
                zone=data["zone"],
                status=data["status"],
                registration_period_years=random.randint(1, 3),
                organisation_name=data["org"],
                organisation_registration_number=f"BW-{random.randint(10000, 99999)}",
                registrant_name=f"{applicant.first_name} {applicant.last_name}".strip() or applicant.email,
                registrant_email=applicant.email,
                registrant_phone=f"+267 7{random.randint(1,9)}{random.randint(100000,999999)}",
                registrant_address=f"Plot {random.randint(100,9999)}, Gaborone, Botswana",
                nameserver_1=f"ns1.{slug}.co.bw",
                nameserver_2=f"ns2.{slug}.co.bw",
                tech_contact_name=f"{applicant.first_name} IT" if applicant.first_name else "IT Admin",
                tech_contact_email=f"tech@{data['domain_name']}",
                justification=f"We need {data['domain_name']} for our organisation's online presence.",
                submitted_at=submitted_at,
                reviewed_by=reviewed_by,
                decision_date=decision_date,
                decision_reason=decision_reason,
                info_request_message=info_request_message,
                created_by=applicant,
            )
            app.save()

            # Create status logs
            if data["status"] != DomainApplicationStatus.DRAFT:
                DomainApplicationStatusLog.objects.create(
                    application=app,
                    from_status=DomainApplicationStatus.DRAFT,
                    to_status=DomainApplicationStatus.SUBMITTED,
                    changed_by=applicant,
                    reason="Application submitted.",
                )

            if data["status"] in (DomainApplicationStatus.UNDER_REVIEW, DomainApplicationStatus.APPROVED, DomainApplicationStatus.REJECTED, DomainApplicationStatus.INFO_REQUESTED):
                DomainApplicationStatusLog.objects.create(
                    application=app,
                    from_status=DomainApplicationStatus.SUBMITTED,
                    to_status=DomainApplicationStatus.UNDER_REVIEW,
                    changed_by=reviewer,
                    reason="Application picked up for review.",
                )

            if data["status"] == DomainApplicationStatus.INFO_REQUESTED:
                DomainApplicationStatusLog.objects.create(
                    application=app,
                    from_status=DomainApplicationStatus.UNDER_REVIEW,
                    to_status=DomainApplicationStatus.INFO_REQUESTED,
                    changed_by=reviewer,
                    reason=info_request_message,
                )

            if data["status"] == DomainApplicationStatus.APPROVED:
                DomainApplicationStatusLog.objects.create(
                    application=app,
                    from_status=DomainApplicationStatus.UNDER_REVIEW,
                    to_status=DomainApplicationStatus.APPROVED,
                    changed_by=reviewer,
                    reason="Application approved.",
                )
                # Auto-create domain record for approved applications
                Domain.objects.create(
                    domain_name=data["domain_name"],
                    zone=data["zone"],
                    status=DomainStatus.ACTIVE,
                    registrant=applicant,
                    registrant_name=app.registrant_name,
                    registrant_email=app.registrant_email,
                    registrant_phone=app.registrant_phone,
                    registrant_address=app.registrant_address,
                    organisation_name=data["org"],
                    nameserver_1=app.nameserver_1,
                    nameserver_2=app.nameserver_2,
                    tech_contact_name=app.tech_contact_name,
                    tech_contact_email=app.tech_contact_email,
                    registered_at=now,
                    expires_at=now + timedelta(days=365 * app.registration_period_years),
                    created_from_application=app,
                    is_seeded=False,
                )

            if data["status"] == DomainApplicationStatus.REJECTED:
                DomainApplicationStatusLog.objects.create(
                    application=app,
                    from_status=DomainApplicationStatus.UNDER_REVIEW,
                    to_status=DomainApplicationStatus.REJECTED,
                    changed_by=reviewer,
                    reason=decision_reason,
                )

            if data["status"] == DomainApplicationStatus.CANCELLED:
                DomainApplicationStatusLog.objects.create(
                    application=app,
                    from_status=DomainApplicationStatus.DRAFT,
                    to_status=DomainApplicationStatus.CANCELLED,
                    changed_by=applicant,
                    reason="Application withdrawn by applicant.",
                )

        self.stdout.write(self.style.SUCCESS(f"  Total applications created: {len(application_data)}"))

    def _get_user_model(self):
        from django.contrib.auth import get_user_model
        return get_user_model()

from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.ingestion.services.energy_sector_enrichment import enrich_energy_disclosures


class Command(BaseCommand):
    help = "Promote explicit first-party Energy disclosures into reusable company records."

    def add_arguments(self, parser):
        parser.add_argument("--company", type=str, default="")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        if options["company"]:
            companies = Company.objects.filter(slug=options["company"], is_active=True)
        elif options["all"]:
            companies = Company.objects.filter(industry="Energy", is_active=True).order_by("name")
        else:
            self.stderr.write("Use --company <slug> or --all.")
            return

        totals = {"companies": 0, "events_created": 0, "offerings_created": 0}
        for company in companies:
            result = enrich_energy_disclosures(company)
            totals["companies"] += 1
            totals["events_created"] += result["events_created"]
            totals["offerings_created"] += result["offerings_created"]
            self.stdout.write(f"{company.slug}: {result}")
        self.stdout.write(self.style.SUCCESS(f"Energy disclosure enrichment complete: {totals}"))

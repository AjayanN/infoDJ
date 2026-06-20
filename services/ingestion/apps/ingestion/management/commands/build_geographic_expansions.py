from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.ingestion.services.geographic_expansion import build_geographic_expansion


class Command(BaseCommand):
    help = "Build reviewed Geographic Expansion Map baselines."

    def add_arguments(self, parser):
        parser.add_argument("--company", type=str, default="")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        if options["company"]:
            companies = Company.objects.filter(slug=options["company"], is_active=True)
        elif options["all"]:
            companies = Company.objects.filter(is_active=True).order_by("name")
        else:
            self.stderr.write("Use --company <slug> or --all.")
            return
        totals = {"companies": 0, "markets_created": 0, "markets_updated": 0}
        for company in companies:
            result = build_geographic_expansion(company)
            totals["companies"] += 1
            totals["markets_created"] += result["markets_created"]
            totals["markets_updated"] += result["markets_updated"]
            self.stdout.write(f"{company.slug}: {result}")
        self.stdout.write(self.style.SUCCESS(f"Geographic expansion build complete: {totals}"))

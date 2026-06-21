from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.ownership_insider_activity import build_ownership_insider_activity


class Command(BaseCommand):
    help = "Build reviewed Ownership and Insider Activity baselines."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug to rebuild.")
        parser.add_argument("--all", action="store_true", help="Rebuild all active companies.")

    def handle(self, *args, **options):
        if not options["all"] and not options["company"]:
            raise CommandError("Pass --all or --company <slug>.")
        companies = Company.objects.filter(is_active=True).order_by("name")
        if options["company"]:
            companies = companies.filter(slug=options["company"])
        totals = {"companies": 0, "snapshots_created": 0, "snapshots_updated": 0, "positions_created": 0, "positions_updated": 0}
        for company in companies:
            result = build_ownership_insider_activity(company)
            totals["companies"] += 1
            for key, value in result.items():
                totals[key] += value
            self.stdout.write(f"{company.slug}: {result}")
        self.stdout.write(self.style.SUCCESS(f"Ownership and Insider Activity build complete: {totals}"))

from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.product_pricing_history import build_product_pricing_history


class Command(BaseCommand):
    help = "Build reviewed Product and Pricing History records from reviewed profiles and product/pricing events."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug to build. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Build all active companies.")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else [self._company(options["company"])]
        totals = {"companies": 0, "snapshots_created": 0, "snapshots_updated": 0, "offerings_created": 0, "offerings_updated": 0, "changes_created": 0, "changes_updated": 0}
        for company in companies:
            result = build_product_pricing_history(company)
            totals["companies"] += 1
            for key, value in result.items():
                totals[key] += value
            self.stdout.write(self.style.SUCCESS(f"{company.slug}: {result}"))
        self.stdout.write(self.style.SUCCESS(f"Product and pricing history build complete: {totals}"))

    def _company(self, slug: str) -> Company:
        try:
            return Company.objects.get(slug=slug)
        except Company.DoesNotExist as exc:
            raise CommandError(f"Company not found: {slug}") from exc

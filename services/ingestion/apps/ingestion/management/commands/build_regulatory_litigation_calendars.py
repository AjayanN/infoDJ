from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.regulatory_litigation import build_regulatory_litigation_calendar


class Command(BaseCommand):
    help = "Build reviewed Regulatory and Litigation Calendar records from reviewed regulatory events and sources."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug to build. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Build all active companies.")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else [self._company(options["company"])]
        totals = {
            "companies": 0,
            "snapshots_created": 0,
            "snapshots_updated": 0,
            "matters_created": 0,
            "matters_updated": 0,
        }
        for company in companies:
            result = build_regulatory_litigation_calendar(company)
            totals["companies"] += 1
            for key, value in result.items():
                totals[key] += value
            self.stdout.write(self.style.SUCCESS(f"{company.slug}: {result}"))
        self.stdout.write(self.style.SUCCESS(f"Regulatory and Litigation Calendar build complete: {totals}"))

    def _company(self, slug: str) -> Company:
        try:
            return Company.objects.get(slug=slug)
        except Company.DoesNotExist as exc:
            raise CommandError(f"Company not found: {slug}") from exc

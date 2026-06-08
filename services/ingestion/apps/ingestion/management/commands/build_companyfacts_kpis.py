from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.kpi_companyfacts_builder import build_companyfacts_kpis


class Command(BaseCommand):
    help = "Build reviewed operating-tracker baseline series from stored official SEC Company Facts."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Build series for every active company.")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else Company.objects.filter(slug=options["company"])
        if not companies.exists():
            raise CommandError(f"Company not found: {options['company']}")
        totals = {"companies": 0, "definitions": 0, "observations": 0, "skipped": 0}
        for company in companies:
            counters = build_companyfacts_kpis(company)
            totals["companies"] += 1
            for key in ("definitions", "observations", "skipped"):
                totals[key] += counters[key]
            self.stdout.write(f"{company.slug}: {counters}")
        self.stdout.write(self.style.SUCCESS(f"Company Facts KPI build complete: {totals}"))

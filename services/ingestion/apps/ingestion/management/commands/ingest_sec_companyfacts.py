from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobType
from apps.ingestion.services.sec_companyfacts_client import (
    USEFUL_US_GAAP_CONCEPTS,
    ingest_sec_companyfacts_for_company,
)
from apps.ingestion.services.kpi_companyfacts_builder import build_companyfacts_kpis


class Command(BaseCommand):
    help = "Ingest official SEC companyfacts into FinancialFact rows."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug to ingest. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Ingest all active companies with a SEC CIK.")
        parser.add_argument("--forms", default="10-K,10-Q")
        parser.add_argument("--concepts", default=",".join(USEFUL_US_GAAP_CONCEPTS))
        parser.add_argument("--limit", type=int, default=500, help="Maximum facts to store per company.")
        parser.add_argument("--skip-kpi-build", action="store_true", help="Store facts without refreshing tracker series.")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")

        financial_fact_model = self._financial_fact_model()
        forms = tuple(value.strip().upper() for value in options["forms"].split(",") if value.strip())
        concepts = tuple(value.strip() for value in options["concepts"].split(",") if value.strip())
        companies = self._companies(options)

        totals = {
            "companies": 0,
            "facts_found": 0,
            "facts_inserted": 0,
            "facts_updated": 0,
            "duplicates_skipped": 0,
            "skipped_missing_cik": 0,
        }

        for company in companies:
            if not company.sec_cik:
                totals["skipped_missing_cik"] += 1
                self.stdout.write(self.style.WARNING(f"Skipping {company.slug}: missing sec_cik"))
                continue

            job = IngestionJob.objects.create(
                company=company,
                job_type=IngestionJobType.FINANCIAL_FACTS,
                source="SEC_COMPANYFACTS",
                query=f"{company.sec_cik}: concepts={len(concepts)} forms={', '.join(forms)} limit={options['limit']}",
                status="PENDING",
            )
            counters = ingest_sec_companyfacts_for_company(
                company=company,
                financial_fact_model=financial_fact_model,
                concepts=concepts,
                forms=forms,
                limit=options["limit"],
                job=job,
            )
            if not options["skip_kpi_build"]:
                kpi_counters = build_companyfacts_kpis(company)
                counters["kpi_definitions"] = kpi_counters["definitions"]
                counters["kpi_observations"] = kpi_counters["observations"]
            totals["companies"] += 1
            for key, value in counters.items():
                totals[key] = totals.get(key, 0) + value
            self.stdout.write(self.style.SUCCESS(f"{company.slug}: {counters}"))

        self.stdout.write(self.style.SUCCESS(f"SEC companyfacts ingestion complete: {totals}"))

    def _companies(self, options):
        if options["all"]:
            return Company.objects.filter(is_active=True).order_by("name")
        try:
            return [Company.objects.get(slug=options["company"])]
        except Company.DoesNotExist as exc:
            raise CommandError(f"Company not found: {options['company']}") from exc

    def _financial_fact_model(self):
        try:
            return apps.get_model("ingestion", "FinancialFact")
        except LookupError as exc:
            raise CommandError("apps.ingestion.models.FinancialFact is not installed yet.") from exc

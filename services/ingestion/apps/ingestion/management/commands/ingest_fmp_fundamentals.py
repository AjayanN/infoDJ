from __future__ import annotations

import os
import re

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.companies.models import Company
from apps.ingestion.management.commands.ingest_market_prices import ticker_for_company
from apps.ingestion.models import IngestionJob, IngestionJobStatus, IngestionJobType
from apps.ingestion.services.fmp_fundamentals import FMP_TAXONOMY, FmpFundamentalsClient


class Command(BaseCommand):
    help = "Ingest curated, standardized FMP financial fundamentals for active companies."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="", help="Company slug. Omit to ingest all active companies.")
        parser.add_argument("--limit", type=int, default=5, help="Financial periods to request for each FMP series.")
        parser.add_argument("--fmp-api-key", default="", help="FMP API key. Defaults to FMP_API_KEY.")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1.")
        api_key = options["fmp_api_key"] or os.getenv("FMP_API_KEY", "")
        client = FmpFundamentalsClient(api_key=api_key)
        financial_fact_model = apps.get_model("ingestion", "FinancialFact")
        totals = {"companies": 0, "facts_found": 0, "facts_inserted": 0, "facts_updated": 0, "skipped": 0}

        for company in self._companies(options["company"]):
            ticker = ticker_for_company(company)
            if not ticker:
                totals["skipped"] += 1
                self.stderr.write(f"Skipping {company.slug}: no ticker found.")
                continue
            counters = self._ingest_company(company, ticker, options["limit"], client, financial_fact_model)
            totals["companies"] += 1
            for key, value in counters.items():
                totals[key] += value

        self.stdout.write(self.style.SUCCESS(f"FMP fundamentals ingestion complete: {totals}"))

    def _companies(self, slug):
        if not slug:
            return Company.objects.filter(is_active=True).order_by("name")
        try:
            return [Company.objects.get(slug=slug)]
        except Company.DoesNotExist as exc:
            raise CommandError(f"Company not found: {slug}") from exc

    def _ingest_company(self, company, ticker, limit, client, financial_fact_model):
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.FINANCIAL_FACTS,
            source="FMP_FUNDAMENTALS",
            query=f"{ticker}: periods={limit}",
            status=IngestionJobStatus.RUNNING,
            started_at=timezone.now(),
        )
        counters = {"facts_found": 0, "facts_inserted": 0, "facts_updated": 0, "skipped": 0}
        try:
            for fact in client.fundamentals(ticker, limit=limit):
                defaults = {
                    "label": fact.label,
                    "value": fact.value,
                    "raw": fact.raw,
                }
                _, created = financial_fact_model.objects.update_or_create(
                    company=company,
                    taxonomy=FMP_TAXONOMY,
                    concept=fact.concept,
                    unit=fact.unit,
                    fy=fact.fiscal_year,
                    fp=fact.fiscal_period,
                    frame=fact.period_end.isoformat(),
                    filed=fact.period_end,
                    accession_number="",
                    defaults=defaults,
                )
                counters["facts_found"] += 1
                counters["facts_inserted" if created else "facts_updated"] += 1
        except Exception as exc:
            job.status = IngestionJobStatus.FAILED
            job.error_message = sanitize_error(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
            self.stderr.write(f"Skipping {company.slug}: {job.error_message}")
            counters["skipped"] += 1
            return counters

        job.status = IngestionJobStatus.SUCCEEDED
        job.sources_found = counters["facts_found"]
        job.sources_inserted = counters["facts_inserted"]
        job.duplicates_skipped = counters["facts_updated"]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "sources_found", "sources_inserted", "duplicates_skipped", "finished_at", "updated_at"])
        self.stdout.write(f"{company.slug} ({ticker}): {counters}")
        return counters


def sanitize_error(exc: Exception) -> str:
    return re.sub(r"apikey=[^&\s]+", "apikey=<redacted>", str(exc))

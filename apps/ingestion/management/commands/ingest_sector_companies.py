from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobType, SourceDocument
from apps.ingestion.services.gdelt_client import discover_sources_for_company
from apps.ingestion.services.query_generator import generate_query_strings
from apps.ingestion.services.sec_edgar_client import discover_sec_filings_for_company
from apps.ingestion.services.wikidata_client import sync_company_metadata
from apps.ingestion.services.wikipedia_client import WikipediaClient, store_wikipedia_sources


class Command(BaseCommand):
    help = "Seed and ingest a representative cross-sector company batch."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--skip-wikidata", action="store_true")
        parser.add_argument("--skip-sec", action="store_true")
        parser.add_argument("--skip-wikipedia", action="store_true")
        parser.add_argument("--include-gdelt", action="store_true")
        parser.add_argument("--sec-limit", type=int, default=60)
        parser.add_argument("--wikipedia-limit", type=int, default=40)
        parser.add_argument("--gdelt-records-per-query", type=int, default=5)
        parser.add_argument("--gdelt-query-limit", type=int, default=3)
        parser.add_argument("--full-history", action="store_true")
        parser.add_argument("--daily-idempotent", action="store_true")

    def handle(self, *args, **options):
        seeds = CROSS_SECTOR_COMPANIES[: options["limit"]]
        totals = {
            "companies": 0,
            "wikidata_ok": 0,
            "wikidata_failed": 0,
            "sec_inserted": 0,
            "sec_duplicates": 0,
            "sec_failed": 0,
            "wikipedia_inserted": 0,
            "wikipedia_duplicates": 0,
            "wikipedia_failed": 0,
            "gdelt_inserted": 0,
            "gdelt_duplicates": 0,
            "gdelt_failed": 0,
        }

        wikipedia_client = WikipediaClient()
        for seed in seeds:
            company, _created = Company.objects.get_or_create(
                slug=slugify(seed.name),
                defaults={
                    "name": seed.name,
                    "industry": seed.sector,
                    "country": seed.country,
                    "aliases": [seed.ticker],
                },
            )
            if seed.ticker not in (company.aliases or []):
                company.aliases = [*(company.aliases or []), seed.ticker]
            if not company.industry:
                company.industry = seed.sector
            if not company.country:
                company.country = seed.country
            company.save()
            totals["companies"] += 1

            if not options["skip_wikidata"]:
                if self._should_skip(company, "WIKIDATA", options):
                    self.stdout.write(f"{company.name}: WIKIDATA already succeeded today, skipping")
                elif self._sync_wikidata(company):
                    totals["wikidata_ok"] += 1
                else:
                    totals["wikidata_failed"] += 1
                company.industry = seed.sector
                company.country = company.country or seed.country
                company.save(update_fields=["industry", "country", "updated_at"])

            if not options["skip_sec"]:
                counters = None if self._should_skip(company, "SEC_EDGAR", options) else self._ingest_sec(company, seed.ticker, options)
                if counters is None and self._should_skip(company, "SEC_EDGAR", options):
                    self.stdout.write(f"{company.name}: SEC_EDGAR already succeeded today, skipping")
                if counters is None:
                    if not self._should_skip(company, "SEC_EDGAR", options):
                        totals["sec_failed"] += 1
                else:
                    totals["sec_inserted"] += counters["sources_inserted"]
                    totals["sec_duplicates"] += counters["duplicates_skipped"]

            if not options["skip_wikipedia"]:
                counters = None if self._should_skip(company, "WIKIPEDIA_REFERENCES", options) else self._ingest_wikipedia(company, wikipedia_client, options)
                if counters is None and self._should_skip(company, "WIKIPEDIA_REFERENCES", options):
                    self.stdout.write(f"{company.name}: WIKIPEDIA_REFERENCES already succeeded today, skipping")
                if counters is None:
                    if not self._should_skip(company, "WIKIPEDIA_REFERENCES", options):
                        totals["wikipedia_failed"] += 1
                else:
                    totals["wikipedia_inserted"] += counters["sources_inserted"]
                    totals["wikipedia_duplicates"] += counters["duplicates_skipped"]

            if options["include_gdelt"]:
                counters = None if self._should_skip(company, "GDELT_DOC_2", options) else self._ingest_gdelt(company, options)
                if counters is None and self._should_skip(company, "GDELT_DOC_2", options):
                    self.stdout.write(f"{company.name}: GDELT_DOC_2 already succeeded today, skipping")
                if counters is None:
                    if not self._should_skip(company, "GDELT_DOC_2", options):
                        totals["gdelt_failed"] += 1
                else:
                    totals["gdelt_inserted"] += counters["sources_inserted"]
                    totals["gdelt_duplicates"] += counters["duplicates_skipped"]

            self.stdout.write(
                f"{company.name}: sector={seed.sector}, ticker={seed.ticker}, "
                f"sources={company.source_documents.count()}"
            )

        self.stdout.write(self.style.SUCCESS(f"Cross-sector ingestion complete: {totals}"))

    def _should_skip(self, company, source: str, options) -> bool:
        if not options["daily_idempotent"]:
            return False
        today = timezone.localdate()
        return IngestionJob.objects.filter(
            company=company,
            source=source,
            status="SUCCEEDED",
            created_at__date=today,
        ).exists()

    def _sync_wikidata(self, company):
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.COMPANY_METADATA_SYNC,
            source="WIKIDATA",
            status="PENDING",
        )
        try:
            sync_company_metadata(company, job=job)
        except Exception as exc:
            self.stderr.write(f"Wikidata failed for {company.name}: {exc}")
            return False
        return True

    def _ingest_sec(self, company, ticker: str, options):
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.SOURCE_DISCOVERY,
            source="SEC_EDGAR",
            query=ticker,
            status="PENDING",
        )
        try:
            return discover_sec_filings_for_company(
                company=company,
                source_document_model=SourceDocument,
                ticker=ticker,
                forms=("10-K", "10-Q", "8-K"),
                limit=options["sec_limit"],
                full_history=options["full_history"],
                job=job,
            )
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            job.save()
            self.stderr.write(f"SEC failed for {company.name} ({ticker}): {exc}")
            return None

    def _ingest_wikipedia(self, company, client: WikipediaClient, options):
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.SOURCE_DISCOVERY,
            source="WIKIPEDIA_REFERENCES",
            query=company.name,
            status="RUNNING",
        )
        try:
            sources = client.discover_sources(company.name, limit=options["wikipedia_limit"])
            counters = store_wikipedia_sources(
                company=company,
                sources=sources,
                source_document_model=SourceDocument,
            )
            for key, value in counters.items():
                setattr(job, key, value)
            job.status = "SUCCEEDED"
            job.save()
            return counters
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            job.save()
            self.stderr.write(f"Wikipedia failed for {company.name}: {exc}")
            return None

    def _ingest_gdelt(self, company, options):
        aliases = company.aliases if isinstance(company.aliases, list) else []
        queries = generate_query_strings(company.name, aliases=aliases, include_aliases=False)[
            : options["gdelt_query_limit"]
        ]
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.SOURCE_DISCOVERY,
            source="GDELT_DOC_2",
            query="\n".join(queries),
            status="PENDING",
        )
        try:
            return discover_sources_for_company(
                company=company,
                queries=queries,
                source_document_model=SourceDocument,
                job=job,
                max_records_per_query=options["gdelt_records_per_query"],
                query_delay=1.0,
                allowed_languages=("English",),
            )
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            job.save()
            self.stderr.write(f"GDELT failed for {company.name}: {exc}")
            return None

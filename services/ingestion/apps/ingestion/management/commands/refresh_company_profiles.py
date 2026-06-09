from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobStatus, IngestionJobType
from apps.ingestion.services.company_profile_client import collect_official_company_profile
from apps.ingestion.services.wikidata_client import sync_company_metadata


class Command(BaseCommand):
    help = "Refresh source-backed Company 360 profiles for the configured company universe."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--batch-size", type=int, default=0)
        parser.add_argument("--skip-wikidata", action="store_true")
        parser.add_argument("--skip-official", action="store_true")
        parser.add_argument("--daily-idempotent", action="store_true")
        parser.add_argument("--retry-failed-only", action="store_true")

    def handle(self, *args, **options):
        seeds = CROSS_SECTOR_COMPANIES[options["offset"] : options["limit"]]
        if options["batch_size"]:
            seeds = seeds[: options["batch_size"]]

        totals = {
            "companies": 0,
            "wikidata_ok": 0,
            "wikidata_failed": 0,
            "official_ok": 0,
            "official_failed": 0,
            "skipped": 0,
        }
        for seed in seeds:
            company, _created = Company.objects.get_or_create(
                slug=slugify(seed.name),
                defaults={
                    "name": seed.name,
                    "industry": seed.sector,
                    "country": seed.country,
                    "aliases": [seed.ticker],
                    "website": seed.website,
                },
            )
            totals["companies"] += 1

            if not options["skip_wikidata"]:
                result = self._refresh_wikidata(company, options)
                totals[result] += 1

            company.refresh_from_db()
            company.industry = seed.sector
            company.country = company.country or seed.country
            company.website = seed.website or company.website
            company.save(update_fields=["industry", "country", "website", "updated_at"])
            if not options["skip_official"]:
                result = self._refresh_official(company, options)
                totals[result] += 1

            self.stdout.write(
                f"{company.name}: snapshots={company.profile_snapshots.count()} website={company.website or 'unavailable'}"
            )

        self.stdout.write(self.style.SUCCESS(f"Company 360 profile refresh complete: {totals}"))

    def _refresh_wikidata(self, company, options) -> str:
        if self._should_skip(company, "WIKIDATA", options):
            self.stdout.write(f"{company.name}: WIKIDATA already processed today, skipping")
            return "skipped"
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.COMPANY_METADATA_SYNC,
            source="WIKIDATA",
            status=IngestionJobStatus.PENDING,
        )
        try:
            sync_company_metadata(company, job=job)
        except Exception as exc:
            self.stderr.write(f"Wikidata profile refresh failed for {company.name}: {exc}")
            return "wikidata_failed"
        return "wikidata_ok"

    def _refresh_official(self, company, options) -> str:
        if self._should_skip(company, "OFFICIAL_WEBSITE", options):
            self.stdout.write(f"{company.name}: OFFICIAL_WEBSITE already processed today, skipping")
            return "skipped"
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.COMPANY_METADATA_SYNC,
            source="OFFICIAL_WEBSITE",
            query=company.website,
            status=IngestionJobStatus.RUNNING,
            started_at=timezone.now(),
        )
        try:
            collect_official_company_profile(company)
        except Exception as exc:
            job.status = IngestionJobStatus.FAILED
            job.error_message = str(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error_message", "finished_at"])
            self.stderr.write(f"Official profile refresh failed for {company.name}: {exc}")
            return "official_failed"
        job.status = IngestionJobStatus.SUCCEEDED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at"])
        return "official_ok"

    def _should_skip(self, company, source: str, options) -> bool:
        if not options["daily_idempotent"]:
            return False
        jobs = IngestionJob.objects.filter(company=company, source=source, created_at__date=timezone.localdate())
        if options["retry_failed_only"]:
            latest = jobs.order_by("-created_at").first()
            return latest is None or latest.status != IngestionJobStatus.FAILED
        return jobs.filter(status=IngestionJobStatus.SUCCEEDED).exists()

"""Import reviewable historical lifecycle episodes from a curated primary-source manifest."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.models import Company
from apps.curation.models import LifecycleEpisode, LifecycleEpisodeStatus
from apps.ingestion.models import SourceDocument


class Command(BaseCommand):
    help = (
        "Import historical company/product lifecycle episodes. Records remain pending "
        "unless --verify is supplied after primary-source review."
    )

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="JSON array of historical lifecycle episode records.")
        parser.add_argument("--verify", action="store_true", help="Mark imported records VERIFIED after model validation.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        path = Path(options["input"])
        if not path.is_file():
            raise CommandError(f"Input file not found: {path}")
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise CommandError(f"Input must be a JSON array: {error}") from error
        if not isinstance(records, list):
            raise CommandError("Input must be a JSON array.")

        counts = {"scanned": 0, "created": 0, "updated": 0, "pending": 0, "verified": 0}
        for row in records:
            counts["scanned"] += 1
            if not isinstance(row, dict):
                raise CommandError(f"Record {counts['scanned']} is not an object.")
            company = self._company(row)
            start_date = self._date(row, "start_date")
            end_date = self._date(row, "end_date", required=False)
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                raise CommandError(f"{company.slug}: source_url is required.")
            source_document = SourceDocument.objects.filter(company=company, url=source_url).first()
            status = LifecycleEpisodeStatus.VERIFIED if options["verify"] else LifecycleEpisodeStatus.PENDING
            defaults = {
                "stage": str(row.get("stage") or "").strip(),
                "start_date_precision": str(row.get("start_date_precision") or "DAY").strip(),
                "end_date": end_date,
                "evidence_text": str(row.get("evidence_text") or "").strip(),
                "source_document": source_document,
                "verification_status": status,
                "metadata": {
                    "sector": company.sector,
                    "decision_type": str(row.get("decision_type") or "").strip(),
                    "target_customer": str(row.get("target_customer") or "").strip(),
                    "business_model": str(row.get("business_model") or "").strip(),
                    "imported_by": "import_historical_lifecycle_episodes",
                },
            }
            lookup = {
                "company": company,
                "scope": str(row.get("scope") or "COMPANY").strip(),
                "subject_name": str(row.get("subject_name") or "").strip(),
                "start_date": start_date,
                "source_url": source_url,
            }
            episode = LifecycleEpisode(**lookup, **defaults)
            episode.full_clean()
            if options["dry_run"]:
                counts["verified" if status == LifecycleEpisodeStatus.VERIFIED else "pending"] += 1
                continue
            existing = LifecycleEpisode.objects.filter(**lookup).first()
            if existing:
                for key, value in defaults.items():
                    setattr(existing, key, value)
                existing.full_clean()
                existing.save()
                counts["updated"] += 1
            else:
                episode.save()
                counts["created"] += 1
            counts["verified" if status == LifecycleEpisodeStatus.VERIFIED else "pending"] += 1

        mode = "Dry run" if options["dry_run"] else "Import"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {counts}"))

    @staticmethod
    def _company(row):
        slug = slugify(str(row.get("company_slug") or ""))
        if not slug:
            raise CommandError("company_slug is required.")
        try:
            return Company.objects.get(slug=slug)
        except Company.DoesNotExist as error:
            raise CommandError(f"Unknown company_slug: {slug}") from error

    @staticmethod
    def _date(row, key, *, required=True):
        value = row.get(key)
        if not value and not required:
            return None
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError) as error:
            raise CommandError(f"{key} must be YYYY-MM-DD.") from error


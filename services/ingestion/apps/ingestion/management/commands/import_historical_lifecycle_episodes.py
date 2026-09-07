"""Import reviewable historical lifecycle episodes from a curated primary-source manifest."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import transaction

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
        parser.add_argument("--milestones", help="Reviewed product milestone manifest.")

    @transaction.atomic
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

        milestones = self._milestones(options.get("milestones"))
        subjects = {(r.get("company_slug"), r.get("scope"), r.get("subject_name"))
                    for r in records if isinstance(r, dict)}
        if set(milestones) - subjects:
            raise CommandError("Milestones contain a subject absent from the episode manifest.")

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
                "source_url": source_url,
                "source_document": source_document,
                "verification_status": status,
                "metadata": {
                    "industry": company.industry,
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
            }
            milestone_key = (company.slug, lookup["scope"], lookup["subject_name"])
            if milestone_key in milestones:
                defaults["metadata"]["product_milestones"] = milestones[milestone_key]
            episode = LifecycleEpisode(**lookup, **defaults)
            episode.full_clean()
            if options["dry_run"]:
                counts["verified" if status == LifecycleEpisodeStatus.VERIFIED else "pending"] += 1
                continue
            matches = LifecycleEpisode.objects.filter(**lookup)
            existing = matches.filter(source_url=source_url).first() or matches.first()
            if existing:
                defaults["metadata"] = {**(existing.metadata or {}), **defaults["metadata"]}
                duplicate_ids = matches.exclude(pk=existing.pk).filter(
                    verification_status=LifecycleEpisodeStatus.VERIFIED
                ).values_list("pk", flat=True)
                if duplicate_ids:
                    LifecycleEpisode.objects.filter(pk__in=duplicate_ids).update(
                        verification_status=LifecycleEpisodeStatus.REJECTED
                    )
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



    @staticmethod
    def _milestones(input_path):
        if not input_path:
            return {}
        try:
            rows = json.loads(Path(input_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CommandError("Cannot read product milestone manifest.") from error
        if not isinstance(rows, list):
            raise CommandError("Product milestones must be a JSON array.")
        grouped = {}
        seen = set()
        kinds = {"PUBLIC_ANNOUNCEMENT", "PROTOTYPE_UNVEILING", "RETAIL_RELEASE", "REGULAR_PRODUCTION_START"}
        for row in rows:
            if not isinstance(row, dict):
                raise CommandError("Each product milestone must be an object.")
            if row.get("scope") not in {"PRODUCT", "BUSINESS_LINE"} or row.get("review_status") != "VERIFIED":
                raise CommandError("Product milestones require a product/business-line scope and reviewed evidence.")
            if row.get("date_precision") != "DAY" or row.get("establishes_product_inception") is not False:
                raise CommandError("Milestones require an exact day and must not claim product inception.")
            if row.get("milestone") not in kinds:
                raise CommandError("Unsupported product milestone type.")
            for field in ("company_slug", "subject_name", "evidence", "source_url", "action_date"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise CommandError(f"Product milestone requires {field}.")
            try:
                parsed = date.fromisoformat(row["action_date"])
                if parsed.isoformat() != row["action_date"]:
                    raise ValueError("Noncanonical date")
                URLValidator(schemes=["https", "http"])(row["source_url"])
            except (ValueError, ValidationError) as error:
                raise CommandError("Invalid product milestone date or source URL.") from error
            key = (row["company_slug"], row["scope"], row["subject_name"])
            identity = (*key, row["milestone"], row["action_date"])
            if identity in seen:
                raise CommandError("Duplicate product milestone identity.")
            seen.add(identity)
            grouped.setdefault(key, []).append(row)
        for rows in grouped.values():
            rows.sort(key=lambda row: (row["action_date"], row["milestone"]))
        return grouped

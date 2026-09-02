"""Import reviewed founding anchors from a versioned evidence manifest."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.models import Company, DatePrecision, FoundingAnchorStatus


class Command(BaseCommand):
    help = "Import source-backed company founding anchors."

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="JSON array of founding-anchor records.")
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

        counts = {"scanned": 0, "created": 0, "updated": 0}
        for row in records:
            counts["scanned"] += 1
            if not isinstance(row, dict):
                raise CommandError(f"Record {counts['scanned']} is not an object.")
            company = self._company(row)
            anchor = self._anchor(row)
            changed = any(getattr(company, key) != value for key, value in anchor.items())
            if changed and not options["dry_run"]:
                for key, value in anchor.items():
                    setattr(company, key, value)
                company.save(update_fields=[*anchor.keys(), "updated_at"])
            counts["created" if changed and not company.founded_date else "updated"] += 1

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
    def _anchor(row):
        try:
            founded_date = date.fromisoformat(str(row.get("founded_date") or ""))
        except ValueError as error:
            raise CommandError("founded_date must be YYYY-MM-DD.") from error
        precision = str(row.get("precision") or "")
        if precision not in DatePrecision.values:
            raise CommandError("precision must be DAY, MONTH, or YEAR.")
        evidence = str(row.get("evidence_text") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        if not evidence or not source_url:
            raise CommandError("evidence_text and source_url are required.")
        return {
            "founded_date": founded_date,
            "founded_date_precision": precision,
            "founded_date_evidence": evidence,
            "founded_date_source_url": source_url,
            "founding_anchor_status": FoundingAnchorStatus.VERIFIED,
        }

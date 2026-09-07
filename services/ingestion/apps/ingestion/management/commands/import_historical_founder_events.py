"""Import source-backed historical founder-comparison actions."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, LifecycleEpisode, LifecycleEpisodeStatus, LifecycleTimingStatus, ReviewStatus
from apps.ingestion.models import SourceDocument


class Command(BaseCommand):
    help = "Import verified historical actions linked to verified lifecycle episodes."

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="JSON array of historical action records.")
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
            event, created = self._event(row, create_source=not options["dry_run"])
            event.full_clean()
            if options["dry_run"]:
                counts["created" if created else "updated"] += 1
                continue
            if created:
                event.save()
                counts["created"] += 1
            else:
                existing = BusinessEvent.objects.get(
                    company=event.company,
                    event_type=event.event_type,
                    action_date=event.action_date,
                    source_document=event.source_document,
                )
                for field in self._mutable_fields():
                    setattr(existing, field, getattr(event, field))
                existing.full_clean()
                existing.save()
                counts["updated"] += 1

        mode = "Dry run" if options["dry_run"] else "Import"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {counts}"))

    def _event(self, row, *, create_source: bool):
        company = self._company(row)
        action_date = self._date(row, "action_date")
        source_url = self._required(row, "source_url")
        evidence = self._required(row, "evidence_text")
        episode = self._episode(company, row, action_date)
        source_document = self._source_document(company, row, source_url, evidence, create_source=create_source)
        lookup = {
            "company": company,
            "event_type": self._required(row, "event_type"),
            "action_date": action_date,
            "source_document": source_document,
        }
        existing = BusinessEvent.objects.filter(**lookup).first()
        event = existing or BusinessEvent(**lookup)
        event.action_date_precision = "DAY"
        event.action_date_evidence = evidence
        event.lifecycle_episode = episode
        event.lifecycle_stage = episode.stage
        event.lifecycle_timing_status = LifecycleTimingStatus.VERIFIED
        event.lifecycle_context_json = {
            "evidence_mode": "HISTORICAL_PRIMARY_SOURCE",
            "source_url": source_url,
            "source_title": self._required(row, "source_title"),
            "scope": episode.scope,
            "subject_name": episode.subject_name,
            "stage": episode.stage,
            "stage_evidence": episode.evidence_text,
            "stage_source_url": episode.source_url,
            "company_lifecycle_stage": episode.stage if episode.scope == "COMPANY" else None,
            "company_lifecycle_stage_evidence": episode.evidence_text if episode.scope == "COMPANY" else None,
            "company_lifecycle_stage_source_url": episode.source_url if episode.scope == "COMPANY" else None,
        }
        event.decision_theme = str(row.get("decision_theme") or "HISTORICAL_LIFECYCLE")
        event.decision = self._required(row, "decision")
        event.actual_change = self._required(row, "actual_change")
        event.source_claim = evidence
        event.evidence_text = evidence
        event.before_state = str(row.get("before_state") or "")
        event.after_state = str(row.get("after_state") or "")
        event.trigger = str(row.get("trigger") or "")
        event.outcome = str(row.get("outcome") or "")
        event.confidence_score = "1.000"
        event.review_status = ReviewStatus.APPROVED
        event.raw_extraction_json = {
            "provenance": "HISTORICAL_PRIMARY_SOURCE",
            "action_date_source": "explicit_primary_or_authoritative_source",
            "source_url": source_url,
        }
        return event, existing is None

    @staticmethod
    def _mutable_fields():
        return (
            "action_date_precision", "action_date_evidence", "lifecycle_episode", "lifecycle_stage",
            "lifecycle_timing_status", "lifecycle_context_json", "decision_theme", "decision",
            "actual_change", "source_claim", "evidence_text", "before_state", "after_state",
            "trigger", "outcome", "confidence_score", "review_status", "raw_extraction_json",
        )

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
    def _date(row, key):
        try:
            return date.fromisoformat(str(row.get(key) or ""))
        except ValueError as error:
            raise CommandError(f"{key} must be YYYY-MM-DD.") from error

    @staticmethod
    def _required(row, key):
        value = str(row.get(key) or "").strip()
        if not value:
            raise CommandError(f"{key} is required.")
        return value

    def _episode(self, company, row, action_date):
        try:
            episode_start = self._date(row, "episode_start_date")
            episode = LifecycleEpisode.objects.get(
                company=company,
                scope=self._required(row, "episode_scope"),
                subject_name=str(row.get("episode_subject_name") or "").strip(),
                start_date=episode_start,
                verification_status=LifecycleEpisodeStatus.VERIFIED,
            )
        except LifecycleEpisode.DoesNotExist as error:
            raise CommandError(f"No verified lifecycle episode for {company.slug} at requested start date.") from error
        if not episode.contains(action_date):
            raise CommandError(f"{company.slug}: lifecycle episode does not cover action_date.")
        return episode

    @staticmethod
    def _source_document(company, row, source_url, evidence, *, create_source: bool):
        source = SourceDocument.objects.filter(url=source_url).first()
        if source:
            if source.company_id != company.id:
                raise CommandError(f"Source URL already belongs to another company: {source_url}")
            return source
        if not create_source:
            return None
        return SourceDocument.objects.create(
            company=company,
            source_api="HISTORICAL_PRIMARY_SOURCE",
            url=source_url,
            canonical_url=source_url,
            title=Command._required(row, "source_title"),
            publisher=str(row.get("source_publisher") or "").strip(),
            snippet=evidence,
            language=str(row.get("source_language") or "en").strip(),
        )

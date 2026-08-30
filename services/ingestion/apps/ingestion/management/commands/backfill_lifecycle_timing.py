"""Backfill only auditable, exact-date lifecycle timing for BusinessEvent records."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.text import slugify

from apps.curation.models import BusinessEvent, LifecycleTimingStatus
from apps.ingestion.models import FinancialFact
from apps.ingestion.services.lifecycle_timing import (
    exact_action_date_from_evidence,
    lifecycle_context_from_financial_facts,
)


class Command(BaseCommand):
    help = (
        "Backfill verified lifecycle timing from existing primary-source evidence. "
        "Events without an exact action day and contemporaneous scale remain pending."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company", action="append", default=[], help="Company slug; repeatable.")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        requested = {slugify(value) for value in options["company"] if value.strip()}
        events = BusinessEvent.objects.select_related("company").order_by("id")
        if requested:
            events = [event for event in events if slugify(event.company.name) in requested]
        elif options["limit"]:
            events = events[: options["limit"]]

        counts = {"scanned": 0, "verified": 0, "pending": 0, "no_founding_anchor": 0, "no_exact_date": 0, "no_scale_context": 0}
        for event in events:
            counts["scanned"] += 1
            if options["limit"] and counts["scanned"] > options["limit"]:
                break
            parsed = exact_action_date_from_evidence(event.evidence_text or "")
            if not event.company.founded_date:
                counts["no_founding_anchor"] += 1
                self._mark_pending(event, "missing_founding_anchor", options["dry_run"])
                continue
            if not parsed:
                counts["no_exact_date"] += 1
                self._mark_pending(event, "missing_exact_action_date_in_primary_evidence", options["dry_run"])
                continue
            action_date, evidence = parsed
            facts = FinancialFact.objects.filter(company=event.company).filter(Q(filed__lte=action_date)).order_by("-filed")
            context = lifecycle_context_from_financial_facts(
                company=event.company,
                action_date=action_date,
                financial_facts=facts,
            )
            if not context or not context.get("source_url"):
                counts["no_scale_context"] += 1
                self._mark_pending(event, "missing_contemporaneous_primary_financial_fact", options["dry_run"])
                continue
            counts["verified"] += 1
            if not options["dry_run"]:
                event.action_date = action_date
                event.action_date_precision = "DAY"
                event.action_date_evidence = evidence
                event.lifecycle_context_json = context
                event.lifecycle_timing_status = LifecycleTimingStatus.VERIFIED
                event.full_clean()
                event.save(update_fields=[
                    "action_date", "action_date_precision", "action_date_evidence",
                    "lifecycle_context_json", "lifecycle_timing_status", "updated_at",
                ])

        counts["pending"] = counts["scanned"] - counts["verified"]
        mode = "Dry run" if options["dry_run"] else "Backfill"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {counts}"))

    @staticmethod
    def _mark_pending(event, reason: str, dry_run: bool) -> None:
        if dry_run:
            return
        raw = dict(event.raw_extraction_json or {})
        raw["lifecycle_timing_gap"] = {
            "status": "PENDING_PRIMARY_SOURCE_RESEARCH",
            "reason": reason,
            "recommended_sources": [
                "SEC EDGAR filing text with an explicit effective/action date",
                "Issuer investor-relations press release announcing the action",
            ],
        }
        event.raw_extraction_json = raw
        event.lifecycle_timing_status = LifecycleTimingStatus.PENDING
        event.save(update_fields=["raw_extraction_json", "lifecycle_timing_status", "updated_at"])

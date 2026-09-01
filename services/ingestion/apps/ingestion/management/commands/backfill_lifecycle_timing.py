"""Backfill only auditable, exact-date lifecycle timing for BusinessEvent records."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.text import slugify

from apps.curation.models import BusinessEvent, LifecycleEpisode, LifecycleEpisodeStatus, LifecycleTimingStatus
from apps.ingestion.models import FinancialFact, SourceGap, SourceGapStatus
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

        counts = {"scanned": 0, "verified": 0, "pending": 0, "action_dates_recovered": 0, "no_founding_anchor": 0, "no_exact_date": 0, "no_scale_context": 0, "no_lifecycle_episode": 0}
        for event in events:
            counts["scanned"] += 1
            if options["limit"] and counts["scanned"] > options["limit"]:
                break
            parsed = exact_action_date_from_evidence(event.evidence_text or "")
            if parsed and self._store_exact_action_date_if_missing(event, *parsed, options["dry_run"]):
                counts["action_dates_recovered"] += 1
            if not self._has_verified_founding_anchor(event.company):
                counts["no_founding_anchor"] += 1
                self._mark_pending(event, "missing_verified_founding_anchor", options["dry_run"])
                continue
            if not parsed:
                counts["no_exact_date"] += 1
                self._mark_pending(event, "missing_exact_action_date_in_primary_evidence", options["dry_run"])
                continue
            action_date, evidence = parsed
            facts = FinancialFact.objects.filter(company=event.company).filter(Q(filed__lte=action_date)).order_by("-filed")
            episode = self._episode_for(event.company, action_date)
            if not episode:
                counts["no_lifecycle_episode"] += 1
                self._mark_pending(event, "missing_verified_lifecycle_episode_at_action_date", options["dry_run"])
                continue
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
                context["company_lifecycle_stage"] = episode.stage
                context["company_lifecycle_stage_evidence"] = episode.evidence_text
                context["company_lifecycle_stage_source_url"] = episode.source_url
                event.lifecycle_episode = episode
                event.full_clean()
                event.save(update_fields=[
                    "action_date", "action_date_precision", "action_date_evidence",
                    "lifecycle_context_json", "lifecycle_episode", "lifecycle_timing_status", "updated_at",
                ])

        counts["pending"] = counts["scanned"] - counts["verified"]
        companies = {event.company for event in events}
        self._reconcile_company_source_gaps(companies, dry_run=options["dry_run"])
        mode = "Dry run" if options["dry_run"] else "Backfill"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {counts}"))

    @staticmethod
    def _episode_for(company, action_date):
        return (
            LifecycleEpisode.objects.filter(
                company=company,
                verification_status=LifecycleEpisodeStatus.VERIFIED,
                start_date__lte=action_date,
            )
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=action_date))
            .order_by("-start_date")
            .first()
        )

    def _reconcile_company_source_gaps(self, companies, *, dry_run: bool) -> None:
        """Create/resolve the single actionable lifecycle gap for every company.

        The public eligibility gate prevents bad evidence from rendering; this gap
        makes the required remediation durable and discoverable by source tooling.
        """
        for company in companies:
            if not self._has_verified_founding_anchor(company):
                reason = "A source-backed founding anchor with disclosed precision has not been verified."
                task = "Collect an issuer history, charter, or archived primary record for the founding anchor; preserve its stated precision."
                metadata = {"missing": ["founding_anchor"], "required_sources": ["issuer history", "charter or incorporation record"]}
            elif not BusinessEvent.objects.filter(company=company, lifecycle_timing_status=LifecycleTimingStatus.VERIFIED).exists():
                reason = "No founder-comparison event has an exact action day, direct evidence sentence, and contemporaneous primary scale fact."
                task = "Collect issuer or SEC primary documents that state the action's effective date, then attach a financial fact known on or before that day."
                metadata = {"missing": ["actual_action_date", "contemporaneous_scale"], "required_sources": ["SEC EDGAR filing text", "issuer investor-relations release"]}
            else:
                if not dry_run:
                    SourceGap.objects.filter(
                        company=company, dashboard="FOUNDER_DECISION", gap_type="LIFECYCLE_TIMING", provider="PRIMARY_SOURCE"
                    ).update(status=SourceGapStatus.RESOLVED)
                continue
            if not dry_run:
                SourceGap.objects.update_or_create(
                    company=company,
                    dashboard="FOUNDER_DECISION",
                    gap_type="LIFECYCLE_TIMING",
                    provider="PRIMARY_SOURCE",
                    defaults={
                        "reason": reason,
                        "next_ingestion_task": task,
                        "status": SourceGapStatus.OPEN,
                        "metadata": metadata,
                    },
                )

    @staticmethod
    def _has_verified_founding_anchor(company) -> bool:
        return bool(
            company.founded_date
            and company.founded_date_precision
            and company.founding_anchor_status == "VERIFIED"
            and company.founded_date_evidence.strip()
            and company.founded_date_source_url.strip()
        )

    @staticmethod
    def _store_exact_action_date_if_missing(event, action_date, evidence: str, dry_run: bool) -> bool:
        """Persist only an action day stated in this event's own source evidence.

        This recovery remains PENDING until founding, scale, and lifecycle evidence
        gates are met; it never turns a dated observation into a comparison.
        """
        if event.action_date:
            return False
        if not dry_run:
            event.action_date = action_date
            event.action_date_precision = "DAY"
            event.action_date_evidence = evidence
            event.save(update_fields=["action_date", "action_date_precision", "action_date_evidence", "updated_at"])
        return True

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

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.services.dashboard_quality import event_eligibility
from apps.ingestion.services.event_extractor import additional_source_documents_for, founder_lesson_for


class Command(BaseCommand):
    help = "Build specific strategic turns from eligible source-backed business events."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="", help="Company slug. Omit to process all active companies.")
        parser.add_argument("--limit", type=int, default=0, help="Maximum eligible events to process.")
        parser.add_argument("--delete-generated", action="store_true", help="Delete previously generated specific turns before rebuilding.")

    def handle(self, *args, **options):
        companies = self._companies(options["company"])
        totals = {"companies": 0, "events": 0, "turns_created": 0, "turns_updated": 0}
        for company in companies:
            if options["delete_generated"]:
                StrategicTurn.objects.filter(
                    company=company,
                    turn_sources__business_event__isnull=False,
                    turn_sources__source_document__source_api__in=["SEC_EDGAR", "SEC", "GDELT_DOC_2"],
                ).exclude(turn_sources__source_document__source_api="MANUAL").distinct().delete()
            events = eligible_events_for_company(company, limit=options["limit"])
            created = 0
            updated = 0
            for event in events:
                turn, was_created = upsert_turn_from_event(event)
                link_turn_sources(turn, event)
                created += 1 if was_created else 0
                updated += 0 if was_created else 1
            totals["companies"] += 1
            totals["events"] += len(events)
            totals["turns_created"] += created
            totals["turns_updated"] += updated
            self.stdout.write(f"{company.slug}: eligible_events={len(events)} created={created} updated={updated}")
        self.stdout.write(self.style.SUCCESS(f"Specific turn rebuild complete: {totals}"))

    def _companies(self, company_slug: str):
        if company_slug:
            try:
                return [Company.objects.get(slug=company_slug)]
            except Company.DoesNotExist as exc:
                raise CommandError(f"Company not found: {company_slug}") from exc
        return Company.objects.filter(is_active=True).order_by("name")


def eligible_events_for_company(company: Company, *, limit: int = 0) -> list[BusinessEvent]:
    queryset = (
        BusinessEvent.objects.select_related("company", "source_document")
        .filter(company=company)
        .exclude(actual_change="")
        .order_by("-event_date", "-confidence_score", "id")
    )
    events = [event for event in queryset if event_eligibility(event).eligible]
    return events[:limit] if limit else events


def upsert_turn_from_event(event: BusinessEvent):
    title = specific_turn_title(event)
    decision = event.decision if event.decision and clean_sentence(event.decision) != clean_sentence(event.actual_change) else event.source_claim
    defaults = {
        "turn_type": event.event_type,
        "start_date": event.event_date,
        "end_date": event.event_date,
        "lifecycle_stage": event.lifecycle_stage,
        "summary": event.actual_change,
        "before_state": event.before_state,
        "after_state": event.after_state,
        "trigger": event.trigger,
        "decision": decision,
        "outcome": event.outcome or event.source_claim,
        "founder_lesson": founder_lesson_for(event.event_type),
        "confidence_score": max(event.confidence_score, 0),
        "review_status": "NEEDS_REVIEW",
        "is_published": False,
    }
    turn, created = StrategicTurn.objects.update_or_create(
        company=event.company,
        title=title,
        defaults=defaults,
    )
    return turn, created


def specific_turn_title(event: BusinessEvent) -> str:
    action = clean_sentence(event.actual_change or event.source_claim)
    if action.lower().startswith(event.company.name.lower()):
        return action[:512]
    return f"{event.company.name}: {action}"[:512]


def clean_sentence(value: str) -> str:
    return " ".join(str(value or "").strip().split()).rstrip(".") + "."


def link_turn_sources(turn: StrategicTurn, event: BusinessEvent) -> None:
    if event.source_document_id:
        StrategicTurnSource.objects.get_or_create(
            strategic_turn=turn,
            source_document=event.source_document,
            business_event=event,
            defaults={"evidence_text": event.evidence_text},
        )
    for source_document in additional_source_documents_for(event):
        StrategicTurnSource.objects.get_or_create(
            strategic_turn=turn,
            source_document=source_document,
            business_event=event,
            defaults={"evidence_text": event.evidence_text},
        )

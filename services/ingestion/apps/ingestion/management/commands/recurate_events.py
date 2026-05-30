from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.services.event_extractor import (
    SEC_EVENT_SIGNALS,
    create_strategic_turns_from_events,
)


class Command(BaseCommand):
    help = "Backfill decision themes and rebuild strategic turns from event clusters."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="netflix")
        parser.add_argument("--delete-old-turns", action="store_true")

    def handle(self, *args, **options):
        company = Company.objects.get(slug=options["company"])
        signal_by_decision = {signal.decision: signal for signal in SEC_EVENT_SIGNALS}

        updated = 0
        for event in BusinessEvent.objects.filter(company=company):
            signal = signal_by_decision.get(event.decision)
            if not signal:
                continue
            if event.decision_theme != signal.decision_theme:
                event.decision_theme = signal.decision_theme
                event.raw_extraction_json = {
                    **(event.raw_extraction_json or {}),
                    "decision_theme": signal.decision_theme,
                }
                event.save(update_fields=["decision_theme", "raw_extraction_json", "updated_at"])
                updated += 1

        if options["delete_old_turns"]:
            StrategicTurn.objects.filter(company=company).exclude(
                turn_sources__source_document__source_api="MANUAL"
            ).delete()

        turns = create_strategic_turns_from_events(
            company=company,
            business_event_model=BusinessEvent,
            strategic_turn_model=StrategicTurn,
            strategic_turn_source_model=StrategicTurnSource,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfilled {updated} events and rebuilt {len(turns)} strategic turns."
            )
        )

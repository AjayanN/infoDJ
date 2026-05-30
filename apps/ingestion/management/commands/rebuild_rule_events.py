from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource


class Command(BaseCommand):
    help = "Delete rule-generated events and rebuild them with current extraction logic."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="netflix")
        parser.add_argument("--forms", default="10-K")
        parser.add_argument("--limit", type=int, default=30)
        parser.add_argument("--reuse-extractions", action="store_true")

    def handle(self, *args, **options):
        company = Company.objects.get(slug=options["company"])
        rule_events = BusinessEvent.objects.filter(
            company=company,
            raw_extraction_json__extractor="sec_rules_v1",
        )
        deleted_events = rule_events.count()
        rule_events.delete()
        StrategicTurnSource.objects.filter(strategic_turn__company=company).delete()
        StrategicTurn.objects.filter(company=company).exclude(
            turn_sources__source_document__source_api="MANUAL"
        ).delete()

        call_command(
            "extract_edgar_events",
            company=company.slug,
            forms=options["forms"],
            limit=options["limit"],
            oldest_first=True,
            reuse_extractions=options["reuse_extractions"],
        )
        call_command("recurate_events", company=company.slug, delete_old_turns=True)
        self.stdout.write(self.style.SUCCESS(f"Deleted and rebuilt {deleted_events} rule events."))

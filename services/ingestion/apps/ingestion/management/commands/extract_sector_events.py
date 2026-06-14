from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource


class Command(BaseCommand):
    help = "Rebuild SEC rule events for the cross-sector company universe."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--batch-size", type=int, default=0)
        parser.add_argument("--forms", default="10-K")
        parser.add_argument("--filing-limit", type=int, default=30)
        parser.add_argument("--skip-existing", action="store_true")
        parser.add_argument("--reuse-extractions", action="store_true")

    def handle(self, *args, **options):
        totals = {
            "companies": 0,
            "deleted_rule_events": 0,
            "events": 0,
            "turns": 0,
            "failed": 0,
        }

        seeds = CROSS_SECTOR_COMPANIES[options["offset"] : options["limit"]]
        if options["batch_size"]:
            seeds = seeds[: options["batch_size"]]
        if options["company"]:
            wanted_slug = slugify(options["company"])
            seeds = tuple(seed for seed in seeds if slugify(seed.name) == wanted_slug)

        for seed in seeds:
            company = Company.objects.get(slug=slugify(seed.name))
            if options["skip_existing"] and BusinessEvent.objects.filter(
                company=company,
                raw_extraction_json__extractor="sec_rules_v1",
            ).exists():
                self.stdout.write(f"{company.name}: skipped existing rule events")
                continue

            deleted = BusinessEvent.objects.filter(
                company=company,
                raw_extraction_json__extractor="sec_rules_v1",
            ).count()
            BusinessEvent.objects.filter(
                company=company,
                raw_extraction_json__extractor="sec_rules_v1",
            ).delete()
            StrategicTurnSource.objects.filter(strategic_turn__company=company).delete()
            StrategicTurn.objects.filter(company=company).exclude(
                turn_sources__source_document__source_api="MANUAL"
            ).delete()

            try:
                self.stdout.write(
                    f"{company.name}: extracting forms={options['forms']} "
                    f"filing_limit={options['filing_limit']}"
                )
                call_command(
                    "extract_edgar_events",
                    company=company.slug,
                    forms=options["forms"],
                    limit=options["filing_limit"],
                    oldest_first=True,
                    reuse_extractions=options["reuse_extractions"],
                    verbosity=0,
                )
                call_command("recurate_events", company=company.slug, delete_old_turns=True, verbosity=0)
                call_command("rebuild_specific_turns", company=company.slug, delete_generated=True, verbosity=0)
            except Exception as exc:
                totals["failed"] += 1
                self.stderr.write(f"{company.name}: extraction failed: {exc}")
                continue

            event_count = BusinessEvent.objects.filter(
                company=company,
                raw_extraction_json__extractor="sec_rules_v1",
            ).count()
            turn_count = StrategicTurn.objects.filter(company=company).count()
            totals["companies"] += 1
            totals["deleted_rule_events"] += deleted
            totals["events"] += event_count
            totals["turns"] += turn_count
            self.stdout.write(
                f"{company.name}: sector={company.industry}, deleted={deleted}, "
                f"events={event_count}, turns={turn_count}"
            )

        self.stdout.write(self.style.SUCCESS(f"Cross-sector event extraction complete: {totals}"))

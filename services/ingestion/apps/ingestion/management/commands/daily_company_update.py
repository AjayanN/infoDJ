from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Daily idempotent source refresh and event rebuild for the company ingestion service."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--sec-limit", type=int, default=30)
        parser.add_argument("--wikipedia-limit", type=int, default=10)
        parser.add_argument("--gdelt-records-per-query", type=int, default=5)
        parser.add_argument("--gdelt-query-limit", type=int, default=3)
        parser.add_argument("--skip-gdelt", action="store_true")
        parser.add_argument("--skip-event-extraction", action="store_true")
        parser.add_argument("--event-filing-limit", type=int, default=8)

    def handle(self, *args, **options):
        ingest_args = {
            "limit": options["limit"],
            "skip_wikidata": True,
            "skip_sec": False,
            "skip_wikipedia": False,
            "include_gdelt": not options["skip_gdelt"],
            "sec_limit": options["sec_limit"],
            "wikipedia_limit": options["wikipedia_limit"],
            "gdelt_records_per_query": options["gdelt_records_per_query"],
            "gdelt_query_limit": options["gdelt_query_limit"],
            "full_history": False,
            "daily_idempotent": True,
        }
        call_command("ingest_sector_companies", **ingest_args)

        if not options["skip_event_extraction"]:
            call_command(
                "extract_sector_events",
                limit=options["limit"],
                forms="10-K",
                filing_limit=options["event_filing_limit"],
                reuse_extractions=True,
            )

        self.stdout.write(self.style.SUCCESS("Daily company update complete."))


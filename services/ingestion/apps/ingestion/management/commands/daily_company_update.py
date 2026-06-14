from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Daily idempotent source refresh and event rebuild for the company ingestion service."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--batch-size", type=int, default=0)
        parser.add_argument("--sec-limit", type=int, default=30)
        parser.add_argument("--wikipedia-limit", type=int, default=10)
        parser.add_argument("--gdelt-records-per-query", type=int, default=5)
        parser.add_argument("--gdelt-query-limit", type=int, default=3)
        parser.add_argument("--skip-gdelt", action="store_true")
        parser.add_argument("--skip-event-extraction", action="store_true")
        parser.add_argument("--event-filing-limit", type=int, default=8)
        parser.add_argument("--retry-failed-only", action="store_true")
        parser.add_argument("--include-market-data", action="store_true")
        parser.add_argument("--include-financial-facts", action="store_true")
        parser.add_argument("--include-macro-context", action="store_true")
        parser.add_argument("--include-quality-scoring", action="store_true")
        parser.add_argument("--include-company-profiles", action="store_true")

    def handle(self, *args, **options):
        ingest_args = {
            "limit": options["limit"],
            "offset": options["offset"],
            "batch_size": options["batch_size"],
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
            "retry_failed_only": options["retry_failed_only"],
        }
        call_command("ingest_sector_companies", **ingest_args)

        if options["include_company_profiles"]:
            call_command(
                "refresh_company_profiles",
                limit=options["limit"],
                offset=options["offset"],
                batch_size=options["batch_size"],
                daily_idempotent=True,
                retry_failed_only=options["retry_failed_only"],
            )

        if options["include_financial_facts"]:
            call_command("ingest_sec_companyfacts", all=True, limit=500)

        if options["include_market_data"]:
            call_command("ingest_market_prices", days=30)

        if options["include_macro_context"]:
            self.stdout.write(
                self.style.WARNING(
                    "Macro context refresh requested but not implemented yet. "
                    "Next implementation source: FRED API."
                )
            )

        if not options["skip_event_extraction"]:
            extraction_offset = 0 if options["retry_failed_only"] else options["offset"]
            extraction_batch_size = 0 if options["retry_failed_only"] else options["batch_size"]
            call_command(
                "extract_sector_events",
                limit=options["limit"],
                offset=extraction_offset,
                batch_size=extraction_batch_size,
                forms="10-K",
                filing_limit=options["event_filing_limit"],
                reuse_extractions=True,
            )

        call_command("build_earnings_intelligence", collect_exhibits=True)

        if options["include_quality_scoring"]:
            self.stdout.write(
                self.style.WARNING(
                    "Data quality scoring requested but not implemented yet. "
                    "Next implementation: source count/type/review/conflict confidence scoring."
                )
            )

        self.stdout.write(self.style.SUCCESS("Daily company update complete."))

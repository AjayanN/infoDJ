from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.ingestion.services.source_gap_source_collector import collect_gap_sources


class Command(BaseCommand):
    help = "Collect official source documents targeted at currently open source gaps."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug to collect for.")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--filing-limit", type=int, default=120)
        parser.add_argument("--full-history", action="store_true")

    def handle(self, *args, **options):
        company = Company.objects.get(slug=options["company"]) if options["company"] else None
        result = collect_gap_sources(
            company=company,
            limit=options["limit"],
            filing_limit=options["filing_limit"],
            full_history=options["full_history"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Source gap collection complete: "
                f"companies_checked={result.companies_checked} "
                f"companies_collected={result.companies_collected} "
                f"sources_found={result.sources_found} "
                f"sources_inserted={result.sources_inserted} "
                f"duplicates_skipped={result.duplicates_skipped} "
                f"failed={result.failed}"
            )
        )

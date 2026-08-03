from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.sec_form4 import form4_sources, ingest_form4_sources


class Command(BaseCommand):
    help = "Parse already discovered SEC Forms 3, 4, and 5 into auditable insider transactions."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Process every active company.")
        parser.add_argument("--limit", type=int, default=100, help="Maximum ownership-form filings per company.")
        parser.add_argument("--offset", type=int, default=0, help="Company offset when processing a scheduled batch.")
        parser.add_argument("--company-limit", type=int, default=0, help="Maximum companies to process; 0 means all.")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        if options["offset"] < 0 or options["company_limit"] < 0:
            raise CommandError("--offset and --company-limit must not be negative.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else Company.objects.filter(slug=options["company"])
        if options["all"]:
            if options["company_limit"]:
                companies = companies[options["offset"] : options["offset"] + options["company_limit"]]
            else:
                companies = companies[options["offset"] :]
        if not companies.exists():
            raise CommandError(f"Company not found: {options['company']}")
        totals = {"companies": 0, "sources_seen": 0, "sources_parsed": 0, "sources_failed": 0, "transactions_found": 0, "transactions_inserted": 0, "transactions_updated": 0}
        for company in companies:
            result = ingest_form4_sources(company=company, sources=form4_sources(company, limit=options["limit"]))
            totals["companies"] += 1
            for key, value in result.items():
                totals[key] += value
            self.stdout.write(f"{company.slug}: {result}")
        self.stdout.write(self.style.SUCCESS(f"SEC ownership-form ingestion complete: {totals}"))

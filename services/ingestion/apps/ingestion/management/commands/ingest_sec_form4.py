from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobStatus, IngestionJobType, SourceDocument
from apps.ingestion.services.sec_edgar_client import discover_sec_filings_for_company
from apps.ingestion.services.sec_form4 import form4_sources, ingest_form4_sources


OWNERSHIP_FORMS = ("3", "3/A", "4", "4/A", "5", "5/A")


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
        totals = {
            "companies": 0,
            "sources_discovered": 0,
            "sources_seen": 0,
            "sources_parsed": 0,
            "sources_failed": 0,
            "transactions_found": 0,
            "transactions_inserted": 0,
            "transactions_updated": 0,
        }
        for company in companies:
            discovery = self._discover_sources(company, limit=options["limit"])
            totals["sources_discovered"] += discovery["sources_inserted"]
            result = ingest_form4_sources(company=company, sources=form4_sources(company, limit=options["limit"]))
            totals["companies"] += 1
            for key, value in result.items():
                totals[key] += value
            self.stdout.write(f"{company.slug}: {result}")
        self.stdout.write(self.style.SUCCESS(f"SEC ownership-form ingestion complete: {totals}"))

    def _discover_sources(self, company, *, limit: int) -> dict[str, int]:
        ticker = next(
            (seed.ticker for seed in CROSS_SECTOR_COMPANIES if slugify(seed.name) == company.slug),
            company.aliases[-1] if isinstance(company.aliases, list) and company.aliases else company.slug,
        )
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.SOURCE_DISCOVERY,
            source="SEC_EDGAR_FORM4",
            query=f"{ticker}: {', '.join(OWNERSHIP_FORMS)}",
            status=IngestionJobStatus.PENDING,
        )
        try:
            return discover_sec_filings_for_company(
                company=company,
                source_document_model=SourceDocument,
                ticker=ticker,
                forms=OWNERSHIP_FORMS,
                limit=limit,
                job=job,
            )
        except Exception as exc:
            self.stderr.write(f"Ownership-form discovery failed for {company.name}: {exc}")
            return {"sources_found": 0, "sources_inserted": 0, "duplicates_skipped": 0}

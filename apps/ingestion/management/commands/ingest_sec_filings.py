from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobType, SourceDocument
from apps.ingestion.services.sec_edgar_client import discover_sec_filings_for_company


class Command(BaseCommand):
    help = "Ingest SEC EDGAR filing metadata for a company."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="netflix")
        parser.add_argument("--ticker", default="NFLX")
        parser.add_argument("--forms", default="10-K,10-Q,8-K,S-1,S-1/A")
        parser.add_argument("--limit", type=int, default=250)
        parser.add_argument("--full-history", action="store_true")

    def handle(self, *args, **options):
        company = Company.objects.get(slug=options["company"])
        forms = tuple(form.strip() for form in options["forms"].split(",") if form.strip())
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.SOURCE_DISCOVERY,
            source="SEC_EDGAR",
            query=f"{options['ticker']}: {', '.join(forms)} full_history={options['full_history']}",
            status="PENDING",
        )
        counters = discover_sec_filings_for_company(
            company=company,
            source_document_model=SourceDocument,
            ticker=options["ticker"],
            forms=forms,
            limit=options["limit"],
            full_history=options["full_history"],
            job=job,
        )
        self.stdout.write(self.style.SUCCESS(f"SEC EDGAR ingestion complete: {counters}"))

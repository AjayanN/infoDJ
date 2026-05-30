from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobType, SourceDocument
from apps.ingestion.services.wikipedia_client import WikipediaClient, store_wikipedia_sources


class Command(BaseCommand):
    help = "Ingest Wikipedia page and reference URLs as source documents."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="netflix")
        parser.add_argument("--query", default="")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        company = Company.objects.get(slug=options["company"])
        query = options["query"] or company.name
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.SOURCE_DISCOVERY,
            source="WIKIPEDIA_REFERENCES",
            query=query,
            status="RUNNING",
        )
        try:
            sources = WikipediaClient().discover_sources(query, limit=options["limit"])
            counters = store_wikipedia_sources(
                company=company,
                sources=sources,
                source_document_model=SourceDocument,
            )
            for key, value in counters.items():
                setattr(job, key, value)
            job.status = "SUCCEEDED"
            job.save()
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            job.save()
            raise
        self.stdout.write(self.style.SUCCESS(f"Wikipedia ingestion complete: {counters}"))

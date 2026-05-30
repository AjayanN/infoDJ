from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import ArticleExtraction, IngestionJob, IngestionJobType, SourceDocument
from apps.ingestion.services.article_extractor import extract_source_document
from apps.ingestion.services.event_extractor import (
    create_strategic_turns_from_events,
    extract_business_events_from_sec_filing,
)


class Command(BaseCommand):
    help = "Extract SEC EDGAR filing text and create reviewable business events."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="netflix")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--forms", default="")
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--reuse-extractions", action="store_true")

    def handle(self, *args, **options):
        company = Company.objects.get(slug=options["company"])
        limit = options["limit"]
        sources_query = SourceDocument.objects.filter(company=company, source_api="SEC_EDGAR").exclude(status="IGNORED")
        forms = tuple(form.strip() for form in options["forms"].split(",") if form.strip())
        if forms:
            form_filter = Q()
            for form in forms:
                form_filter |= Q(title__icontains=f" {form} filing ")
            sources_query = sources_query.filter(form_filter)
        ordering = "published_date" if options["oldest_first"] else "-published_date"
        sources = list(sources_query.order_by(ordering)[:limit])

        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.EVENT_EXTRACTION,
            source="SEC_EDGAR",
            query=f"extract_edgar_events limit={limit} forms={','.join(forms)} oldest_first={options['oldest_first']}",
            status="RUNNING",
        )

        articles_extracted = 0
        events_created = 0
        try:
            with transaction.atomic():
                for source in sources:
                    extraction = None
                    if options["reuse_extractions"]:
                        extraction = ArticleExtraction.objects.filter(
                            source_document=source,
                            extraction_status="SUCCEEDED",
                        ).first()
                    if extraction is None:
                        extraction = extract_source_document(
                            source,
                            article_extraction_model=ArticleExtraction,
                        )
                    if extraction.extraction_status == "SUCCEEDED":
                        articles_extracted += 1
                    events = extract_business_events_from_sec_filing(
                        company=company,
                        source_document=source,
                        article_extraction=extraction,
                        business_event_model=BusinessEvent,
                    )
                    events_created += len(events)

                turns = create_strategic_turns_from_events(
                    company=company,
                    business_event_model=BusinessEvent,
                    strategic_turn_model=StrategicTurn,
                    strategic_turn_source_model=StrategicTurnSource,
                )

                job.status = "SUCCEEDED"
                job.articles_extracted = articles_extracted
                job.events_extracted = events_created
                job.turns_created = len(turns)
                job.save()
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            job.save()
            raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Extracted {articles_extracted} filings, created {events_created} events, "
                f"updated {len(turns)} strategic turns."
            )
        )

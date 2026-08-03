from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.ingestion.models import ArticleExtraction, SourceDocument
from apps.ingestion.services.article_extractor import ArticleExtractor, extract_source_document


REPORT_FORMS = ("10-K", "10-Q", "8-K", "DEF 14A")


class Command(BaseCommand):
    help = "Extract primary SEC report text for evidence review without creating business events."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--timeout", type=float, default=10.0)
        parser.add_argument("--retry-failed", action="store_true")

    def handle(self, *args, **options):
        form_filter = Q()
        for form in REPORT_FORMS:
            form_filter |= Q(title__icontains=f" {form} filing ")
        sources = SourceDocument.objects.filter(source_api="SEC_EDGAR").filter(form_filter)
        if not options["retry_failed"]:
            sources = sources.exclude(article_extraction__extraction_status="SUCCEEDED").exclude(
                article_extraction__extraction_status="FAILED"
            )
        sources = list(sources.order_by("company_id", "-published_date")[options["offset"] : options["offset"] + options["limit"]])

        extracted = 0
        failed = 0
        for source in sources:
            result = extract_source_document(
                source,
                article_extraction_model=ArticleExtraction,
                extractor=ArticleExtractor(timeout=options["timeout"]),
            )
            if result.extraction_status == "SUCCEEDED":
                extracted += 1
            else:
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Report filing extraction complete: "
                f"checked={len(sources)} extracted={extracted} failed={failed}"
            )
        )

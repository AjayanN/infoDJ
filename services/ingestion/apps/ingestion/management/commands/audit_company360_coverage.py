from django.core.management.base import BaseCommand
from django.db.models import Count, Max

from apps.companies.models import Company
from apps.ingestion.models import ArticleExtraction, MarketPrice, SourceDocument


class Command(BaseCommand):
    help = "Report source, extraction, and Company 360 coverage without changing data."

    def handle(self, *args, **options):
        self.stdout.write(f"Active companies: {Company.objects.filter(is_active=True).count()}")
        self.stdout.write(f"Source documents: {SourceDocument.objects.count()}")
        self.stdout.write(f"Successful extractions: {ArticleExtraction.objects.filter(extraction_status='SUCCEEDED').count()}")
        self.stdout.write(f"Market prices: {MarketPrice.objects.count()}")
        self.stdout.write("\nPer-company source and market coverage:")
        companies = Company.objects.filter(is_active=True).annotate(
            source_count=Count("source_documents", distinct=True),
            extraction_count=Count("source_documents__article_extraction", distinct=True),
            price_count=Count("market_prices", distinct=True),
            latest_price=Max("market_prices__price_date"),
        ).order_by("name")
        for company in companies:
            self.stdout.write(
                f"{company.slug}: sources={company.source_count}, extractions={company.extraction_count}, "
                f"market_prices={company.price_count}, latest_price={company.latest_price or 'missing'}"
            )

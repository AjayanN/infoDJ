from django.core.management.base import BaseCommand
from apps.companies.models import Company, DependencyContractTerm, InsiderTransaction, PriceObservation
from apps.ingestion.models import ArticleExtraction, FinancialFact, MarketPrice, SourceDocument


class Command(BaseCommand):
    help = "Report source, extraction, and Company 360 coverage without changing data."

    def handle(self, *args, **options):
        self.stdout.write(f"Active companies: {Company.objects.filter(is_active=True).count()}")
        self.stdout.write(f"Source documents: {SourceDocument.objects.count()}")
        self.stdout.write(f"Successful extractions: {ArticleExtraction.objects.filter(extraction_status='SUCCEEDED').count()}")
        self.stdout.write(f"SEC financial facts: {FinancialFact.objects.count()}")
        self.stdout.write(f"Market prices: {MarketPrice.objects.count()}")
        self.stdout.write(f"Insider transactions: {InsiderTransaction.objects.count()}")
        self.stdout.write(f"Product price observations: {PriceObservation.objects.count()}")
        self.stdout.write(f"Dependency contract terms: {DependencyContractTerm.objects.count()}")
        self.stdout.write("\nPer-company source and market coverage:")
        for company in Company.objects.filter(is_active=True).order_by("name"):
            source_count = SourceDocument.objects.filter(company=company).count()
            extraction_count = ArticleExtraction.objects.filter(source_document__company=company, extraction_status="SUCCEEDED").count()
            prices = MarketPrice.objects.filter(company=company)
            financial_facts = FinancialFact.objects.filter(company=company)
            insider_transaction_count = InsiderTransaction.objects.filter(snapshot__company=company).count()
            self.stdout.write(
                f"{company.slug}: sources={source_count}, extractions={extraction_count}, "
                f"market_prices={prices.count()}, latest_price={prices.order_by('-price_date').values_list('price_date', flat=True).first() or 'missing'}, "
                f"financial_facts={financial_facts.count()}, latest_financial_filing={financial_facts.order_by('-filed').values_list('filed', flat=True).first() or 'missing'}, "
                f"insider_transactions={insider_transaction_count}"
            )

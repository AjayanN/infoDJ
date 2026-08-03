import requests

from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_client import robots_allows
from apps.ingestion.services.official_product_price import store_official_prices
from apps.ingestion.services.wikidata_client import DEFAULT_USER_AGENT


class Command(BaseCommand):
    help = "Ingest explicit JSON-LD prices from stored, robots-permitted first-party pages."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug. Omit with --all.")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--limit", type=int, default=3, help="Maximum official pages per company.")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else Company.objects.filter(slug=options["company"])
        if not companies.exists():
            raise CommandError(f"Company not found: {options['company']}")
        totals = {"pages_seen": 0, "pages_skipped": 0, "pages_failed": 0, "prices_found": 0, "prices_inserted": 0, "prices_updated": 0, "skipped": 0}
        session = requests.Session()
        session.headers["User-Agent"] = DEFAULT_USER_AGENT
        for company in companies:
            pages = SourceDocument.objects.filter(company=company, source_api="OFFICIAL_WEBSITE").order_by("-updated_at")[: options["limit"]]
            for page in pages:
                totals["pages_seen"] += 1
                try:
                    if not robots_allows(page.url, session=session):
                        totals["pages_skipped"] += 1
                        continue
                    response = session.get(page.url, timeout=20)
                    response.raise_for_status()
                    result = store_official_prices(company=company, source=page, html=response.text)
                except (requests.RequestException, PermissionError):
                    totals["pages_failed"] += 1
                    continue
                for key in ("prices_found", "prices_inserted", "prices_updated", "skipped"):
                    totals[key] += result[key]
        self.stdout.write(self.style.SUCCESS(f"Official product-price ingestion complete: {totals}"))

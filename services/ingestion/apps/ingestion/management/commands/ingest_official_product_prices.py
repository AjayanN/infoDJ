import requests

from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_client import robots_allows
from apps.ingestion.services.company_profile_client import official_product_price_links
from apps.ingestion.services.official_product_price import store_official_prices
from apps.ingestion.services.url_utils import url_hash
from apps.ingestion.services.wikidata_client import DEFAULT_USER_AGENT


class Command(BaseCommand):
    help = "Ingest explicit JSON-LD prices from stored, robots-permitted first-party pages."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug. Omit with --all.")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--limit", type=int, default=3, help="Maximum official pages per company.")
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--company-limit", type=int, default=0)

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else Company.objects.filter(slug=options["company"])
        if options["all"]:
            companies = companies[options["offset"] : options["offset"] + options["company_limit"]] if options["company_limit"] else companies[options["offset"] :]
        if not companies.exists():
            raise CommandError(f"Company not found: {options['company']}")
        totals = {"pages_seen": 0, "pages_discovered": 0, "pages_skipped": 0, "pages_failed": 0, "prices_found": 0, "prices_inserted": 0, "prices_updated": 0, "skipped": 0}
        session = requests.Session()
        session.headers["User-Agent"] = DEFAULT_USER_AGENT
        for company in companies:
            pages = prioritized_official_pages(company, limit=options["limit"])
            seen_urls = {page.url for page in pages}
            page_index = 0
            while page_index < len(pages) and page_index < options["limit"]:
                page = pages[page_index]
                page_index += 1
                totals["pages_seen"] += 1
                try:
                    if not robots_allows(page.url, session=session):
                        totals["pages_skipped"] += 1
                        continue
                    response = session.get(page.url, timeout=20)
                    response.raise_for_status()
                    result = store_official_prices(company=company, source=page, html=response.text)
                    for link in official_product_price_links(response.text, base_url=response.url or page.url):
                        _source, created = SourceDocument.objects.get_or_create(
                            url_hash=url_hash(link),
                            defaults={"company": company, "source_api": "OFFICIAL_WEBSITE", "url": link, "canonical_url": link, "title": f"{company.name} official product or pricing page", "publisher": company.name, "language": "en", "status": "DISCOVERED"},
                        )
                        totals["pages_discovered"] += 1 if created else 0
                        if created and link not in seen_urls and len(pages) < options["limit"]:
                            pages.append(_source)
                            seen_urls.add(link)
                except (requests.RequestException, PermissionError):
                    totals["pages_failed"] += 1
                    continue
                for key in ("prices_found", "prices_inserted", "prices_updated", "skipped"):
                    totals[key] += result[key]
        self.stdout.write(self.style.SUCCESS(f"Official product-price ingestion complete: {totals}"))


def prioritized_official_pages(company: Company, *, limit: int) -> list[SourceDocument]:
    """Prefer discovered product or pricing URLs before falling back to general first-party pages."""

    if limit <= 0:
        return []
    pages = list(
        SourceDocument.objects.filter(company=company, source_api="OFFICIAL_WEBSITE")
        .order_by("-updated_at", "-id")
    )
    price_words = ("pricing", "prices", "price", "plans", "products", "product", "store", "shop", "buy")
    return sorted(
        pages,
        key=lambda page: (
            not any(word in f"{page.title} {page.url}".lower() for word in price_words),
            -page.updated_at.timestamp(),
            -page.id,
        ),
    )[:limit]

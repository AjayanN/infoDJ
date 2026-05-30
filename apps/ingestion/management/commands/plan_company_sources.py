import json

from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.ingestion.services.source_router import build_company_source_plan


class Command(BaseCommand):
    help = "Print a stage/year based source plan for a company."

    def add_arguments(self, parser):
        parser.add_argument("company_slug")
        parser.add_argument("--founded-year", type=int)
        parser.add_argument("--public-listing-year", type=int)
        parser.add_argument("--ticker", default="")

    def handle(self, *args, **options):
        company = Company.objects.get(slug=options["company_slug"])
        routes = build_company_source_plan(
            company,
            founded_year=options["founded_year"],
            public_listing_year=options["public_listing_year"],
            ticker=options["ticker"],
        )
        payload = {
            "company": company.name,
            "slug": company.slug,
            "wikidata_id": company.wikidata_id,
            "sec_cik": company.sec_cik,
            "routes": [
                {
                    "stage": route.stage,
                    "year_start": route.year_start,
                    "year_end": route.year_end,
                    "primary_sources": route.primary_sources,
                    "supporting_sources": route.supporting_sources,
                    "collector_priority": route.collector_priority,
                    "notes": route.notes,
                }
                for route in routes
            ],
        }
        self.stdout.write(json.dumps(payload, indent=2))

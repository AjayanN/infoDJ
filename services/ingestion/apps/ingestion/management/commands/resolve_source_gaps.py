from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.ingestion.services.source_gap_resolver import resolve_source_gaps


class Command(BaseCommand):
    help = "Create source-backed resolution candidates for open source gaps."

    def add_arguments(self, parser):
        parser.add_argument("--company", type=str, default="")
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args, **options):
        company = None
        if options["company"]:
            company = Company.objects.get(slug=options["company"])
        result = resolve_source_gaps(company=company, limit=options["limit"])
        self.stdout.write(
            self.style.SUCCESS(
                "Resolved source gap candidates: "
                f"gaps_checked={result.gaps_checked} "
                f"created={result.candidates_created} "
                f"updated={result.candidates_updated}"
            )
        )

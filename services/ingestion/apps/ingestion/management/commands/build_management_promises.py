from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.services.management_promise_builder import build_promise_candidates_from_kpi_targets
from apps.ingestion.services.reviewed_management_promises import build_reviewed_management_promise


class Command(BaseCommand):
    help = "Build reviewed filing-backed promises and unpublished KPI-target candidates."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="", help="Optional company slug; defaults to the full universe")

    def handle(self, *args, **options):
        slugs = [slugify(seed.name) for seed in CROSS_SECTOR_COMPANIES]
        if options["company"]:
            slugs = [slugify(options["company"])]
        companies = {row.slug: row for row in Company.objects.filter(slug__in=slugs)}
        missing = [slug for slug in slugs if slug not in companies]
        if missing:
            raise CommandError(f"Unknown companies: {', '.join(missing)}")

        totals = {
            "reviewed_created": 0,
            "reviewed_updated": 0,
            "reviewed_skipped": 0,
            "candidates_created": 0,
            "candidates_updated": 0,
            "candidates_skipped": 0,
        }
        for slug in slugs:
            company = companies[slug]
            reviewed = build_reviewed_management_promise(company)
            candidates = build_promise_candidates_from_kpi_targets(company)
            totals["reviewed_created"] += reviewed["created"]
            totals["reviewed_updated"] += reviewed["updated"]
            totals["reviewed_skipped"] += reviewed["skipped"]
            for key in ("created", "updated", "skipped"):
                totals[f"candidates_{key}"] += candidates[key]
            self.stdout.write(f"{company.name}: reviewed={reviewed} candidates={candidates}")
        self.stdout.write(self.style.SUCCESS(f"Management promise build complete: {totals}"))

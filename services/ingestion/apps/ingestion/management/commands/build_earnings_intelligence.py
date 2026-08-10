from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.services.earnings_intelligence import build_earnings_periods, collect_earnings_exhibits, collect_latest_earnings_exhibit


class Command(BaseCommand):
    help = "Build source-backed quarterly Earnings Intelligence periods."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="", help="Optional company slug")
        parser.add_argument("--collect-exhibits", action="store_true")
        parser.add_argument("--all-periods", action="store_true", help="Collect earnings exhibits for every published period.")

    def handle(self, *args, **options):
        slugs = [slugify(seed.name) for seed in CROSS_SECTOR_COMPANIES]
        if options["company"]:
            slugs = [slugify(options["company"])]
        companies = {row.slug: row for row in Company.objects.filter(slug__in=slugs)}
        missing = [slug for slug in slugs if slug not in companies]
        if missing:
            raise CommandError(f"Unknown companies: {', '.join(missing)}")
        totals = {"created": 0, "updated": 0, "skipped": 0}
        for slug in slugs:
            result = build_earnings_periods(companies[slug])
            for key in totals:
                totals[key] += result[key]
            self.stdout.write(f"{companies[slug].name}: {result}")
            if options["collect_exhibits"]:
                collector = collect_earnings_exhibits if options["all_periods"] else collect_latest_earnings_exhibit
                self.stdout.write(f"{companies[slug].name} exhibit: {collector(companies[slug])}")
        self.stdout.write(self.style.SUCCESS(f"Earnings Intelligence build complete: {totals}"))

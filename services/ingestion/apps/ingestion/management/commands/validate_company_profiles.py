from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.services.company_profile_quality import company_profile_quality_issues


class Command(BaseCommand):
    help = "Validate semantic Company 360 and Business Model Map quality for the configured company universe."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--company", default="", help="Optional company slug")

    def handle(self, *args, **options):
        seeds = CROSS_SECTOR_COMPANIES[: options["limit"]]
        if options["company"]:
            seeds = tuple(seed for seed in seeds if slugify(seed.name) == slugify(options["company"]))

        failures = {}
        for seed in seeds:
            company = Company.objects.filter(slug=slugify(seed.name)).first()
            issues = ["company record unavailable"] if company is None else company_profile_quality_issues(company)
            if issues:
                failures[seed.name] = issues
                self.stderr.write(f"{seed.name}: FAILED - {'; '.join(issues)}")
            else:
                self.stdout.write(self.style.SUCCESS(f"{seed.name}: passed"))

        if failures:
            raise CommandError(f"Company profile semantic validation failed for {len(failures)} companies.")
        self.stdout.write(self.style.SUCCESS(f"Company profile semantic validation passed for {len(seeds)} companies."))

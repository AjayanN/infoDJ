from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.services.earnings_intelligence import earnings_quality_issues


class Command(BaseCommand):
    help = "Validate Earnings Intelligence coverage for every configured company."

    def handle(self, *args, **options):
        failures = {}
        for seed in CROSS_SECTOR_COMPANIES:
            company = Company.objects.filter(slug=slugify(seed.name)).first()
            issues = ["company record unavailable"] if company is None else earnings_quality_issues(company)
            if issues:
                failures[seed.name] = issues
                self.stderr.write(f"{seed.name}: FAILED - {'; '.join(issues)}")
            else:
                self.stdout.write(self.style.SUCCESS(f"{seed.name}: passed"))
        if failures:
            raise CommandError(f"Earnings Intelligence validation failed for {len(failures)} companies.")
        self.stdout.write(self.style.SUCCESS("Earnings Intelligence validation passed for 20 companies."))

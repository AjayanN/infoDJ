from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.services.reviewed_strategy_milestones import build_reviewed_strategy_milestone


class Command(BaseCommand):
    help = "Build the reviewed Strategy Milestone Tracker baseline."

    def handle(self, *args, **options):
        failures = []
        for seed in CROSS_SECTOR_COMPANIES:
            company = Company.objects.filter(slug=slugify(seed.name)).first()
            result = {"created": 0, "updated": 0, "skipped": 1, "reason": "company unavailable"} if company is None else build_reviewed_strategy_milestone(company)
            self.stdout.write(f"{seed.name}: {result}")
            if result["skipped"]:
                failures.append(seed.name)
        if failures:
            raise CommandError(f"Strategy milestone build failed for: {', '.join(failures)}")
        self.stdout.write(self.style.SUCCESS("Strategy milestone build passed for 20 companies."))

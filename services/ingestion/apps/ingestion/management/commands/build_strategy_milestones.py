from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.services.reviewed_strategy_milestones import build_reviewed_strategy_milestone


class Command(BaseCommand):
    help = "Build the reviewed Strategy Milestone Tracker baseline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail when a configured company has no reviewed source-backed milestone.",
        )

    def handle(self, *args, **options):
        skipped = []
        for seed in CROSS_SECTOR_COMPANIES:
            company = Company.objects.filter(slug=slugify(seed.name)).first()
            result = {"created": 0, "updated": 0, "skipped": 1, "reason": "company unavailable"} if company is None else build_reviewed_strategy_milestone(company)
            self.stdout.write(f"{seed.name}: {result}")
            if result["skipped"]:
                skipped.append(f"{seed.name} ({result['reason']})")
        if skipped and options["strict"]:
            raise CommandError(f"Strategy milestone build incomplete for: {', '.join(skipped)}")
        if skipped:
            self.stdout.write(self.style.WARNING(f"Strategy milestones skipped: {', '.join(skipped)}"))
        self.stdout.write(self.style.SUCCESS("Strategy milestone build completed."))

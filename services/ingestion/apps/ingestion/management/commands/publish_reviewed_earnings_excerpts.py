from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.services.earnings_intelligence import (
    publish_reviewed_earnings_excerpt,
    publish_reviewed_guidance_comparisons,
)


class Command(BaseCommand):
    help = "Publish the editorially reviewed earnings-explanation baseline."

    def handle(self, *args, **options):
        failures = []
        for seed in CROSS_SECTOR_COMPANIES:
            slug = slugify(seed.name)
            company = Company.objects.filter(slug=slug).first()
            result = {"reviewed": 0, "skipped": 1, "reason": "company unavailable"} if company is None else publish_reviewed_earnings_excerpt(company)
            self.stdout.write(f"{seed.name}: {result}")
            if result["skipped"]:
                failures.append(seed.name)
            if company is not None and company.slug == "netflix":
                self.stdout.write(f"{seed.name} guidance: {publish_reviewed_guidance_comparisons(company)}")
        if failures:
            raise CommandError(f"Reviewed earnings excerpts unavailable for: {', '.join(failures)}")
        self.stdout.write(self.style.SUCCESS("Published reviewed earnings excerpts for 20 companies."))

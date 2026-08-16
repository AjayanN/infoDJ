from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company


class Command(BaseCommand):
    help = "Create or activate every configured cross-sector company without overwriting reviewed metadata."

    def handle(self, *args, **options):
        created = 0
        activated = 0
        for seed in CROSS_SECTOR_COMPANIES:
            company, was_created = Company.objects.get_or_create(
                slug=slugify(seed.name),
                defaults={
                    "name": seed.name,
                    "industry": seed.sector,
                    "country": seed.country,
                    "headquarters_country": seed.country,
                    "aliases": [seed.ticker],
                    "website": seed.website,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                continue
            changed_fields = []
            if not company.is_active:
                company.is_active = True
                activated += 1
                changed_fields.append("is_active")
            if not company.industry:
                company.industry = seed.sector
                changed_fields.append("industry")
            if not company.country:
                company.country = seed.country
                changed_fields.append("country")
            if not company.headquarters_country:
                company.headquarters_country = seed.country
                changed_fields.append("headquarters_country")
            if seed.ticker not in (company.aliases or []):
                company.aliases = [*(company.aliases or []), seed.ticker]
                changed_fields.append("aliases")
            if not company.website and seed.website:
                company.website = seed.website
                changed_fields.append("website")
            if changed_fields:
                company.save(update_fields=[*changed_fields, "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"Company universe ready: created={created}, activated={activated}, active={Company.objects.filter(is_active=True).count()}"))

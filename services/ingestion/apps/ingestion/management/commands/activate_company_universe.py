from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company


class Command(BaseCommand):
    help = "Create or activate every configured cross-sector company without overwriting reviewed metadata."

    @staticmethod
    def _company_defaults(seed):
        return {
            "name": seed.name,
            "industry": seed.sector,
            "country": seed.country,
            "headquarters_country": seed.country,
            "aliases": [seed.ticker],
            "website": seed.website,
            "sec_cik": seed.sec_cik,
            "is_active": True,
        }

    @staticmethod
    def _apply_missing_metadata(company, seed):
        desired_values = {
            "is_active": True,
            "industry": company.industry or seed.sector,
            "country": company.country or seed.country,
            "headquarters_country": company.headquarters_country or seed.country,
            "aliases": list(dict.fromkeys([*(company.aliases or []), seed.ticker])),
            "website": company.website or seed.website,
            "sec_cik": seed.sec_cik or company.sec_cik,
        }
        changed_fields = [
            field
            for field, value in desired_values.items()
            if getattr(company, field) != value
        ]
        for field in changed_fields:
            setattr(company, field, desired_values[field])
        if changed_fields:
            company.save(update_fields=[*changed_fields, "updated_at"])
        return "is_active" in changed_fields

    def handle(self, *args, **options):
        created = 0
        activated = 0
        for seed in CROSS_SECTOR_COMPANIES:
            company, was_created = Company.objects.get_or_create(
                slug=slugify(seed.name),
                defaults=self._company_defaults(seed),
            )
            if was_created:
                created += 1
                continue
            activated += self._apply_missing_metadata(company, seed)
        self.stdout.write(self.style.SUCCESS(f"Company universe ready: created={created}, activated={activated}, active={Company.objects.filter(is_active=True).count()}"))

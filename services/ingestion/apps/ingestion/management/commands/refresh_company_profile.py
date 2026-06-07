from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.company_profile_client import collect_official_company_profile


class Command(BaseCommand):
    help = "Collect a draft Company 360 snapshot from the official company website."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True, help="Company slug")

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(slug=options["company"])
        except Company.DoesNotExist as exc:
            raise CommandError(f"Unknown company: {options['company']}") from exc

        snapshot = collect_official_company_profile(company)
        self.stdout.write(
            self.style.SUCCESS(
                f"Collected draft Company 360 snapshot for {company.name} at {snapshot.effective_date}."
            )
        )

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.business_model_builder import collect_business_model_page


class Command(BaseCommand):
    help = "Collect a permitted current or archived page as draft business-model evidence."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True, help="Company slug")
        parser.add_argument("--url", required=True)
        parser.add_argument("--effective-date", required=True, help="YYYY-MM-DD")

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(slug=options["company"])
        except Company.DoesNotExist as exc:
            raise CommandError(f"Unknown company: {options['company']}") from exc
        try:
            effective_date = date.fromisoformat(options["effective_date"])
        except ValueError as exc:
            raise CommandError("--effective-date must use YYYY-MM-DD") from exc
        snapshot = collect_business_model_page(
            company,
            url=options["url"],
            effective_date=effective_date,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Collected draft business-model source for {company.name} at {snapshot.effective_date}."
            )
        )

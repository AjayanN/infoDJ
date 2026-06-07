from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.business_model_builder import build_business_model_from_profile


class Command(BaseCommand):
    help = "Build a draft business-model map from the latest reviewed Company 360 profile."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True, help="Company slug")

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(slug=options["company"])
        except Company.DoesNotExist as exc:
            raise CommandError(f"Unknown company: {options['company']}") from exc
        try:
            snapshot = build_business_model_from_profile(company)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Built draft business-model map for {company.name} at {snapshot.effective_date}."
            )
        )

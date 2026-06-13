from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.management_promise_builder import build_promise_candidates_from_kpi_targets


class Command(BaseCommand):
    help = "Build unpublished management-promise candidates from source-backed KPI targets."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True, help="Company slug")

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(slug=options["company"])
        except Company.DoesNotExist as exc:
            raise CommandError(f"Unknown company: {options['company']}") from exc
        counters = build_promise_candidates_from_kpi_targets(company)
        self.stdout.write(self.style.SUCCESS(f"Management promise candidate build complete: {counters}"))

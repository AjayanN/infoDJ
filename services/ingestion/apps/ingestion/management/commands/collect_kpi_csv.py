from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.kpi_collector import collect_kpi_csv


class Command(BaseCommand):
    help = "Collect a permitted official KPI CSV into inactive records for analyst review."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True)
        parser.add_argument("--url", required=True)
        parser.add_argument("--metric-slug", required=True)
        parser.add_argument("--metric-name", required=True)
        parser.add_argument("--unit", required=True)

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(slug=options["company"])
            kpi, count = collect_kpi_csv(
                company, url=options["url"], metric_slug=options["metric_slug"],
                metric_name=options["metric_name"], unit=options["unit"],
            )
        except Company.DoesNotExist as exc:
            raise CommandError(f"Unknown company: {options['company']}") from exc
        except (KeyError, ValueError) as exc:
            raise CommandError(f"Invalid KPI CSV: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Collected {count} observations for inactive KPI {kpi.slug}; review required."))

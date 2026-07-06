from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company, KpiDefinition


class Command(BaseCommand):
    help = "Validate all-company Operating KPI baseline depth from reviewed SEC-backed KPI rows."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Validate every active company.")
        parser.add_argument("--min-definitions", type=int, default=1)
        parser.add_argument("--min-observations", type=int, default=1)

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else Company.objects.filter(slug=options["company"])
        if not companies.exists():
            raise CommandError(f"Company not found: {options['company']}")

        failures = []
        checked = 0
        for company in companies:
            definitions = KpiDefinition.objects.filter(
                company=company,
                is_active=True,
                scope="Company-wide reported financial context",
            ).prefetch_related("observations")
            definition_count = definitions.count()
            observation_count = sum(definition.observations.count() for definition in definitions)
            annual_count = sum(definition.observations.count() for definition in definitions if definition.cadence == "ANNUAL")
            quarterly_count = sum(definition.observations.count() for definition in definitions if definition.cadence == "QUARTERLY")
            checked += 1
            self.stdout.write(
                f"{company.slug}: definitions={definition_count} observations={observation_count} "
                f"annual={annual_count} quarterly={quarterly_count}"
            )
            if definition_count < options["min_definitions"]:
                failures.append(f"{company.slug}: only {definition_count} baseline definitions")
            if observation_count < options["min_observations"]:
                failures.append(f"{company.slug}: only {observation_count} baseline observations")
            if annual_count == 0 and quarterly_count == 0:
                failures.append(f"{company.slug}: no annual or quarterly baseline observations")

        if failures:
            raise CommandError("Operating KPI baseline validation failed:\n" + "\n".join(failures))
        self.stdout.write(self.style.SUCCESS(f"Operating KPI baseline validation passed for {checked} companies."))

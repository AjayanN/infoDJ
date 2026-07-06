from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company, CompanyProfileStatus


class Command(BaseCommand):
    help = "Validate reviewed Geographic Expansion coverage and guardrails."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Validate every active company.")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else Company.objects.filter(slug=options["company"])
        if not companies.exists():
            raise CommandError(f"Company not found: {options['company']}")

        failures = []
        checked = 0
        for company in companies:
            snapshot = (
                company.geographic_expansion_snapshots.filter(status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
                .prefetch_related("markets")
                .order_by("-effective_date", "-updated_at")
                .first()
            )
            if snapshot is None:
                failures.append(f"{company.slug}: no reviewed geographic expansion snapshot")
                continue
            markets = list(snapshot.markets.all())
            if not markets:
                failures.append(f"{company.slug}: no reviewed geographic markets")
                continue
            invalid = [row.geography for row in markets if not row.geography or row.geography.lower() in {"unknown", "n/a", "none"}]
            if invalid:
                failures.append(f"{company.slug}: invalid geography labels: {invalid[:5]}")
            revenue_without_currency = [row.geography for row in markets if row.revenue_contribution is not None and not row.revenue_currency]
            if revenue_without_currency:
                failures.append(f"{company.slug}: revenue contribution without currency: {revenue_without_currency[:5]}")
            if not all(row.market_type for row in markets):
                failures.append(f"{company.slug}: market row without geography level")
            checked += 1
            self.stdout.write(
                f"{company.slug}: markets={len(markets)} dated={sum(1 for row in markets if row.entry_date or row.exit_date)} "
                f"revenue={sum(1 for row in markets if row.revenue_contribution is not None)}"
            )

        if failures:
            raise CommandError("Geographic expansion validation failed:\n" + "\n".join(failures))
        self.stdout.write(self.style.SUCCESS(f"Geographic expansion validation passed for {checked} companies."))

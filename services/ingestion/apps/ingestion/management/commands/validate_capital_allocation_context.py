from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import CapitalAllocationCategory, Company, PromiseReviewStatus
from apps.ingestion.services.capital_allocation import DEPLOYMENT_CATEGORIES


class Command(BaseCommand):
    help = "Validate capital allocation reported/adjusted/currency guardrails for reviewed published periods."

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
            periods = company.capital_allocation_periods.filter(
                is_published=True,
                review_status=PromiseReviewStatus.REVIEWED,
            ).prefetch_related("items")
            if not periods.exists():
                failures.append(f"{company.slug}: no reviewed published capital allocation periods")
                continue
            latest = periods.order_by("-period_end", "-filed_date").first()
            items = list(latest.items.filter(review_status=PromiseReviewStatus.REVIEWED))
            deployment_items = [row for row in items if row.category in DEPLOYMENT_CATEGORIES and not row.is_context]
            context_categories = {CapitalAllocationCategory.CASH_CONTEXT, CapitalAllocationCategory.OPERATING_CASH_FLOW}
            if not any(row.source_fact_id and not row.is_calculated for row in items):
                failures.append(f"{company.slug}: no reported SEC source-backed rows")
            deployment_units = {row.unit for row in deployment_items if row.unit}
            non_usd_units = {row.unit for row in items if row.unit and row.unit.upper() != "USD"}
            if len(deployment_units) > 1:
                failures.append(f"{company.slug}: mixed deployment units require reviewed currency conversion: {sorted(deployment_units)}")
            if non_usd_units:
                failures.append(f"{company.slug}: non-USD units require reviewed currency conversion: {sorted(non_usd_units)}")
            if latest.total_deployment is not None and not deployment_items:
                failures.append(f"{company.slug}: total deployment exists without deployment rows")
            if any(row.category in context_categories and not row.is_context for row in items):
                failures.append(f"{company.slug}: cash or operating-cash-flow context row marked as deployment")
            checked += 1
            self.stdout.write(
                f"{company.slug}: periods={periods.count()} latest={latest.period_end.isoformat()} "
                f"items={len(items)} deployment_units={sorted(deployment_units) or ['none']} adjusted=unavailable"
            )

        if failures:
            raise CommandError("Capital allocation validation failed:\n" + "\n".join(failures))
        self.stdout.write(self.style.SUCCESS(f"Capital allocation validation passed for {checked} companies."))

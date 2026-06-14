from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.ingestion.api import compare_turn_rows, scorecard_candidate_rows


class Command(BaseCommand):
    help = "Validate scorecard and cross-company comparison coverage for the configured universe."

    def handle(self, *args, **options):
        expected = {slugify(seed.name) for seed in CROSS_SECTOR_COMPANIES}
        scorecards = scorecard_candidate_rows(500)
        covered = {row["company_slug"] for row in scorecards}
        missing = sorted(expected - covered)
        comparisons = compare_turn_rows(500)
        invalid = [row["turn_type"] for row in comparisons if row["company_count"] < 2]

        if missing:
            raise CommandError(f"Scorecard coverage missing for: {', '.join(missing)}")
        if not comparisons:
            raise CommandError("No eligible cross-company strategic-turn comparisons are available.")
        if invalid:
            raise CommandError(f"Comparison groups are not cross-company: {', '.join(invalid)}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Dashboard coverage passed: {len(covered)} companies, "
                f"{len(scorecards)} scorecards, {len(comparisons)} comparison groups."
            )
        )

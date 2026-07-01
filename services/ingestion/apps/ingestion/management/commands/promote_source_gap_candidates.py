from django.core.management.base import BaseCommand

from apps.ingestion.services.source_gap_candidate_promoter import promote_source_gap_candidates


class Command(BaseCommand):
    help = "Promote deterministic source-gap resolution candidates into reviewed dashboard rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dashboard", default="")
        parser.add_argument("--gap-type", default="")

    def handle(self, *args, **options):
        result = promote_source_gap_candidates(
            limit=options["limit"],
            dashboard=options["dashboard"],
            gap_type=options["gap_type"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Source gap candidate promotion complete: "
                f"candidates_checked={result.candidates_checked} "
                f"dashboard_rows_created={result.dashboard_rows_created} "
                f"dashboard_rows_updated={result.dashboard_rows_updated} "
                f"candidates_promoted={result.candidates_promoted} "
                f"candidates_skipped={result.candidates_skipped}"
            )
        )

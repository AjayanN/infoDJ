from django.core.management.base import BaseCommand

from apps.ingestion.services.source_gap_candidate_extractor import extract_source_gap_candidates


class Command(BaseCommand):
    help = "Extract full text for source-gap resolution candidates and update evidence excerpts."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dashboard", default="")
        parser.add_argument("--gap-type", default="")
        parser.add_argument(
            "--timeout",
            type=float,
            default=10.0,
            help="Maximum seconds for each document request.",
        )
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Retry documents with a previously recorded extraction failure.",
        )
        parser.add_argument(
            "--refresh-extracted",
            action="store_true",
            help="Rebuild evidence excerpts for candidates whose full text already exists.",
        )

    def handle(self, *args, **options):
        result = extract_source_gap_candidates(
            limit=options["limit"],
            dashboard=options["dashboard"],
            gap_type=options["gap_type"],
            timeout=options["timeout"],
            retry_failed=options["retry_failed"],
            refresh_extracted=options["refresh_extracted"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Source gap candidate extraction complete: "
                f"candidates_checked={result.candidates_checked} "
                f"documents_extracted={result.documents_extracted} "
                f"candidates_updated={result.candidates_updated} "
                f"candidates_failed={result.candidates_failed}"
            )
        )

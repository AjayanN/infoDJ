from django.core.management.base import BaseCommand

from apps.ingestion.services.evidence_ledger import rebuild_evidence_ledger


class Command(BaseCommand):
    help = "Build the idempotent retrieval-ready evidence ledger from current curated facts."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="", help="Optional company slug.")

    def handle(self, *args, **options):
        totals = rebuild_evidence_ledger(company_slug=options["company"].strip())
        self.stdout.write(self.style.SUCCESS(f"Evidence ledger rebuilt: {totals}"))

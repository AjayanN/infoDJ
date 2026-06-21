from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from apps.ingestion.services.leadership_decision_record import build_leadership_decision_record


class Command(BaseCommand):
    help = "Build reviewed Leadership Decision Record baselines."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug to rebuild.")
        parser.add_argument("--all", action="store_true", help="Rebuild all active companies.")

    def handle(self, *args, **options):
        if not options["all"] and not options["company"]:
            raise CommandError("Pass --all or --company <slug>.")
        companies = Company.objects.filter(is_active=True).order_by("name")
        if options["company"]:
            companies = companies.filter(slug=options["company"])
        totals = {"companies": 0, "snapshots_created": 0, "snapshots_updated": 0, "roles_created": 0, "roles_updated": 0, "decisions_created": 0, "decisions_updated": 0}
        for company in companies:
            result = build_leadership_decision_record(company)
            totals["companies"] += 1
            for key, value in result.items():
                totals[key] += value
            self.stdout.write(f"{company.slug}: {result}")
        self.stdout.write(self.style.SUCCESS(f"Leadership Decision Record build complete: {totals}"))

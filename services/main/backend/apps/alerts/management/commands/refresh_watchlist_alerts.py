from django.core.management.base import BaseCommand

from apps.alerts.services import refresh_alerts_for_all_users


class Command(BaseCommand):
    help = "Refresh watchlist alerts for all users from source-backed ingestion data."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=12)

    def handle(self, *args, **options):
        stats = refresh_alerts_for_all_users(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Watchlist alert refresh complete: {stats}"))

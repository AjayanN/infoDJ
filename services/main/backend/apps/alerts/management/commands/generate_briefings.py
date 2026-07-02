from django.core.management.base import BaseCommand

from apps.alerts.briefings import generate_briefings_for_all_users
from apps.alerts.models import BriefingCadence


class Command(BaseCommand):
    help = "Generate daily or weekly briefings for users with active watchlists."

    def add_arguments(self, parser):
        parser.add_argument("--cadence", choices=BriefingCadence.values, default=BriefingCadence.DAILY)
        parser.add_argument("--skip-alert-refresh", action="store_true")

    def handle(self, *args, **options):
        stats = generate_briefings_for_all_users(
            cadence=options["cadence"],
            refresh_alerts=not options["skip_alert_refresh"],
        )
        self.stdout.write(self.style.SUCCESS(f"Briefing generation complete: {stats}"))

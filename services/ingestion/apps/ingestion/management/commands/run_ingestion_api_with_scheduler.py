from __future__ import annotations

import signal
import subprocess
import sys
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the ingestion API and the daily scheduler in one container."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", default="8001")
        parser.add_argument("--scheduler-at", default="02:00")
        parser.add_argument("--scheduler-timezone", default="UTC")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--include-gdelt", action="store_true")

    def handle(self, *args, **options):
        scheduler_command = [
            sys.executable,
            "manage.py",
            "scheduled_daily_update",
            "--at",
            options["scheduler_at"],
            "--timezone",
            options["scheduler_timezone"],
            "--limit",
            str(options["limit"]),
        ]
        if options["include_gdelt"]:
            scheduler_command.append("--include-gdelt")

        api_command = [
            sys.executable,
            "manage.py",
            "runserver",
            f"{options['host']}:{options['port']}",
        ]

        scheduler = subprocess.Popen(scheduler_command)
        api = subprocess.Popen(api_command)
        processes = [scheduler, api]

        self.stdout.write(
            self.style.SUCCESS(
                "Started ingestion API and scheduler in one container "
                f"(scheduler daily at {options['scheduler_at']} {options['scheduler_timezone']})."
            )
        )

        def stop_children(_signum, _frame):
            for process in processes:
                if process.poll() is None:
                    process.terminate()

        signal.signal(signal.SIGINT, stop_children)
        signal.signal(signal.SIGTERM, stop_children)

        exit_code = 0
        try:
            while True:
                for process in processes:
                    code = process.poll()
                    if code is not None:
                        exit_code = code
                        stop_children(signal.SIGTERM, None)
                        raise SystemExit(exit_code)
                time.sleep(1)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()

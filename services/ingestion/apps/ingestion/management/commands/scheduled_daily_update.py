from __future__ import annotations

import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


@dataclass(frozen=True)
class ScheduleSlot:
    name: str
    run_time: tuple[int, int]
    offset: int
    batch_size: int
    retry_failed_only: bool = False


class Command(BaseCommand):
    help = "Run daily_company_update on a fixed daily schedule."

    def add_arguments(self, parser):
        parser.add_argument("--at", default="02:00", help="Daily run time in HH:MM format.")
        parser.add_argument("--timezone", default="UTC", help="IANA timezone for --at.")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--batch-size", type=int, default=0)
        parser.add_argument("--sec-limit", type=int, default=30)
        parser.add_argument("--wikipedia-limit", type=int, default=10)
        parser.add_argument("--gdelt-records-per-query", type=int, default=5)
        parser.add_argument("--gdelt-query-limit", type=int, default=3)
        parser.add_argument("--event-filing-limit", type=int, default=8)
        parser.add_argument("--include-gdelt", action="store_true")
        parser.add_argument("--include-market-data", action="store_true")
        parser.add_argument("--include-financial-facts", action="store_true")
        parser.add_argument("--include-insider-transactions", action="store_true")
        parser.add_argument("--include-official-product-prices", action="store_true")
        parser.add_argument("--insider-form-limit", type=int, default=5)
        parser.add_argument("--include-macro-context", action="store_true")
        parser.add_argument("--include-quality-scoring", action="store_true")
        parser.add_argument("--include-company-profiles", action="store_true")
        parser.add_argument("--skip-event-extraction", action="store_true")
        parser.add_argument("--retry-failed-only", action="store_true")
        parser.add_argument(
            "--split-batches",
            action="store_true",
            help="Use the standard 02:00/04:00/06:00 UTC split-batch schedule.",
        )
        parser.add_argument("--run-on-start", action="store_true")
        parser.add_argument("--once", action="store_true", help="Run one scheduler cycle and exit.")
        parser.add_argument("--dry-run", action="store_true", help="Print the planned update without executing it.")

    def handle(self, *args, **options):
        timezone = self._parse_timezone(options["timezone"])
        slots = self._build_slots(options)
        shutdown = {"requested": False}

        def request_shutdown(_signum, _frame):
            shutdown["requested"] = True
            self.stdout.write("Shutdown requested; scheduler will stop after the current wait/run.")

        signal.signal(signal.SIGINT, request_shutdown)
        signal.signal(signal.SIGTERM, request_shutdown)

        self.stdout.write(
            self.style.SUCCESS(
                f"Daily ingestion scheduler started: timezone={options['timezone']} slots={self._format_slots(slots)}"
            )
        )

        if options["run_on_start"] or options["once"]:
            self._run_daily_update(options, slots[0])
            if options["once"]:
                return

        while not shutdown["requested"]:
            next_run, slot = self._next_slot(slots, timezone)
            seconds = max(0, (next_run - datetime.now(timezone)).total_seconds())
            self.stdout.write(
                f"Next daily ingestion update scheduled for {next_run.isoformat()} slot={slot.name}"
            )
            self._sleep_until(seconds, shutdown)
            if shutdown["requested"]:
                break
            self._run_daily_update(options, slot)

        self.stdout.write("Daily ingestion scheduler stopped.")

    def _run_daily_update(self, options, slot: ScheduleSlot):
        command_options = {
            "limit": options["limit"],
            "offset": slot.offset,
            "batch_size": slot.batch_size,
            "sec_limit": options["sec_limit"],
            "wikipedia_limit": options["wikipedia_limit"],
            "gdelt_records_per_query": options["gdelt_records_per_query"],
            "gdelt_query_limit": options["gdelt_query_limit"],
            "skip_gdelt": not options["include_gdelt"],
            "include_market_data": options["include_market_data"],
            "include_financial_facts": options["include_financial_facts"],
            "include_insider_transactions": options["include_insider_transactions"],
            "include_official_product_prices": options["include_official_product_prices"],
            "insider_form_limit": options["insider_form_limit"],
            "include_macro_context": options["include_macro_context"],
            "include_quality_scoring": options["include_quality_scoring"],
            "include_company_profiles": options["include_company_profiles"],
            "skip_event_extraction": options["skip_event_extraction"],
            "event_filing_limit": options["event_filing_limit"],
            "retry_failed_only": slot.retry_failed_only,
        }
        if options["dry_run"]:
            self.stdout.write(f"Dry run: slot={slot.name} daily_company_update options={command_options}")
            return

        self.stdout.write(f"Starting scheduled daily_company_update slot={slot.name}.")
        call_command("daily_company_update", **command_options)
        self.stdout.write(self.style.SUCCESS(f"Scheduled daily_company_update finished slot={slot.name}."))

    def _build_slots(self, options) -> list[ScheduleSlot]:
        if options["split_batches"]:
            batch_size = options["batch_size"] or 10
            return [
                ScheduleSlot("companies-1-10", self._parse_run_time("02:00"), 0, batch_size),
                ScheduleSlot("companies-11-20", self._parse_run_time("04:00"), batch_size, batch_size),
                ScheduleSlot("retry-failed", self._parse_run_time("06:00"), 0, 0, retry_failed_only=True),
            ]
        return [
            ScheduleSlot(
                "daily",
                self._parse_run_time(options["at"]),
                options["offset"],
                options["batch_size"],
                retry_failed_only=options["retry_failed_only"],
            )
        ]

    def _parse_run_time(self, value: str) -> tuple[int, int]:
        try:
            hour_text, minute_text = value.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError as exc:
            raise CommandError("--at must use HH:MM format, for example 02:00") from exc
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise CommandError("--at must be a valid 24-hour time, for example 02:00")
        return hour, minute

    def _parse_timezone(self, value: str) -> ZoneInfo:
        try:
            return ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise CommandError(f"Unknown timezone: {value}") from exc

    def _next_slot(self, slots: list[ScheduleSlot], timezone: ZoneInfo) -> tuple[datetime, ScheduleSlot]:
        candidates = [(self._next_run_at(slot.run_time, timezone), slot) for slot in slots]
        return min(candidates, key=lambda candidate: candidate[0])

    def _next_run_at(self, run_time: tuple[int, int], timezone: ZoneInfo) -> datetime:
        now = datetime.now(timezone)
        next_run = now.replace(hour=run_time[0], minute=run_time[1], second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run

    def _format_slots(self, slots: list[ScheduleSlot]) -> str:
        parts = []
        for slot in slots:
            suffix = " retry_failed_only" if slot.retry_failed_only else f" offset={slot.offset} batch_size={slot.batch_size}"
            parts.append(f"{slot.name}@{slot.run_time[0]:02d}:{slot.run_time[1]:02d}{suffix}")
        return ", ".join(parts)

    def _sleep_until(self, seconds: float, shutdown: dict[str, bool]):
        remaining = seconds
        while remaining > 0 and not shutdown["requested"]:
            sleep_for = min(remaining, 60)
            time.sleep(sleep_for)
            remaining -= sleep_for

from __future__ import annotations

import os
import re
from datetime import date, timedelta

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobType
from apps.ingestion.services.market_price_client import (
    ALPHA_VANTAGE_PROVIDER,
    FMP_PROVIDER,
    STOOQ_PROVIDER,
    AlphaVantageMarketPriceClient,
    FMPMarketPriceClient,
    MarketPriceClientChain,
    StooqMarketPriceClient,
    store_market_prices,
)


TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,12}$")


class Command(BaseCommand):
    help = "Ingest daily OHLCV market prices from FMP, Alpha Vantage, or Stooq."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="", help="Company slug. Omit to ingest all active companies.")
        parser.add_argument("--ticker", default="", help="Ticker override for a single company run.")
        parser.add_argument("--days", type=int, default=30, help="Trailing calendar days to ingest.")
        parser.add_argument("--start", default="", help="Start date in YYYY-MM-DD format.")
        parser.add_argument("--end", default="", help="End date in YYYY-MM-DD format.")
        parser.add_argument(
            "--provider",
            choices=("auto", "fmp", "alpha_vantage", "stooq"),
            default="auto",
            help="Market data provider. auto tries configured FMP, then configured Alpha Vantage, then Stooq.",
        )
        parser.add_argument("--fmp-api-key", default="", help="FMP API key. Defaults to FMP_API_KEY.")
        parser.add_argument("--alpha-vantage-api-key", default="", help="Alpha Vantage API key. Defaults to ALPHA_VANTAGE_API_KEY.")
        parser.add_argument("--include-benchmarks", action="store_true", help="Also ingest global benchmark symbols.")
        parser.add_argument("--benchmark-symbols", default="SPY,QQQ,DIA,IWM,XLC,XLY,XLP,XLE,XLF,XLV,XLI,XLK,XLB,XLRE,XLU")
        parser.add_argument("--max-api-calls", type=int, default=240, help="Maximum provider calls for this run.")

    def handle(self, *args, **options):
        if options["ticker"] and not options["company"]:
            raise CommandError("--ticker can only be used with --company.")

        start_date, end_date = self._date_range(options)
        market_price_model = apps.get_model("ingestion", "MarketPrice")
        client = build_market_client(options)

        companies = self._companies(options["company"])
        calls_remaining = options["max_api_calls"]
        totals = {"companies": 0, "benchmarks": 0, "api_calls": 0, "prices_found": 0, "prices_inserted": 0, "prices_updated": 0, "skipped": 0}
        for company in companies:
            if calls_remaining <= 0:
                totals["skipped"] += 1
                self.stderr.write("Skipping remaining companies: --max-api-calls reached.")
                break
            ticker = options["ticker"].strip().upper() if options["ticker"] else ticker_for_company(company)
            if not ticker:
                totals["skipped"] += 1
                self.stderr.write(f"Skipping {company.name}: no ticker found.")
                continue

            totals["companies"] += 1
            try:
                counters = self._ingest_company(
                    company=company,
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    client=client,
                    market_price_model=market_price_model,
                )
            except Exception as exc:
                totals["skipped"] += 1
                self.stderr.write(f"Skipping {company.slug}: {sanitize_error(exc)}")
                totals["api_calls"] += 1
                calls_remaining -= 1
                continue
            for key in ("prices_found", "prices_inserted", "prices_updated"):
                totals[key] += counters[key]
            totals["api_calls"] += 1
            calls_remaining -= 1

        if options["include_benchmarks"]:
            for symbol in benchmark_symbols(options["benchmark_symbols"]):
                if calls_remaining <= 0:
                    totals["skipped"] += 1
                    self.stderr.write("Skipping remaining benchmarks: --max-api-calls reached.")
                    break
                try:
                    counters = self._ingest_company(
                        company=None,
                        ticker=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        client=client,
                        market_price_model=market_price_model,
                    )
                except Exception as exc:
                    totals["skipped"] += 1
                    self.stderr.write(f"Skipping benchmark {symbol}: {sanitize_error(exc)}")
                    continue
                totals["benchmarks"] += 1
                for key in ("prices_found", "prices_inserted", "prices_updated"):
                    totals[key] += counters[key]
                totals["api_calls"] += 1
                calls_remaining -= 1

        self.stdout.write(self.style.SUCCESS(f"Market price ingestion complete: {totals}"))

    def _companies(self, company_slug: str):
        if company_slug:
            try:
                return [Company.objects.get(slug=company_slug)]
            except Company.DoesNotExist as exc:
                raise CommandError(f"Company not found: {company_slug}") from exc
        return Company.objects.filter(is_active=True).order_by("name")

    def _date_range(self, options):
        end_date = parse_date_option(options["end"]) if options["end"] else timezone.localdate()
        if options["start"]:
            start_date = parse_date_option(options["start"])
        else:
            days = options["days"]
            if days < 1:
                raise CommandError("--days must be at least 1.")
            start_date = end_date - timedelta(days=days - 1)
        if start_date > end_date:
            raise CommandError("--start must be on or before --end.")
        return start_date, end_date

    def _ingest_company(self, *, company, ticker, start_date, end_date, client, market_price_model):
        job = IngestionJob.objects.create(
            company=company,
            job_type=IngestionJobType.MARKET_DATA,
            source=client.provider,
            query=f"{ticker} {start_date.isoformat()}..{end_date.isoformat()}",
            status="RUNNING",
            started_at=timezone.now(),
        )
        try:
            bars = client.daily_prices(ticker, start_date=start_date, end_date=end_date)
            counters = store_market_prices(
                company=company,
                bars=bars,
                market_price_model=market_price_model,
            )
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = sanitize_error(exc)
            job.finished_at = timezone.now()
            job.save()
            raise

        job.sources_found = counters["prices_found"]
        job.sources_inserted = counters["prices_inserted"]
        job.duplicates_skipped = counters["prices_updated"]
        job.status = "SUCCEEDED"
        job.finished_at = timezone.now()
        job.save()
        self.stdout.write(
            f"{company.slug if company else 'benchmark'} ({ticker}): found={counters['prices_found']} "
            f"inserted={counters['prices_inserted']} updated={counters['prices_updated']}"
        )
        return counters


def parse_date_option(value: str):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CommandError(f"Invalid date {value!r}; expected YYYY-MM-DD.") from exc


def ticker_for_company(company) -> str:
    aliases = company.aliases if isinstance(company.aliases, list) else []
    candidates = []
    for alias in aliases:
        raw = str(alias).strip()
        ticker = raw.upper()
        if raw == ticker and TICKER_RE.match(ticker):
            candidates.append(ticker)
    if candidates:
        # Short exchange symbols beat corporate abbreviations such as JPMC.
        return min(candidates, key=lambda value: (len(value), value))
    return ""


def build_market_client(options):
    provider = options["provider"]
    fmp_key = options["fmp_api_key"] or os.getenv("FMP_API_KEY", "")
    alpha_key = options["alpha_vantage_api_key"] or os.getenv("ALPHA_VANTAGE_API_KEY", "")
    if provider == "fmp":
        return FMPMarketPriceClient(api_key=fmp_key)
    if provider == "alpha_vantage":
        return AlphaVantageMarketPriceClient(api_key=alpha_key)
    if provider == "stooq":
        client = StooqMarketPriceClient()
        client.provider = STOOQ_PROVIDER
        return client

    clients = []
    if fmp_key:
        clients.append(FMPMarketPriceClient(api_key=fmp_key))
    if alpha_key:
        clients.append(AlphaVantageMarketPriceClient(api_key=alpha_key))
    clients.append(StooqMarketPriceClient())
    return MarketPriceClientChain(clients)


def benchmark_symbols(raw: str) -> list[str]:
    return [symbol.strip().upper() for symbol in raw.split(",") if symbol.strip()]


def sanitize_error(exc: Exception) -> str:
    return re.sub(r"apikey=[^&\s]+", "apikey=<redacted>", str(exc))

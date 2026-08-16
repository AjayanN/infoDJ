"""Market price ingestion clients."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any, Iterable, Mapping

import requests


STOOQ_DAILY_CSV_URL = "https://stooq.com/q/d/l/"
FMP_HISTORICAL_PRICE_URL = "https://financialmodelingprep.com/stable/historical-price-eod/full"
ALPHA_VANTAGE_QUERY_URL = "https://www.alphavantage.co/query"
STOOQ_PROVIDER = "STOOQ"
FMP_PROVIDER = "FMP"
ALPHA_VANTAGE_PROVIDER = "ALPHA_VANTAGE"


@dataclass(frozen=True)
class MarketPriceBar:
    ticker: str
    provider: str
    price_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    raw: Mapping[str, Any] = field(default_factory=dict)


class StooqMarketPriceClient:
    """Small Stooq daily CSV client. Stooq requires no API key."""

    provider = STOOQ_PROVIDER

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        base_url: str = STOOQ_DAILY_CSV_URL,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.base_url = base_url

    def daily_prices(
        self,
        ticker: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[MarketPriceBar]:
        stooq_symbol = normalize_us_ticker_for_stooq(ticker)
        response = self.session.get(
            self.base_url,
            params={
                "s": stooq_symbol,
                "i": "d",
                "d1": format_stooq_date(start_date),
                "d2": format_stooq_date(end_date),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_stooq_daily_csv(response.text, ticker=stooq_symbol)


class FMPMarketPriceClient:
    """Financial Modeling Prep historical end-of-day price client."""

    provider = FMP_PROVIDER

    def __init__(
        self,
        *,
        api_key: str,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        base_url: str = FMP_HISTORICAL_PRICE_URL,
    ) -> None:
        if not api_key:
            raise ValueError("FMP_API_KEY is required for FMP market price ingestion.")
        self.api_key = api_key
        self.session = session or requests.Session()
        self.timeout = timeout
        self.base_url = base_url

    def daily_prices(
        self,
        ticker: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[MarketPriceBar]:
        response = self.session.get(
            self.base_url,
            params={
                "symbol": normalize_market_ticker(ticker),
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
                "apikey": self.api_key,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_fmp_historical_prices(response.json(), ticker=normalize_market_ticker(ticker))


class AlphaVantageMarketPriceClient:
    """Alpha Vantage daily adjusted CSV client."""

    provider = ALPHA_VANTAGE_PROVIDER

    def __init__(
        self,
        *,
        api_key: str,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        base_url: str = ALPHA_VANTAGE_QUERY_URL,
    ) -> None:
        if not api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required for Alpha Vantage market price ingestion.")
        self.api_key = api_key
        self.session = session or requests.Session()
        self.timeout = timeout
        self.base_url = base_url

    def daily_prices(
        self,
        ticker: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[MarketPriceBar]:
        symbol = normalize_market_ticker(ticker)
        response = self.session.get(
            self.base_url,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "datatype": "csv",
                "apikey": self.api_key,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return [
            bar
            for bar in parse_alpha_vantage_daily_csv(response.text, ticker=symbol)
            if start_date <= bar.price_date <= end_date
        ]


class MarketPriceClientChain:
    """Try configured market data providers in order until one returns rows."""

    def __init__(self, clients: Iterable[Any]) -> None:
        self.clients = list(clients)
        if not self.clients:
            raise ValueError("At least one market price provider must be configured.")

    @property
    def provider(self) -> str:
        return "+".join(getattr(client, "provider", client.__class__.__name__) for client in self.clients)

    def daily_prices(self, ticker: str, *, start_date: date, end_date: date) -> list[MarketPriceBar]:
        errors = []
        for client in self.clients:
            provider = getattr(client, "provider", client.__class__.__name__)
            try:
                bars = client.daily_prices(ticker, start_date=start_date, end_date=end_date)
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                continue
            if bars:
                return bars
            errors.append(f"{provider}: no rows")
        raise RuntimeError("No market price provider returned rows. " + "; ".join(errors))


def normalize_market_ticker(ticker: str) -> str:
    value = ticker.strip().upper()
    if not value:
        raise ValueError("Ticker is required for market price ingestion.")
    return value


def normalize_us_ticker_for_stooq(ticker: str) -> str:
    """Normalize US exchange tickers for Stooq, e.g. AAPL -> aapl.us."""

    value = ticker.strip().lower().replace("-", ".")
    if not value:
        raise ValueError("Ticker is required for Stooq market price ingestion.")
    if "." not in value:
        return f"{value}.us"
    return value


def parse_fmp_historical_prices(payload: Any, *, ticker: str) -> list[MarketPriceBar]:
    if isinstance(payload, dict):
        if payload.get("Error Message") or payload.get("error"):
            raise RuntimeError(str(payload.get("Error Message") or payload.get("error")))
        rows = payload.get("historical") or payload.get("data") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    bars = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        try:
            bars.append(
                MarketPriceBar(
                    ticker=ticker,
                    provider=FMP_PROVIDER,
                    price_date=date.fromisoformat(str(row["date"])),
                    open_price=_decimal(row.get("open")),
                    high_price=_decimal(row.get("high")),
                    low_price=_decimal(row.get("low")),
                    close_price=_decimal(row.get("close")),
                    volume=int(Decimal(str(row.get("volume") or "0"))),
                    raw={"provider": FMP_PROVIDER, "ticker": ticker, "row": dict(row)},
                )
            )
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
    return sorted(bars, key=lambda bar: bar.price_date)


def parse_alpha_vantage_daily_csv(csv_text: str, *, ticker: str) -> list[MarketPriceBar]:
    stripped = csv_text.strip()
    if not stripped:
        return []
    if stripped.startswith("{") or "Thank you for using Alpha Vantage" in stripped:
        raise RuntimeError(stripped[:300])
    rows = csv.DictReader(StringIO(stripped))
    bars: list[MarketPriceBar] = []
    for row in rows:
        if not row:
            continue
        try:
            bars.append(
                MarketPriceBar(
                    ticker=ticker,
                    provider=ALPHA_VANTAGE_PROVIDER,
                    price_date=date.fromisoformat(str(row["timestamp"])),
                    open_price=_decimal(row.get("open")),
                    high_price=_decimal(row.get("high")),
                    low_price=_decimal(row.get("low")),
                    close_price=_decimal(row.get("adjusted_close") or row.get("close")),
                    volume=int(Decimal(str(row.get("volume") or "0"))),
                    raw={"provider": ALPHA_VANTAGE_PROVIDER, "ticker": ticker, "row": dict(row)},
                )
            )
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
    return sorted(bars, key=lambda bar: bar.price_date)


def format_stooq_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def parse_stooq_daily_csv(csv_text: str, *, ticker: str) -> list[MarketPriceBar]:
    rows = csv.DictReader(StringIO(csv_text.strip()))
    bars: list[MarketPriceBar] = []
    for row in rows:
        if not row or row.get("Date") in {"No data", None, ""}:
            continue
        try:
            bar = MarketPriceBar(
                ticker=ticker,
                provider=STOOQ_PROVIDER,
                price_date=date.fromisoformat(str(row["Date"])),
                open_price=_decimal(row.get("Open")),
                high_price=_decimal(row.get("High")),
                low_price=_decimal(row.get("Low")),
                close_price=_decimal(row.get("Close")),
                volume=int(Decimal(str(row.get("Volume") or "0"))),
                raw={"provider": STOOQ_PROVIDER, "ticker": ticker, "row": dict(row)},
            )
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
        bars.append(bar)
    return bars


def store_market_prices(
    *,
    company: Any,
    bars: Iterable[MarketPriceBar],
    market_price_model: Any,
) -> dict[str, int]:
    counters = {"prices_found": 0, "prices_inserted": 0, "prices_updated": 0}
    for bar in bars:
        counters["prices_found"] += 1
        _, created = market_price_model.objects.update_or_create(
            company=company,
            ticker=bar.ticker,
            provider=bar.provider,
            price_date=bar.price_date,
            defaults={
                "open_price": bar.open_price,
                "high_price": bar.high_price,
                "low_price": bar.low_price,
                "close_price": bar.close_price,
                "volume": bar.volume,
                "raw": bar.raw,
            },
        )
        if created:
            counters["prices_inserted"] += 1
        else:
            counters["prices_updated"] += 1
    return counters


def _decimal(value: Any) -> Decimal:
    if value in {None, ""}:
        raise ValueError("Missing decimal value")
    return Decimal(str(value))

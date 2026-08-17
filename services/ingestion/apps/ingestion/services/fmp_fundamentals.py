"""Financial Modeling Prep fundamentals ingestion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

import requests


FMP_BASE_URL = "https://financialmodelingprep.com/stable"
FMP_TAXONOMY = "FMP"

FUNDAMENTAL_SERIES = {
    "income-statement": {
        "revenue": ("Revenue", "USD"),
        "grossProfit": ("Gross profit", "USD"),
        "operatingIncome": ("Operating income", "USD"),
        "ebitda": ("EBITDA", "USD"),
        "netIncome": ("Net income", "USD"),
        "eps": ("Earnings per share", "USD_PER_SHARE"),
    },
    "balance-sheet-statement": {
        "cashAndCashEquivalents": ("Cash and cash equivalents", "USD"),
        "totalAssets": ("Total assets", "USD"),
        "totalDebt": ("Total debt", "USD"),
        "totalStockholdersEquity": ("Shareholders' equity", "USD"),
    },
    "cash-flow-statement": {
        "operatingCashFlow": ("Operating cash flow", "USD"),
        "capitalExpenditure": ("Capital expenditure", "USD"),
        "freeCashFlow": ("Free cash flow", "USD"),
        "dividendsPaid": ("Dividends paid", "USD"),
    },
    "key-metrics": {
        "enterpriseValue": ("Enterprise value", "USD"),
        "marketCap": ("Market capitalization", "USD"),
        "debtToEquity": ("Debt to equity", "RATIO"),
        "returnOnEquity": ("Return on equity", "RATIO"),
        "returnOnAssets": ("Return on assets", "RATIO"),
    },
    "ratios": {
        "grossProfitMargin": ("Gross profit margin", "RATIO"),
        "operatingProfitMargin": ("Operating profit margin", "RATIO"),
        "netProfitMargin": ("Net profit margin", "RATIO"),
        "currentRatio": ("Current ratio", "RATIO"),
    },
}


@dataclass(frozen=True)
class FmpFundamentalFact:
    endpoint: str
    concept: str
    label: str
    unit: str
    period_end: date
    fiscal_year: int | None
    fiscal_period: str
    value: Decimal
    raw: Mapping[str, Any]


class FmpFundamentalsClient:
    """Fetch small, documented FMP fundamental series for a ticker."""

    def __init__(
        self,
        *,
        api_key: str,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        base_url: str = FMP_BASE_URL,
    ) -> None:
        if not api_key:
            raise ValueError("FMP_API_KEY is required for FMP fundamentals ingestion.")
        self.api_key = api_key
        self.session = session or requests.Session()
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    def fundamentals(self, ticker: str, *, limit: int = 5) -> list[FmpFundamentalFact]:
        facts: list[FmpFundamentalFact] = []
        for endpoint, concepts in FUNDAMENTAL_SERIES.items():
            response = self.session.get(
                f"{self.base_url}/{endpoint}",
                params={"symbol": ticker, "limit": limit, "apikey": self.api_key},
                timeout=self.timeout,
            )
            response.raise_for_status()
            facts.extend(parse_fmp_fundamental_facts(response.json(), endpoint=endpoint, concepts=concepts))
        return facts


def parse_fmp_fundamental_facts(
    payload: Any,
    *,
    endpoint: str,
    concepts: Mapping[str, tuple[str, str]],
) -> list[FmpFundamentalFact]:
    """Return only the curated, numeric FMP fields with a stated period."""

    if not isinstance(payload, list):
        return []
    facts: list[FmpFundamentalFact] = []
    for row in payload:
        if not isinstance(row, Mapping):
            continue
        period_end = _parse_date(row.get("date"))
        if period_end is None:
            continue
        fiscal_year = _parse_year(row.get("calendarYear"))
        fiscal_period = str(row.get("period") or "").upper()
        for field_name, (label, unit) in concepts.items():
            value = _parse_decimal(row.get(field_name))
            if value is None:
                continue
            facts.append(
                FmpFundamentalFact(
                    endpoint=endpoint,
                    concept=f"{endpoint}:{field_name}",
                    label=label,
                    unit=unit,
                    period_end=period_end,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    value=value,
                    raw={"provider": "FMP", "endpoint": endpoint, "row": dict(row)},
                )
            )
    return facts


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _parse_year(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

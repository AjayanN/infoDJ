"""Starter company universe for cross-sector ingestion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanySeed:
    name: str
    ticker: str
    sector: str
    country: str = "United States"


CROSS_SECTOR_COMPANIES: tuple[CompanySeed, ...] = (
    CompanySeed("Apple", "AAPL", "Information Technology"),
    CompanySeed("Microsoft", "MSFT", "Information Technology"),
    CompanySeed("JPMorgan Chase", "JPM", "Financials"),
    CompanySeed("Visa", "V", "Financials"),
    CompanySeed("UnitedHealth Group", "UNH", "Health Care"),
    CompanySeed("Pfizer", "PFE", "Health Care"),
    CompanySeed("Amazon", "AMZN", "Consumer Discretionary"),
    CompanySeed("Walmart", "WMT", "Consumer Staples"),
    CompanySeed("ExxonMobil", "XOM", "Energy"),
    CompanySeed("NextEra Energy", "NEE", "Utilities"),
    CompanySeed("Ford Motor Company", "F", "Consumer Discretionary"),
    CompanySeed("Tesla", "TSLA", "Consumer Discretionary"),
    CompanySeed("Caterpillar", "CAT", "Industrials"),
    CompanySeed("General Electric", "GE", "Industrials"),
    CompanySeed("Disney", "DIS", "Communication Services"),
    CompanySeed("Netflix", "NFLX", "Communication Services"),
    CompanySeed("Prologis", "PLD", "Real Estate"),
    CompanySeed("American Tower", "AMT", "Real Estate"),
    CompanySeed("Freeport-McMoRan", "FCX", "Materials"),
    CompanySeed("Newmont", "NEM", "Materials"),
)


def seeds_by_ticker() -> dict[str, CompanySeed]:
    return {seed.ticker: seed for seed in CROSS_SECTOR_COMPANIES}


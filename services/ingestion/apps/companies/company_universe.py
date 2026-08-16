"""Starter company universe for cross-sector ingestion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanySeed:
    name: str
    ticker: str
    sector: str
    country: str = "United States"
    website: str = ""
    sec_cik: str = ""


CROSS_SECTOR_COMPANIES: tuple[CompanySeed, ...] = (
    CompanySeed("Apple", "AAPL", "Information Technology", website="https://www.apple.com/"),
    CompanySeed("Microsoft", "MSFT", "Information Technology", website="https://www.microsoft.com/"),
    CompanySeed("JPMorgan Chase", "JPM", "Financials", website="https://www.jpmorganchase.com/"),
    CompanySeed("Visa", "V", "Financials", website="https://corporate.visa.com/"),
    CompanySeed("UnitedHealth Group", "UNH", "Health Care", website="https://www.unitedhealthgroup.com/"),
    CompanySeed("Pfizer", "PFE", "Health Care", website="https://www.pfizer.com/"),
    CompanySeed("Amazon", "AMZN", "Consumer Discretionary", website="https://www.aboutamazon.com/"),
    CompanySeed("Walmart", "WMT", "Consumer Staples", website="https://corporate.walmart.com/"),
    CompanySeed(
        "ExxonMobil",
        "XOM",
        "Energy",
        website="https://corporate.exxonmobil.com/",
        sec_cik="0000034088",
    ),
    CompanySeed("NextEra Energy", "NEE", "Utilities", website="https://www.nexteraenergy.com/"),
    CompanySeed("Ford Motor Company", "F", "Consumer Discretionary", website="https://corporate.ford.com/"),
    CompanySeed("Tesla", "TSLA", "Consumer Discretionary", website="https://www.tesla.com/"),
    CompanySeed("Caterpillar", "CAT", "Industrials", website="https://www.caterpillar.com/"),
    CompanySeed("General Electric", "GE", "Industrials", website="https://www.ge.com/"),
    CompanySeed("Disney", "DIS", "Communication Services", website="https://thewaltdisneycompany.com/"),
    CompanySeed("Netflix", "NFLX", "Communication Services", website="https://about.netflix.com/"),
    CompanySeed("Prologis", "PLD", "Real Estate", website="https://www.prologis.com/"),
    CompanySeed("American Tower", "AMT", "Real Estate", website="https://www.americantower.com/"),
    CompanySeed("Freeport-McMoRan", "FCX", "Materials", website="https://www.fcx.com/"),
    CompanySeed("Newmont", "NEM", "Materials", website="https://www.newmont.com/"),
)


def seeds_by_ticker() -> dict[str, CompanySeed]:
    return {seed.ticker: seed for seed in CROSS_SECTOR_COMPANIES}

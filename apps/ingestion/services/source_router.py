"""Stage and year based source routing for company-history ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


CURRENT_YEAR = 2026


@dataclass(frozen=True)
class SourceRoute:
    stage: str
    year_start: int
    year_end: int
    primary_sources: tuple[str, ...]
    supporting_sources: tuple[str, ...]
    collector_priority: tuple[str, ...]
    notes: str


def build_company_source_plan(
    company: Any,
    *,
    founded_year: int | None = None,
    public_listing_year: int | None = None,
    ticker: str = "",
    current_year: int = CURRENT_YEAR,
) -> list[SourceRoute]:
    """Build a generic source plan from company stage/year metadata."""

    founded_year = founded_year or _year(getattr(company, "founded_date", None)) or current_year - 10
    has_public_filing_route = bool(getattr(company, "sec_cik", "")) or bool(ticker)
    routes: list[SourceRoute] = []

    if public_listing_year and founded_year < public_listing_year:
        routes.append(private_route(founded_year, public_listing_year - 1))
    elif not has_public_filing_route:
        routes.append(private_route(founded_year, current_year))
        return routes

    if has_public_filing_route:
        listing_year = public_listing_year or founded_year
        recent_start = max(listing_year, current_year - 3)
        if listing_year <= recent_start - 1:
            routes.append(public_route(listing_year, recent_start - 1))
        routes.append(recent_public_route(recent_start, current_year))
    else:
        routes.append(recent_private_route(max(founded_year, current_year - 3), current_year))

    return routes


def private_route(year_start: int, year_end: int) -> SourceRoute:
    return SourceRoute(
        stage="PRIVATE_EARLY_AND_GROWTH",
        year_start=year_start,
        year_end=year_end,
        primary_sources=(
            "WIKIDATA",
            "WIKIPEDIA_REFERENCES",
            "COMPANY_HISTORY_PAGE",
            "ARCHIVED_WEB",
            "FOUNDER_INTERVIEWS",
        ),
        supporting_sources=("TARGETED_NEWS", "COMPANY_BLOG", "FUNDING_NEWS"),
        collector_priority=(
            "wikidata",
            "wikipedia_references",
            "company_history_page",
            "archived_web",
            "targeted_news",
        ),
        notes="Use non-filing sources before public listing or for private companies.",
    )


def public_route(year_start: int, year_end: int) -> SourceRoute:
    return SourceRoute(
        stage="PUBLIC_COMPANY",
        year_start=year_start,
        year_end=year_end,
        primary_sources=("SEC_EDGAR", "INVESTOR_RELATIONS", "ANNUAL_REPORTS"),
        supporting_sources=("COMPANY_NEWSROOM", "TARGETED_NEWS", "WIKIPEDIA_REFERENCES"),
        collector_priority=("sec_edgar_full_history", "investor_relations", "company_newsroom", "targeted_news"),
        notes="Use filings as the backbone from listing year onward.",
    )


def recent_public_route(year_start: int, year_end: int) -> SourceRoute:
    return SourceRoute(
        stage="RECENT_PUBLIC_COMPANY",
        year_start=year_start,
        year_end=year_end,
        primary_sources=("SEC_EDGAR", "INVESTOR_RELATIONS", "COMPANY_NEWSROOM"),
        supporting_sources=("GDELT_SUPPORTING", "TRUSTED_BUSINESS_NEWS"),
        collector_priority=("sec_edgar_recent", "company_newsroom", "gdelt_supporting"),
        notes="Use recent news as supporting evidence; keep official sources primary.",
    )


def recent_private_route(year_start: int, year_end: int) -> SourceRoute:
    return SourceRoute(
        stage="RECENT_PRIVATE_COMPANY",
        year_start=year_start,
        year_end=year_end,
        primary_sources=("COMPANY_NEWSROOM", "COMPANY_BLOG", "WIKIPEDIA_REFERENCES"),
        supporting_sources=("TARGETED_NEWS", "GDELT_SUPPORTING", "FOUNDER_INTERVIEWS"),
        collector_priority=("company_newsroom", "wikipedia_references", "targeted_news", "gdelt_supporting"),
        notes="For private companies, skip public filing sources unless a filing route exists.",
    )


def _year(value: Any) -> int | None:
    if isinstance(value, date):
        return value.year
    return None

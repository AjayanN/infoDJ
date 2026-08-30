from __future__ import annotations

from dataclasses import dataclass

from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import Company
from apps.ingestion.models import IngestionJob, IngestionJobType, SourceDocument, SourceGap, SourceGapStatus
from apps.ingestion.services.sec_edgar_client import discover_sec_filings_for_company


SOURCE_GAP_FORM_RULES: dict[tuple[str, str], tuple[str, ...]] = {
    # Lifecycle evidence needs the action itself, not merely current disclosure.
    # Include transaction forms to reach historical effective dates and definitive terms.
    ("FOUNDER_DECISION", "LIFECYCLE_TIMING"): ("8-K", "10-K", "10-Q", "S-4", "DEFM14A"),
    ("earnings", "management_explanation"): ("10-Q", "10-K", "8-K"),
    ("earnings", "guidance_comparison"): ("8-K", "10-Q", "10-K"),
    ("capital_allocation", "capital_deployment_categories"): ("10-K", "10-Q", "8-K"),
    ("capital_allocation", "cash_flow_context"): ("10-K", "10-Q"),
    ("capital_allocation", "free_cash_flow"): ("10-K", "10-Q"),
    ("acquisition_lifecycle", "acquisition_deals"): ("8-K", "10-K", "10-Q", "S-4", "DEFM14A"),
    ("acquisition_lifecycle", "acquisition_deal_terms"): ("8-K", "10-K", "10-Q", "S-4", "DEFM14A"),
    ("acquisition_lifecycle", "acquisition_promised_synergies"): ("8-K", "10-K", "10-Q"),
    ("competitive_position", "competitive_market_share"): ("10-K", "10-Q", "8-K"),
    ("customer_supplier_dependency", "named_counterparties"): ("10-K", "10-Q", "8-K"),
    ("customer_supplier_dependency", "concentration_percentages"): ("10-K", "10-Q"),
    ("customer_supplier_dependency", "dependency_contract_terms"): ("8-K", "10-K", "10-Q"),
    ("product_pricing_history", "product_list_prices"): ("8-K", "10-K", "10-Q"),
    ("geographic_expansion", "market_entry_dates"): ("8-K", "10-K", "10-Q"),
    ("geographic_expansion", "local_partnerships"): ("8-K", "10-K", "10-Q"),
    ("geographic_expansion", "regulatory_barriers"): ("10-K", "10-Q", "8-K"),
    ("geographic_expansion", "revenue_contribution"): ("10-K", "10-Q"),
    ("geographic_expansion", "expansion_outcomes"): ("10-Q", "10-K", "8-K"),
    ("leadership_decision_record", "tenure_dates"): ("8-K", "10-K", "10-Q", "DEF 14A"),
    ("leadership_decision_record", "transition_events"): ("8-K", "10-K", "10-Q", "DEF 14A"),
    ("leadership_decision_record", "leadership_decisions"): ("8-K", "10-K", "10-Q", "DEF 14A"),
    ("leadership_decision_record", "decision_links"): ("8-K", "10-K", "10-Q", "DEF 14A"),
    ("ownership_insider_activity", "ownership_positions"): ("DEF 14A", "4", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"),
    ("ownership_insider_activity", "ownership_percentages"): ("DEF 14A", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"),
    ("ownership_insider_activity", "voting_control"): ("DEF 14A", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"),
    ("ownership_insider_activity", "institutional_positions"): ("DEF 14A", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"),
    ("ownership_insider_activity", "insider_transactions"): ("4", "4/A"),
    ("ownership_insider_activity", "transaction_plans"): ("4", "4/A", "8-K", "DEF 14A"),
    ("regulatory_litigation_calendar", "matter_list"): ("10-K", "10-Q", "8-K"),
    ("regulatory_litigation_calendar", "authorities"): ("10-K", "10-Q", "8-K"),
    ("regulatory_litigation_calendar", "future_dates"): ("8-K", "10-Q", "10-K"),
    ("regulatory_litigation_calendar", "exposure_context"): ("10-K", "10-Q", "8-K"),
    ("sector_theme_intelligence", "theme_exposures"): ("10-K", "10-Q", "8-K"),
    ("sector_theme_intelligence", "operating_exposure"): ("10-K", "10-Q", "8-K"),
    ("sector_theme_intelligence", "strategic_move_links"): ("8-K", "10-Q", "10-K"),
    ("sector_theme_intelligence", "kpi_links"): ("10-K", "10-Q", "8-K"),
    ("sector_theme_intelligence", "capital_allocation_links"): ("10-K", "10-Q", "8-K"),
    ("macro_sensitivity_profile", "macro_sensitivities"): ("10-K", "10-Q", "8-K"),
    ("macro_sensitivity_profile", "management_disclosures"): ("10-K", "10-Q", "8-K"),
    ("macro_sensitivity_profile", "calculated_relationships"): ("10-K", "10-Q"),
    ("macro_sensitivity_profile", "macro_series_alignment"): ("10-K", "10-Q"),
    ("macro_sensitivity_profile", "stress_examples"): ("10-K", "10-Q", "8-K"),
}


DEFAULT_GAP_FORMS = ("10-K", "10-Q", "8-K")
TICKERS_BY_SLUG = {slugify(seed.name): seed.ticker for seed in CROSS_SECTOR_COMPANIES}


@dataclass(frozen=True)
class GapSourceCollectionResult:
    companies_checked: int
    companies_collected: int
    sources_found: int
    sources_inserted: int
    duplicates_skipped: int
    failed: int


def collect_gap_sources(*, company: Company | None = None, limit: int = 20, filing_limit: int = 120, full_history: bool = False) -> GapSourceCollectionResult:
    gaps = SourceGap.objects.filter(status__in=[SourceGapStatus.OPEN, SourceGapStatus.IN_PROGRESS], company__isnull=False).select_related("company")
    if company is not None:
        gaps = gaps.filter(company=company)
    company_forms = forms_by_company(gaps)
    checked = 0
    collected = 0
    failed = 0
    totals = {"sources_found": 0, "sources_inserted": 0, "duplicates_skipped": 0}
    for target_company, forms in company_forms[:limit]:
        checked += 1
        ticker = ticker_for(target_company)
        if not ticker:
            failed += 1
            continue
        job = IngestionJob.objects.create(
            company=target_company,
            job_type=IngestionJobType.SOURCE_DISCOVERY,
            source="SEC_EDGAR_GAP",
            query=f"{ticker}: {', '.join(forms)}",
            status="PENDING",
        )
        try:
            counters = discover_sec_filings_for_company(
                company=target_company,
                source_document_model=SourceDocument,
                ticker=ticker,
                forms=forms,
                limit=filing_limit,
                full_history=full_history,
                job=job,
            )
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            job.save(update_fields=["status", "error_message", "updated_at"])
            failed += 1
            continue
        collected += 1
        for key in totals:
            totals[key] += counters.get(key, 0)
    return GapSourceCollectionResult(
        companies_checked=checked,
        companies_collected=collected,
        sources_found=totals["sources_found"],
        sources_inserted=totals["sources_inserted"],
        duplicates_skipped=totals["duplicates_skipped"],
        failed=failed,
    )


def forms_by_company(gaps) -> list[tuple[Company, tuple[str, ...]]]:
    forms: dict[int, set[str]] = {}
    companies: dict[int, Company] = {}
    for gap in gaps.order_by("company_id", "dashboard", "gap_type"):
        companies[gap.company_id] = gap.company
        forms.setdefault(gap.company_id, set()).update(forms_for_gap(gap.dashboard, gap.gap_type))
    return [(companies[company_id], tuple(sorted(forms[company_id]))) for company_id in sorted(companies)]


def forms_for_gap(dashboard: str, gap_type: str) -> tuple[str, ...]:
    return SOURCE_GAP_FORM_RULES.get((dashboard, gap_type), DEFAULT_GAP_FORMS)


def ticker_for(company: Company) -> str:
    universe_ticker = TICKERS_BY_SLUG.get(company.slug)
    if universe_ticker:
        return universe_ticker
    aliases = company.aliases if isinstance(company.aliases, list) else []
    for alias in aliases:
        value = str(alias).strip().upper()
        if value and len(value) <= 6 and " " not in value:
            return value
    return TICKERS_BY_SLUG.get(company.slug, "")

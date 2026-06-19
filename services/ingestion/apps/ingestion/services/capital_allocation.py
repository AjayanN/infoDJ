from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from apps.companies.models import (
    CapitalAllocationCategory,
    CapitalAllocationItem,
    CapitalAllocationPeriod,
    PromiseReviewStatus,
)
from apps.ingestion.models import FinancialFact, SourceDocument


DEPLOYMENT_CATEGORIES = {
    CapitalAllocationCategory.ACQUISITION_INVESTMENT,
    CapitalAllocationCategory.CAPEX,
    CapitalAllocationCategory.R_AND_D,
    CapitalAllocationCategory.BUYBACK,
    CapitalAllocationCategory.DIVIDEND,
    CapitalAllocationCategory.DEBT_REPAYMENT,
    CapitalAllocationCategory.RESTRUCTURING,
    CapitalAllocationCategory.CONTENT_INVENTORY,
    CapitalAllocationCategory.INTERNAL_PROGRAM,
}

CONCEPT_CATEGORY_MAP = {
    "PaymentsToAcquirePropertyPlantAndEquipment": CapitalAllocationCategory.CAPEX,
    "PaymentsToAcquireProductiveAssets": CapitalAllocationCategory.CAPEX,
    "CapitalExpenditures": CapitalAllocationCategory.CAPEX,
    "ResearchAndDevelopmentExpense": CapitalAllocationCategory.R_AND_D,
    "PaymentsForRepurchaseOfCommonStock": CapitalAllocationCategory.BUYBACK,
    "PaymentsForRepurchaseOfEquity": CapitalAllocationCategory.BUYBACK,
    "PaymentsOfDividends": CapitalAllocationCategory.DIVIDEND,
    "PaymentsOfDividendsCommonStock": CapitalAllocationCategory.DIVIDEND,
    "PaymentsToAcquireBusinessesNetOfCashAcquired": CapitalAllocationCategory.ACQUISITION_INVESTMENT,
    "PaymentsToAcquireInvestments": CapitalAllocationCategory.ACQUISITION_INVESTMENT,
    "PaymentsToAcquireAvailableForSaleSecurities": CapitalAllocationCategory.ACQUISITION_INVESTMENT,
    "ProceedsFromIssuanceOfLongTermDebt": CapitalAllocationCategory.DEBT_ISSUANCE,
    "ProceedsFromIssuanceOfDebt": CapitalAllocationCategory.DEBT_ISSUANCE,
    "RepaymentsOfLongTermDebt": CapitalAllocationCategory.DEBT_REPAYMENT,
    "RepaymentsOfDebt": CapitalAllocationCategory.DEBT_REPAYMENT,
    "PaymentsOfDebtIssuanceCosts": CapitalAllocationCategory.DEBT_REPAYMENT,
    "RestructuringCharges": CapitalAllocationCategory.RESTRUCTURING,
    "RestructuringAndRelatedCostIncurred": CapitalAllocationCategory.RESTRUCTURING,
    "InventoryWriteDown": CapitalAllocationCategory.CONTENT_INVENTORY,
    "NetCashProvidedByUsedInOperatingActivities": CapitalAllocationCategory.OPERATING_CASH_FLOW,
    "CashAndCashEquivalentsAtCarryingValue": CapitalAllocationCategory.CASH_CONTEXT,
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": CapitalAllocationCategory.CASH_CONTEXT,
}

CAPITAL_ALLOCATION_CONCEPTS = tuple(CONCEPT_CATEGORY_MAP)


def build_capital_allocation_periods(company) -> dict[str, int]:
    facts = list(
        FinancialFact.objects.filter(company=company, concept__in=CAPITAL_ALLOCATION_CONCEPTS)
        .exclude(accession_number="")
        .order_by("accession_number", "concept", "-filed", "-id")
    )
    grouped: dict[tuple[str, str, int | None, str], list[FinancialFact]] = defaultdict(list)
    for fact in facts:
        raw = fact.raw or {}
        end = raw.get("end") or fact.frame
        if not end or fact.fp not in {"Q1", "Q2", "Q3", "FY"}:
            continue
        grouped[(fact.accession_number, str(end), fact.fy, fact.fp)].append(fact)

    counters = {"periods_created": 0, "periods_updated": 0, "items_created": 0, "items_updated": 0, "skipped": 0}
    for (_accession, end_value, fy, fp), group in grouped.items():
        period_end = parse_fact_date(end_value)
        if period_end is None or fy is None:
            counters["skipped"] += 1
            continue
        source = source_for_filing(company, max((row.filed for row in group if row.filed), default=None), group[0].accession_number)
        period_start = latest_start_before_end(group, period_end)
        period, created = CapitalAllocationPeriod.objects.update_or_create(
            company=company,
            fiscal_year=fy,
            fiscal_period=fp,
            period_end=period_end,
            defaults={
                "period_start": period_start,
                "filed_date": max((row.filed for row in group if row.filed), default=None),
                "accession_number": group[0].accession_number,
                "cadence": "ANNUAL" if fp == "FY" else "QUARTERLY",
                "headline": f"{company.name} capital allocation for {fp} FY{fy}, period ended {period_end.isoformat()}.",
                "calculation_note": "Source-backed SEC Company Facts. Deployment totals exclude cash and operating cash-flow context; free cash flow is calculated only when operating cash flow and capex are both available.",
                "review_status": PromiseReviewStatus.REVIEWED,
                "is_published": True,
            },
        )
        counters["periods_created" if created else "periods_updated"] += 1
        item_counters = upsert_period_items(period, group, source)
        counters["items_created"] += item_counters["created"]
        counters["items_updated"] += item_counters["updated"]
        update_period_totals(period)
    return counters


def capital_allocation_quality_issues(company) -> list[str]:
    periods = company.capital_allocation_periods.filter(is_published=True, review_status=PromiseReviewStatus.REVIEWED)
    if not periods.exists():
        return ["no reviewed published capital allocation period"]
    latest = periods.order_by("-period_end", "-filed_date").first()
    issues = []
    if latest and not latest.items.filter(category=CapitalAllocationCategory.OPERATING_CASH_FLOW).exists():
        issues.append(f"{latest.fiscal_period} FY{latest.fiscal_year}: operating cash flow context unavailable")
    if latest and not latest.items.filter(category__in=DEPLOYMENT_CATEGORIES).exists():
        issues.append(f"{latest.fiscal_period} FY{latest.fiscal_year}: source-backed deployment item unavailable")
    return issues


def upsert_period_items(period: CapitalAllocationPeriod, facts: list[FinancialFact], source: SourceDocument | None) -> dict[str, int]:
    counters = {"created": 0, "updated": 0}
    latest_by_category: dict[str, FinancialFact] = {}
    for fact in facts:
        category = CONCEPT_CATEGORY_MAP.get(fact.concept)
        if not category:
            continue
        current = latest_by_category.get(category)
        if current is None or (fact.filed or date.min, bool(fact.frame), fact.id) > (current.filed or date.min, bool(current.frame), current.id):
            latest_by_category[category] = fact

    for category, fact in latest_by_category.items():
        is_context = category in {
            CapitalAllocationCategory.OPERATING_CASH_FLOW,
            CapitalAllocationCategory.CASH_CONTEXT,
            CapitalAllocationCategory.FREE_CASH_FLOW,
            CapitalAllocationCategory.DEBT_ISSUANCE,
        }
        label = fact.label or dict(CapitalAllocationCategory.choices).get(category, category)
        item, created = CapitalAllocationItem.objects.update_or_create(
            period=period,
            category=category,
            label=label[:255],
            concept=fact.concept,
            defaults={
                "value": abs(fact.value) if category in DEPLOYMENT_CATEGORIES else fact.value,
                "unit": fact.unit,
                "source_fact": fact,
                "source_document": source,
                "evidence_text": f"SEC Company Facts concept {fact.concept} from accession {fact.accession_number}.",
                "is_context": is_context,
                "is_calculated": False,
                "calculation_method": "",
                "confidence_score": "0.950",
                "review_status": PromiseReviewStatus.REVIEWED,
            },
        )
        counters["created" if created else "updated"] += 1

    ocf = latest_by_category.get(CapitalAllocationCategory.OPERATING_CASH_FLOW)
    capex = latest_by_category.get(CapitalAllocationCategory.CAPEX)
    if ocf and capex:
        value = ocf.value - abs(capex.value)
        _item, created = CapitalAllocationItem.objects.update_or_create(
            period=period,
            category=CapitalAllocationCategory.FREE_CASH_FLOW,
            label="Free cash flow",
            concept="calculated_free_cash_flow",
            defaults={
                "value": value,
                "unit": ocf.unit,
                "source_fact": ocf,
                "source_document": source,
                "evidence_text": "Calculated from operating cash flow minus capital expenditure for the same period.",
                "is_context": True,
                "is_calculated": True,
                "calculation_method": "NetCashProvidedByUsedInOperatingActivities - abs(capex concept)",
                "confidence_score": "0.900",
                "review_status": PromiseReviewStatus.REVIEWED,
            },
        )
        counters["created" if created else "updated"] += 1
    return counters


def update_period_totals(period: CapitalAllocationPeriod) -> None:
    items = list(period.items.filter(review_status=PromiseReviewStatus.REVIEWED))
    deployments = [row for row in items if row.category in DEPLOYMENT_CATEGORIES and not row.is_context]
    period.total_deployment = sum((row.value for row in deployments), Decimal("0")) if deployments else None
    period.operating_cash_flow = value_for_category(items, CapitalAllocationCategory.OPERATING_CASH_FLOW)
    period.cash_balance = value_for_category(items, CapitalAllocationCategory.CASH_CONTEXT)
    period.free_cash_flow = value_for_category(items, CapitalAllocationCategory.FREE_CASH_FLOW)
    period.save(update_fields=["total_deployment", "operating_cash_flow", "cash_balance", "free_cash_flow", "updated_at"])


def value_for_category(items: list[CapitalAllocationItem], category: str) -> Decimal | None:
    matches = [row.value for row in items if row.category == category]
    return matches[0] if matches else None


def parse_fact_date(value) -> date | None:
    if not value:
        return None
    text = str(value)
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return date.fromisoformat(text[:10])
    return None


def latest_start_before_end(facts: list[FinancialFact], period_end: date) -> date | None:
    starts = [parse_fact_date((row.raw or {}).get("start")) for row in facts]
    starts = [value for value in starts if value and value <= period_end]
    return max(starts) if starts else None


def source_for_filing(company, filed: date | None, accession: str) -> SourceDocument | None:
    if accession:
        source = SourceDocument.objects.filter(company=company, url__icontains=accession.replace("-", "")).first()
        if source:
            return source
    if filed:
        return (
            SourceDocument.objects.filter(company=company, source_api__icontains="SEC", published_date__date=filed)
            .order_by("-updated_at")
            .first()
        )
    return SourceDocument.objects.filter(company=company, source_api__icontains="SEC").order_by("-updated_at").first()

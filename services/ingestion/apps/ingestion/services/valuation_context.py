from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from apps.companies.models import (
    Company,
    CompanyProfileStatus,
    CompetitivePositionSnapshot,
    PromiseReviewStatus,
    ValuationApplicability,
    ValuationContextSnapshot,
    ValuationEventSnapshot,
    ValuationMeasureType,
    ValuationObservation,
    ValuationPeerComparison,
)
from apps.curation.models import BusinessEvent
from apps.ingestion.models import FinancialFact, MarketPrice, SourceDocument


DISCLAIMER = (
    "Valuation Context is research context only. It is not investment advice or a trading recommendation."
)

REVENUE_CONCEPTS = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet")
NET_INCOME_CONCEPTS = ("NetIncomeLoss", "ProfitLoss")
SHARE_CONCEPTS = (
    "EntityCommonStockSharesOutstanding",
    "CommonStocksIncludingAdditionalPaidInCapitalSharesOutstanding",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
)
DEBT_CONCEPTS = ("LongTermDebt", "LongTermDebtAndFinanceLeaseObligations", "ShortTermBorrowings", "DebtCurrent")
CASH_CONCEPTS = ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")


@dataclass(frozen=True)
class ValuationBuildResult:
    snapshots_created: int
    snapshots_updated: int
    observations_created: int
    observations_updated: int
    peer_rows_created: int
    peer_rows_updated: int
    event_rows_created: int
    event_rows_updated: int


def build_valuation_context(company: Company) -> dict[str, int]:
    price = latest_price(company)
    effective_date = price.price_date if price else date.today()
    source = latest_source(company)
    snapshot, created = ValuationContextSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": valuation_summary(company, price),
            "methodology": (
                "Calculated from stored market prices and SEC companyfacts. Multiples are shown only when the denominator "
                "is positive and meaningful. Enterprise value is unavailable unless debt and cash inputs are both present."
            ),
            "disclaimer": DISCLAIMER,
            "currency": "USD",
            "confidence_score": "0.820" if price else "0.600",
        },
    )
    counters = {
        "snapshots_created": 1 if created else 0,
        "snapshots_updated": 0 if created else 1,
        "observations_created": 0,
        "observations_updated": 0,
        "peer_rows_created": 0,
        "peer_rows_updated": 0,
        "event_rows_created": 0,
        "event_rows_updated": 0,
    }
    observations = build_observations(snapshot, company, price)
    counters["observations_created"] += observations["created"]
    counters["observations_updated"] += observations["updated"]
    peer_rows = build_peer_comparisons(snapshot)
    counters["peer_rows_created"] += peer_rows["created"]
    counters["peer_rows_updated"] += peer_rows["updated"]
    event_rows = build_event_snapshots(snapshot, company)
    counters["event_rows_created"] += event_rows["created"]
    counters["event_rows_updated"] += event_rows["updated"]
    return counters


def valuation_quality_issues(company: Company) -> list[str]:
    snapshot = (
        ValuationContextSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("observations")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed valuation context snapshot"]
    issues = []
    if not snapshot.observations.exists():
        issues.append("no valuation observations")
    if not snapshot.observations.filter(measure=ValuationMeasureType.MARKET_CAP, applicability=ValuationApplicability.APPLICABLE).exists():
        issues.append("market capitalization unavailable")
    if not snapshot.disclaimer:
        issues.append("research-context disclaimer unavailable")
    return issues


def build_observations(snapshot: ValuationContextSnapshot, company: Company, price: MarketPrice | None) -> dict[str, int]:
    latest_revenue = latest_fact(company, REVENUE_CONCEPTS, unit="USD")
    latest_income = latest_fact(company, NET_INCOME_CONCEPTS, unit="USD")
    latest_shares = latest_fact(company, SHARE_CONCEPTS)
    debt = sum_latest_facts(company, DEBT_CONCEPTS)
    cash = sum_latest_facts(company, CASH_CONCEPTS)
    market_cap = price.close_price * latest_shares.value if price and price.close_price and latest_shares else None
    enterprise_value = market_cap + debt - cash if market_cap is not None and debt is not None and cash is not None else None
    specs = [
        observation_spec(
            ValuationMeasureType.MARKET_CAP,
            market_cap,
            "USD",
            "Market capitalization = close price x shares outstanding",
            price,
            latest_shares,
            numerator=price.close_price if price else None,
            numerator_label="Close price",
            denominator=latest_shares.value if latest_shares else None,
            denominator_label="Shares outstanding",
            source_period=fact_period(latest_shares),
            missing_reason=missing_market_cap_reason(price, latest_shares),
        ),
        observation_spec(
            ValuationMeasureType.PRICE_TO_SALES,
            ratio(market_cap, latest_revenue.value if latest_revenue else None),
            "x",
            "Price to sales = market capitalization / latest annual revenue",
            price,
            latest_revenue,
            numerator=market_cap,
            numerator_label="Market capitalization",
            denominator=latest_revenue.value if latest_revenue else None,
            denominator_label="Revenue",
            source_period=fact_period(latest_revenue),
            missing_reason=missing_ratio_reason(market_cap, latest_revenue, "revenue"),
        ),
        observation_spec(
            ValuationMeasureType.PRICE_TO_EARNINGS,
            ratio(market_cap, latest_income.value if latest_income else None),
            "x",
            "Price to earnings = market capitalization / latest annual net income",
            price,
            latest_income,
            numerator=market_cap,
            numerator_label="Market capitalization",
            denominator=latest_income.value if latest_income else None,
            denominator_label="Net income",
            source_period=fact_period(latest_income),
            missing_reason=missing_ratio_reason(market_cap, latest_income, "net income"),
        ),
        observation_spec(
            ValuationMeasureType.ENTERPRISE_VALUE,
            enterprise_value,
            "USD",
            "Enterprise value = market capitalization + debt - cash",
            price,
            latest_revenue,
            numerator=market_cap,
            numerator_label="Market capitalization",
            denominator=None,
            denominator_label="Debt and cash adjustments",
            source_period=fact_period(latest_revenue),
            missing_reason="" if enterprise_value is not None else "Debt and cash inputs are not both available from reviewed financial facts.",
        ),
        observation_spec(
            ValuationMeasureType.EV_TO_REVENUE,
            ratio(enterprise_value, latest_revenue.value if latest_revenue else None),
            "x",
            "EV to revenue = enterprise value / latest annual revenue",
            price,
            latest_revenue,
            numerator=enterprise_value,
            numerator_label="Enterprise value",
            denominator=latest_revenue.value if latest_revenue else None,
            denominator_label="Revenue",
            source_period=fact_period(latest_revenue),
            missing_reason=missing_ratio_reason(enterprise_value, latest_revenue, "revenue"),
        ),
    ]
    created = updated = 0
    keep_ids = set()
    for spec in specs:
        row, was_created = ValuationObservation.objects.update_or_create(
            snapshot=snapshot,
            measure=spec["measure"],
            defaults=spec,
        )
        keep_ids.add(row.id)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    snapshot.observations.exclude(id__in=keep_ids).delete()
    return {"created": created, "updated": updated}


def build_peer_comparisons(snapshot: ValuationContextSnapshot) -> dict[str, int]:
    peers = reviewed_peers(snapshot.company)
    company_metrics = {row.measure: row for row in snapshot.observations.all()}
    created = updated = 0
    keep_ids = set()
    for peer in peers[:8]:
        peer_snapshot = (
            ValuationContextSnapshot.objects.filter(company=peer, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
            .prefetch_related("observations")
            .order_by("-effective_date", "-updated_at")
            .first()
        )
        for measure in (ValuationMeasureType.PRICE_TO_SALES, ValuationMeasureType.PRICE_TO_EARNINGS, ValuationMeasureType.EV_TO_REVENUE):
            company_row = company_metrics.get(measure)
            peer_row = None
            if peer_snapshot:
                peer_row = next((row for row in peer_snapshot.observations.all() if row.measure == measure), None)
            comparison, was_created = ValuationPeerComparison.objects.update_or_create(
                snapshot=snapshot,
                peer_name=peer.name,
                measure=measure,
                defaults={
                    "peer_company": peer,
                    "peer_value": peer_row.value if peer_row and peer_row.applicability == ValuationApplicability.APPLICABLE else None,
                    "company_value": company_row.value if company_row and company_row.applicability == ValuationApplicability.APPLICABLE else None,
                    "comparison_note": peer_note(snapshot.company, peer, company_row, peer_row),
                    "applicability": (
                        ValuationApplicability.APPLICABLE
                        if company_row and peer_row and company_row.value is not None and peer_row.value is not None
                        else ValuationApplicability.UNAVAILABLE_INPUT
                    ),
                    "evidence_text": f"{peer.name} is a reviewed configured peer for valuation context; comparison is descriptive and not a recommendation.",
                    "confidence_score": "0.760" if peer_row else "0.620",
                },
            )
            keep_ids.add(comparison.id)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
    if keep_ids:
        snapshot.peer_comparisons.exclude(id__in=keep_ids).delete()
    return {"created": created, "updated": updated}


def build_event_snapshots(snapshot: ValuationContextSnapshot, company: Company) -> dict[str, int]:
    ticker = ticker_for_company(company)
    if not ticker:
        return {"created": 0, "updated": 0}
    created = updated = 0
    keep_ids = set()
    events = BusinessEvent.objects.filter(company=company, review_status__in=["NEEDS_REVIEW", "APPROVED"]).order_by("-event_date", "-created_at")[:6]
    for event in events:
        if not event.event_date:
            continue
        before = price_on_or_before(company, ticker, event.event_date - timedelta(days=1))
        after = price_on_or_after(company, ticker, event.event_date + timedelta(days=1))
        if not before or not after or not before.close_price or not after.close_price:
            continue
        shares = latest_fact(company, SHARE_CONCEPTS)
        before_cap = before.close_price * shares.value if shares else None
        after_cap = after.close_price * shares.value if shares else None
        row, was_created = ValuationEventSnapshot.objects.update_or_create(
            snapshot=snapshot,
            event_date=event.event_date,
            event_label=(event.actual_change or event.source_claim or event.event_type)[:255],
            measure=ValuationMeasureType.MARKET_CAP,
            defaults={
                "event": event,
                "before_value": before_cap,
                "after_value": after_cap,
                "before_date": before.price_date,
                "after_date": after.price_date,
                "context_note": "Before/after values are event-aligned context only and do not claim the event caused the valuation movement.",
                "confidence_score": "0.740" if before_cap is not None and after_cap is not None else "0.600",
            },
        )
        keep_ids.add(row.id)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    if keep_ids:
        snapshot.event_snapshots.exclude(id__in=keep_ids).delete()
    return {"created": created, "updated": updated}


def observation_spec(
    measure: str,
    value: Decimal | None,
    unit: str,
    formula: str,
    price: MarketPrice | None,
    source_fact: FinancialFact | None,
    *,
    numerator: Decimal | None,
    numerator_label: str,
    denominator: Decimal | None,
    denominator_label: str,
    source_period: str,
    missing_reason: str,
) -> dict[str, object]:
    applicability = ValuationApplicability.APPLICABLE if value is not None else ValuationApplicability.UNAVAILABLE_INPUT
    if denominator is not None and denominator <= 0:
        applicability = ValuationApplicability.NOT_MEANINGFUL
    return {
        "measure": measure,
        "value": value,
        "unit": unit,
        "currency": "USD" if unit == "USD" else "",
        "market_price": price,
        "numerator": numerator,
        "numerator_label": numerator_label,
        "denominator": denominator,
        "denominator_label": denominator_label,
        "formula": formula,
        "source_period": source_period,
        "applicability": applicability,
        "unavailable_reason": missing_reason if value is None else "",
        "evidence_text": evidence_text(measure, price, source_fact, missing_reason),
        "source_document": source_for_fact(source_fact) if source_fact else None,
        "source_facts": [source_fact_payload(source_fact)] if source_fact else [],
        "confidence_score": "0.820" if value is not None else "0.620",
        "review_status": PromiseReviewStatus.REVIEWED,
    }


def latest_price(company: Company) -> MarketPrice | None:
    return MarketPrice.objects.filter(company=company).exclude(close_price__isnull=True).order_by("-price_date", "-id").first()


def latest_fact(company: Company, concepts: tuple[str, ...], *, unit: str = "") -> FinancialFact | None:
    queryset = FinancialFact.objects.filter(company=company, concept__in=concepts)
    if unit:
        queryset = queryset.filter(unit=unit)
    return queryset.order_by("-fy", "-filed", "-id").first()


def sum_latest_facts(company: Company, concepts: tuple[str, ...]) -> Decimal | None:
    values = []
    for concept in concepts:
        fact = latest_fact(company, (concept,), unit="USD")
        if fact:
            values.append(fact.value)
    return sum(values, Decimal("0")) if values else None


def ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    try:
        return numerator / denominator
    except (InvalidOperation, ZeroDivisionError):
        return None


def missing_market_cap_reason(price: MarketPrice | None, shares: FinancialFact | None) -> str:
    missing = []
    if price is None:
        missing.append("market price")
    if shares is None:
        missing.append("shares outstanding")
    return f"Missing {' and '.join(missing)} input." if missing else ""


def missing_ratio_reason(numerator: Decimal | None, denominator_fact: FinancialFact | None, denominator_label: str) -> str:
    if numerator is None:
        return "Numerator is unavailable because required market value inputs are missing."
    if denominator_fact is None:
        return f"{denominator_label.title()} denominator is unavailable from reviewed financial facts."
    if denominator_fact.value <= 0:
        return f"{denominator_label.title()} denominator is non-positive, so the multiple is not meaningful."
    return ""


def valuation_summary(company: Company, price: MarketPrice | None) -> str:
    if price is None:
        return f"Valuation context for {company.name} is unavailable until market price data is collected."
    return f"{company.name} valuation context uses stored market price data through {price.price_date} and reviewed SEC companyfacts where available."


def evidence_text(measure: str, price: MarketPrice | None, fact: FinancialFact | None, missing_reason: str) -> str:
    if missing_reason:
        return missing_reason
    parts = [f"{measure} calculated from stored market price {price.price_date} ({price.provider})."] if price else []
    if fact:
        parts.append(f"Denominator/input uses {fact.concept} for FY{fact.fy or 'unknown'} {fact.fp or ''}, filed {fact.filed or 'date unavailable'}.")
    return " ".join(parts)


def source_fact_payload(fact: FinancialFact) -> dict[str, object]:
    return {
        "id": fact.id,
        "concept": fact.concept,
        "label": fact.label,
        "unit": fact.unit,
        "fy": fact.fy,
        "fp": fact.fp,
        "filed": fact.filed.isoformat() if fact.filed else None,
        "accession_number": fact.accession_number,
    }


def fact_period(fact: FinancialFact | None) -> str:
    if fact is None:
        return ""
    return f"FY{fact.fy or 'unknown'} {fact.fp or ''}".strip()


def source_for_fact(fact: FinancialFact | None) -> SourceDocument | None:
    if not fact or not fact.accession_number:
        return None
    return SourceDocument.objects.filter(company=fact.company, url__icontains=fact.accession_number.replace("-", "")).first() or SourceDocument.objects.filter(company=fact.company).order_by("-published_date", "-updated_at").first()


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def reviewed_peers(company: Company) -> list[Company]:
    snapshot = (
        CompetitivePositionSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("peers__peer_company")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot:
        peers = [peer.peer_company for peer in snapshot.peers.all() if peer.peer_company_id]
        if peers:
            return unique_companies(peers)
    return list(Company.objects.filter(is_active=True, industry=company.industry).exclude(id=company.id).order_by("name")[:6])


def unique_companies(companies: list[Company]) -> list[Company]:
    seen = set()
    rows = []
    for company in companies:
        if company.id in seen:
            continue
        seen.add(company.id)
        rows.append(company)
    return rows


def peer_note(company: Company, peer: Company, company_row: ValuationObservation | None, peer_row: ValuationObservation | None) -> str:
    if company_row and peer_row and company_row.value is not None and peer_row.value is not None:
        return f"{company.name} and {peer.name} both have reproducible values for this measure; comparison is descriptive context only."
    return "Peer comparison unavailable because one side lacks a meaningful, reproducible measure."


def ticker_for_company(company: Company) -> str:
    aliases = company.aliases if isinstance(company.aliases, list) else []
    return str(aliases[0]).strip() if aliases else ""


def price_on_or_before(company: Company, ticker: str, price_date: date) -> MarketPrice | None:
    return (
        MarketPrice.objects.filter(company=company, price_date__lte=price_date)
        .filter(ticker_query(ticker))
        .order_by("-price_date")
        .first()
    )


def price_on_or_after(company: Company, ticker: str, price_date: date) -> MarketPrice | None:
    return (
        MarketPrice.objects.filter(company=company, price_date__gte=price_date)
        .filter(ticker_query(ticker))
        .order_by("price_date")
        .first()
    )


def ticker_query(ticker: str):
    from django.db.models import Q

    normalized = ticker.strip().lower()
    stooq = normalized if "." in normalized else f"{normalized}.us"
    return Q(ticker__iexact=ticker) | Q(ticker__iexact=stooq)

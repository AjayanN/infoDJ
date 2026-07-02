from __future__ import annotations

import re
from dataclasses import dataclass

from django.db.models import Q

from apps.companies.models import Company
from apps.ingestion.models import SourceDocument, SourceGap, SourceGapResolutionCandidate, SourceGapStatus


SOURCE_RULES = {
    ("acquisition_lifecycle", "acquisition_deals"): {
        "candidate_type": "acquisition_source",
        "keywords": (
            "acquisition",
            "acquire",
            "acquired",
            "merger",
            "purchase",
            "purchased",
            "subsidiary",
            "business combination",
            "company history",
        ),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "WIKIPEDIA_PAGE", "WIKIPEDIA_REFERENCES", "GDELT_DOC_2"),
        "next_action": "Extract named target, announcement date, consideration, rationale, approvals, integration progress, and outcome from this source before creating reviewed lifecycle rows.",
    },
    ("acquisition_lifecycle", "acquisition_deal_terms"): {
        "candidate_type": "acquisition_terms_source",
        "keywords": (
            "purchase price",
            "cash and stock",
            "consideration",
            "synergies",
            "integration",
            "regulatory approval",
            "closed the acquisition",
        ),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract consideration, payment form, approval status, synergy promise, and integration/outcome evidence.",
    },
    ("competitive_position", "competitive_market_share"): {
        "candidate_type": "market_share_source",
        "keywords": ("market share", "share position", "ranked", "leader", "competitive position", "industry position"),
        "sources": ("SEC", "SEC_EDGAR", "OFFICIAL_WEBSITE", "WIKIPEDIA_REFERENCES", "GDELT_DOC_2"),
        "next_action": "Extract dated market-share or rank evidence and keep estimates separate from company-reported disclosures.",
    },
    ("customer_supplier_dependency", "named_counterparties"): {
        "candidate_type": "dependency_counterparty_source",
        "keywords": ("customer concentration", "major customer", "supplier", "vendor", "counterparty", "depends on", "material customer"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE"),
        "next_action": "Extract named customer, supplier, platform, distributor, or infrastructure counterparties with disclosure confidence.",
    },
    ("customer_supplier_dependency", "concentration_percentages"): {
        "candidate_type": "dependency_concentration_source",
        "keywords": ("10% of revenue", "percentage of revenue", "concentration", "accounted for", "net sales", "major customer"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"),
        "next_action": "Extract disclosed percentage, period, denominator, and whether the counterparty is named or unnamed.",
    },
    ("customer_supplier_dependency", "dependency_contract_terms"): {
        "candidate_type": "dependency_contract_source",
        "keywords": ("minimum commitment", "exclusive", "renewal", "termination", "supply agreement", "distribution agreement", "material contract"),
        "sources": ("SEC_EDGAR_EXHIBIT", "SEC", "SEC_EDGAR", "OFFICIAL_WEBSITE"),
        "next_action": "Extract renewal, exclusivity, minimum commitment, termination, and duration terms before surfacing contract risk.",
    },
    ("product_pricing_history", "product_list_prices"): {
        "candidate_type": "product_price_source",
        "keywords": ("pricing", "price", "subscription", "plan", "tier", "package", "launch", "list price"),
        "sources": ("OFFICIAL_WEBSITE", "SEC", "SEC_EDGAR", "WIKIPEDIA_REFERENCES", "GDELT_DOC_2"),
        "next_action": "Extract product, plan, list price, currency, geography, effective date, and source date.",
    },
    ("geographic_expansion", "market_entry_dates"): {
        "candidate_type": "market_entry_source",
        "keywords": ("international", "expansion", "entered", "launched in", "market entry", "new market", "country"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "WIKIPEDIA_REFERENCES", "GDELT_DOC_2"),
        "next_action": "Extract market, entry or exit date, source date, and whether the disclosure is country-specific or region-level.",
    },
    ("geographic_expansion", "local_partnerships"): {
        "candidate_type": "local_partnership_source",
        "keywords": ("partnership", "partner", "joint venture", "local", "distribution agreement", "license"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract named local partner, geography, relationship type, and source evidence before publishing.",
    },
    ("geographic_expansion", "regulatory_barriers"): {
        "candidate_type": "market_regulatory_source",
        "keywords": ("regulatory", "approval", "license", "restriction", "foreign", "country risk", "compliance"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE"),
        "next_action": "Extract market-specific regulatory barrier, approval, licensing requirement, and business exposure.",
    },
    ("geographic_expansion", "revenue_contribution"): {
        "candidate_type": "geographic_revenue_source",
        "keywords": ("geographic", "revenue", "international", "region", "net sales", "segment"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"),
        "next_action": "Extract region or country revenue, period, currency, and whether the disclosure is segment-level or market-level.",
    },
    ("geographic_expansion", "expansion_outcomes"): {
        "candidate_type": "expansion_outcome_source",
        "keywords": ("growth", "international", "expansion", "outcome", "performance", "market", "exited"),
        "sources": ("SEC", "SEC_EDGAR", "OFFICIAL_WEBSITE", "WIKIPEDIA_REFERENCES", "GDELT_DOC_2"),
        "next_action": "Extract later evidence that describes the result of an expansion, exit, or market scaling decision.",
    },
    ("ownership_insider_activity", "ownership_percentages"): {
        "candidate_type": "ownership_percentage_source",
        "keywords": ("beneficial ownership", "owned", "shares beneficially", "proxy statement", "DEF 14A", "13D", "13G", "SC 13D", "SC 13G"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"),
        "next_action": "Extract disclosed holder, share class, economic ownership percentage, report date, and filing form without estimating missing values.",
    },
    ("ownership_insider_activity", "voting_control"): {
        "candidate_type": "voting_control_source",
        "keywords": ("voting power", "voting control", "Class B", "dual class", "vote", "proxy statement", "DEF 14A"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"),
        "next_action": "Extract voting power, share class, holder, and date from proxy or share-class disclosures.",
    },
    ("ownership_insider_activity", "institutional_positions"): {
        "candidate_type": "institutional_position_source",
        "keywords": ("institutional ownership", "13G", "13D", "SC 13G", "SC 13D", "13F", "beneficial owner", "BlackRock", "Vanguard"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"),
        "next_action": "Extract disclosed institution, position type, percentage or shares, filing date, and form.",
    },
    ("ownership_insider_activity", "insider_transactions"): {
        "candidate_type": "insider_transaction_source",
        "keywords": ("Form 4", " 4 filing", "4/A", "insider transaction", "sale", "purchase", "option exercise", "restricted stock", "grant"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"),
        "next_action": "Extract transaction date, insider, role, transaction code/type, shares, price, ownership after, and source form.",
    },
    ("ownership_insider_activity", "transaction_plans"): {
        "candidate_type": "transaction_plan_source",
        "keywords": ("10b5-1", "trading plan", "planned sale", "Rule 10b5-1", "prearranged trading", "Form 4", " 4 filing"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE"),
        "next_action": "Extract plan reference, adoption or termination date, related Form 4 footnote, and transaction scope.",
    },
    ("regulatory_litigation_calendar", "matter_list"): {
        "candidate_type": "regulatory_matter_source",
        "keywords": ("legal proceedings", "litigation", "lawsuit", "investigation", "regulatory", "proceeding", "settlement", "consent decree"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract matter title, type, jurisdiction, authority, allegation or issue, company response, and current status without legal conclusions.",
    },
    ("regulatory_litigation_calendar", "authorities"): {
        "candidate_type": "regulatory_authority_source",
        "keywords": ("SEC", "FTC", "DOJ", "European Commission", "court", "regulator", "agency", "authority", "commission"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract named regulator, court, jurisdiction, and matter reference from authoritative source text.",
    },
    ("regulatory_litigation_calendar", "future_dates"): {
        "candidate_type": "regulatory_deadline_source",
        "keywords": ("hearing", "deadline", "response due", "decision", "appeal", "compliance", "expiration", "approval expected"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract sourced hearing, response, decision, appeal, compliance, or expiration dates with date type and uncertainty.",
    },
    ("regulatory_litigation_calendar", "exposure_context"): {
        "candidate_type": "regulatory_exposure_source",
        "keywords": ("fine", "penalty", "settlement", "remedy", "injunction", "restriction", "material adverse", "liability", "loss contingency"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract only source-stated amounts, ranges, remedies, restrictions, uncertainty language, and affected business area.",
    },
    ("sector_theme_intelligence", "theme_exposures"): {
        "candidate_type": "theme_exposure_source",
        "keywords": ("artificial intelligence", "AI", "cloud", "advertising", "electric vehicle", "energy transition", "commodity", "interest rates", "supply chain", "cybersecurity", "data privacy"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract theme, exposure type, source-stated evidence, date, and whether it is operating exposure or narrative context.",
    },
    ("sector_theme_intelligence", "operating_exposure"): {
        "candidate_type": "theme_operating_exposure_source",
        "keywords": ("revenue", "cost", "capital expenditure", "capex", "R&D", "customers", "suppliers", "production", "capacity", "demand", "operating results"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract operating evidence that links a theme to revenue, cost, capex, product, customer, supply-chain, or regulatory exposure.",
    },
    ("sector_theme_intelligence", "strategic_move_links"): {
        "candidate_type": "theme_event_link_source",
        "keywords": ("announced", "launched", "expanded", "invested", "partnership", "acquisition", "restructuring", "regulatory", "approval"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Link reviewed strategic move evidence to a reviewed theme without treating generic mentions as exposure.",
    },
    ("sector_theme_intelligence", "kpi_links"): {
        "candidate_type": "theme_kpi_source",
        "keywords": ("users", "subscribers", "customers", "ARPU", "occupancy", "production", "deliveries", "bookings", "churn", "volume"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE"),
        "next_action": "Map company-specific KPI definitions and observations to theme exposure only when the metric directly measures exposure.",
    },
    ("sector_theme_intelligence", "capital_allocation_links"): {
        "candidate_type": "theme_capital_source",
        "keywords": ("capital expenditures", "research and development", "R&D", "acquisition", "investment", "content", "debt", "repurchase", "dividend"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"),
        "next_action": "Map reviewed capital deployment rows to relevant themes with amount, period, category, and source evidence.",
    },
    ("leadership_decision_record", "tenure_dates"): {
        "candidate_type": "leadership_tenure_source",
        "keywords": ("chief executive", "CEO", "appointed", "named", "effective", "retired", "resigned", "succession"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract leader name, role, appointment or departure date, interim status, and whether the source states a succession plan.",
    },
    ("leadership_decision_record", "transition_events"): {
        "candidate_type": "leadership_transition_source",
        "keywords": ("leadership change", "succession", "appointed", "departed", "resigned", "retired", "board", "named"),
        "sources": ("SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract transition type, date, predecessor/successor if disclosed, and avoid unsupported departure reasons.",
    },
    ("leadership_decision_record", "leadership_decisions"): {
        "candidate_type": "leadership_decision_source",
        "keywords": ("strategic priorities", "strategy", "initiative", "announced", "decision", "capital allocation", "acquisition"),
        "sources": ("SEC", "SEC_EDGAR", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Extract dated priorities or material decisions and link to existing strategic turns, promises, milestones, acquisitions, or allocation rows.",
    },
    ("leadership_decision_record", "decision_links"): {
        "candidate_type": "leadership_link_source",
        "keywords": ("strategy", "priority", "milestone", "target", "capital allocation", "acquisition", "investment"),
        "sources": ("SEC", "SEC_EDGAR", "OFFICIAL_WEBSITE", "GDELT_DOC_2"),
        "next_action": "Map the leadership claim to the canonical owner feature instead of duplicating the fact.",
    },
}


@dataclass(frozen=True)
class ResolverResult:
    gaps_checked: int
    candidates_created: int
    candidates_updated: int


def resolve_source_gaps(*, company: Company | None = None, limit: int = 500) -> ResolverResult:
    gaps = SourceGap.objects.filter(status__in=[SourceGapStatus.OPEN, SourceGapStatus.IN_PROGRESS]).select_related("company")
    if company is not None:
        gaps = gaps.filter(Q(company=company) | Q(company__isnull=True))
    created = 0
    updated = 0
    checked = 0
    for gap in gaps.order_by("company_id", "dashboard", "gap_type")[:limit]:
        checked += 1
        counters = resolve_gap(gap)
        created += counters["created"]
        updated += counters["updated"]
    return ResolverResult(gaps_checked=checked, candidates_created=created, candidates_updated=updated)


def resolve_gap(gap: SourceGap) -> dict[str, int]:
    rule = SOURCE_RULES.get((gap.dashboard, gap.gap_type))
    if rule is None:
        return {"created": 0, "updated": 0}
    documents = candidate_documents(gap, rule)
    created = 0
    updated = 0
    for document in documents:
        evidence = evidence_excerpt(document, rule["keywords"])
        confidence = confidence_for(document, evidence, rule["sources"], rule["keywords"])
        candidate, was_created = SourceGapResolutionCandidate.objects.update_or_create(
            company=gap.company,
            source_gap=gap,
            dashboard=gap.dashboard,
            gap_type=gap.gap_type,
            source_document=document,
            candidate_type=rule["candidate_type"],
            defaults={
                "evidence_text": evidence,
                "confidence_score": f"{confidence:.3f}",
                "extraction_status": "CANDIDATE",
                "review_status": "NEEDS_REVIEW",
                "next_action": rule["next_action"],
                "metadata": {
                    "source_api": document.source_api,
                    "source_title": document.title,
                    "source_url": document.canonical_url or document.url,
                    "rule_keywords": list(rule["keywords"]),
                },
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    if created or updated:
        gap.status = SourceGapStatus.IN_PROGRESS
        gap.metadata = {
            **(gap.metadata if isinstance(gap.metadata, dict) else {}),
            "resolution_candidate_count": SourceGapResolutionCandidate.objects.filter(source_gap=gap).count(),
        }
        gap.save(update_fields=["status", "metadata", "updated_at"])
    return {"created": created, "updated": updated}


def candidate_documents(gap: SourceGap, rule: dict[str, object]) -> list[SourceDocument]:
    if gap.company_id is None:
        return []
    keywords = tuple(str(keyword).lower() for keyword in rule["keywords"])
    query = Q()
    for keyword in keywords:
        query |= Q(title__icontains=keyword) | Q(snippet__icontains=keyword) | Q(url__icontains=keyword)
    documents = (
        SourceDocument.objects.filter(company=gap.company, source_api__in=rule["sources"])
        .filter(query)
        .order_by("-published_date", "-updated_at")[:8]
    )
    return list(documents)


def evidence_excerpt(document: SourceDocument, keywords: tuple[str, ...]) -> str:
    text = " ".join(part for part in (document.title, document.snippet) if part).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return document.canonical_url or document.url
    lowered = text.lower()
    first_match = min((lowered.find(keyword.lower()) for keyword in keywords if keyword.lower() in lowered), default=-1)
    if first_match < 0:
        return text[:500]
    start = max(first_match - 140, 0)
    end = min(first_match + 360, len(text))
    return text[start:end].strip()


def confidence_for(document: SourceDocument, evidence: str, source_apis: tuple[str, ...], keywords: tuple[str, ...]) -> float:
    confidence = 0.45
    if document.source_api in source_apis:
        confidence += 0.15
    lowered = evidence.lower()
    matched_keywords = sum(1 for keyword in keywords if keyword.lower() in lowered)
    confidence += min(matched_keywords * 0.06, 0.24)
    if document.published_date:
        confidence += 0.04
    if document.status in {"APPROVED", "EXTRACTED"}:
        confidence += 0.07
    return min(confidence, 0.90)

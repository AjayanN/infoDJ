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

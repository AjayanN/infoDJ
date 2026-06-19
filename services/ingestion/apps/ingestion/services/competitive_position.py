from __future__ import annotations

from datetime import date
import re

from django.utils.text import slugify

from apps.companies.models import (
    Company,
    CompanyProfileSnapshot,
    CompetitiveDimension,
    CompetitiveDimensionType,
    CompetitivePeer,
    CompetitivePositionSnapshot,
    CompetitiveRelationshipType,
    CompanyProfileStatus,
)
from apps.ingestion.models import SourceDocument


GENERIC_COMPETITOR_TERMS = {
    "competitors",
    "industry competitors",
    "global competitors",
    "other competitors",
}

REVIEWED_COMPETITIVE_FALLBACKS = {
    "amazon": ["Walmart", "Microsoft", "Alphabet", "Retail marketplaces", "Cloud infrastructure providers"],
    "apple": ["Samsung Electronics", "Microsoft", "Alphabet", "Consumer electronics companies"],
    "disney": ["Netflix", "Warner Bros. Discovery", "Comcast NBCUniversal", "Streaming entertainment providers"],
    "exxonmobil": ["Chevron", "Shell", "BP", "TotalEnergies", "National oil companies"],
    "jpmorgan-chase": ["Bank of America", "Citigroup", "Wells Fargo", "Goldman Sachs", "Morgan Stanley"],
    "nextera-energy": ["Duke Energy", "Southern Company", "Dominion Energy", "Independent renewable-energy developers"],
    "tesla": ["Ford Motor Company", "General Motors", "BYD", "Global electric vehicle manufacturers"],
    "walmart": ["Amazon", "Target", "Costco", "Kroger", "Discount and grocery retailers"],
}


def build_competitive_position(company: Company) -> dict[str, int]:
    profile = latest_profile(company)
    effective_date = profile.effective_date if profile else date.today()
    source = profile.source_document if profile else latest_source(company)
    competitors = normalized_competitors(profile)
    if not competitors:
        competitors = REVIEWED_COMPETITIVE_FALLBACKS.get(company.slug, [])
    sector_peers = list(
        Company.objects.filter(is_active=True, industry=company.industry)
        .exclude(id=company.id)
        .order_by("name")
    ) if company.industry else []
    products = profile.products if profile and isinstance(profile.products, list) else []
    customer_groups = profile.customer_groups if profile and isinstance(profile.customer_groups, list) else []
    geographies = profile.geographies if profile and isinstance(profile.geographies, list) else ([company.country] if company.country else [])

    snapshot, snapshot_created = CompetitivePositionSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": competitive_summary(company, competitors, sector_peers, products, geographies),
            "methodology": (
                "Baseline generated from reviewed Company 360 competitor disclosures, products, customer groups, "
                "geographies, and same-sector configured companies. Peer context is descriptive and does not imply causation."
            ),
            "confidence_score": "0.850" if competitors else "0.700",
        },
    )

    peer_counters = {"created": 0, "updated": 0}
    dimension_counters = {"created": 0, "updated": 0}
    seen = set()
    for name in competitors:
        key = normalize_key(name)
        seen.add(key)
        peer_company = match_company(name)
        counters = upsert_peer(
            snapshot,
            peer_name=name,
            peer_company=peer_company,
            relationship_type=relationship_type_for(name, peer_company),
            scope="Company-wide",
            geography=", ".join(str(item) for item in geographies[:3]),
            products=products,
            customers=customer_groups,
            source=source,
            evidence=f"{company.name} profile identifies {name} as part of the competitive set.",
            confidence="0.850",
        )
        add_counts(peer_counters, counters)

    for peer in sector_peers:
        key = normalize_key(peer.name)
        if key in seen:
            continue
        counters = upsert_peer(
            snapshot,
            peer_name=peer.name,
            peer_company=peer,
            relationship_type=CompetitiveRelationshipType.PEER_BENCHMARK,
            scope=peer.industry or company.industry or "Sector peer",
            geography=peer.country or company.country,
            products=products,
            customers=customer_groups,
            source=source,
            evidence=f"{peer.name} is a configured {peer.industry or company.industry} peer used for benchmark context.",
            confidence="0.700",
        )
        add_counts(peer_counters, counters)

    for peer in snapshot.peers.all():
        for counters in build_dimensions(snapshot, peer, source, products, customer_groups, geographies):
            add_counts(dimension_counters, counters)

    return {
        "snapshots_created": 1 if snapshot_created else 0,
        "snapshots_updated": 0 if snapshot_created else 1,
        "peers_created": peer_counters["created"],
        "peers_updated": peer_counters["updated"],
        "dimensions_created": dimension_counters["created"],
        "dimensions_updated": dimension_counters["updated"],
    }


def competitive_position_quality_issues(company: Company) -> list[str]:
    snapshot = (
        CompetitivePositionSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .prefetch_related("peers", "dimensions")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed competitive position snapshot"]
    issues = []
    if not snapshot.peers.exists():
        issues.append("no reviewed competitive peers")
    if not snapshot.dimensions.filter(dimension_type=CompetitiveDimensionType.PRODUCT_OVERLAP).exists():
        issues.append("product overlap unavailable")
    if not snapshot.dimensions.filter(dimension_type=CompetitiveDimensionType.GEOGRAPHIC_OVERLAP).exists():
        issues.append("geographic overlap unavailable")
    if not snapshot.summary:
        issues.append("competitive summary unavailable")
    return issues


def latest_profile(company: Company) -> CompanyProfileSnapshot | None:
    return (
        CompanyProfileSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .select_related("source_document")
        .order_by("-effective_date", "-updated_at")
        .first()
    )


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def normalized_competitors(profile: CompanyProfileSnapshot | None) -> list[str]:
    if not profile or not isinstance(profile.competitors, list):
        return []
    values = []
    seen = set()
    for item in profile.competitors:
        label = clean_label(str(item))
        if not label or label.lower() in GENERIC_COMPETITOR_TERMS:
            continue
        key = normalize_key(label)
        if key in seen:
            continue
        seen.add(key)
        values.append(label)
    return values[:12]


def clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip(" .;:-")


def normalize_key(value: str) -> str:
    return slugify(value).replace("-", "")


def match_company(peer_name: str) -> Company | None:
    key = normalize_key(peer_name)
    for company in Company.objects.filter(is_active=True):
        names = [company.name, company.slug, *(company.aliases if isinstance(company.aliases, list) else [])]
        if any(normalize_key(str(name)) == key for name in names):
            return company
    return None


def relationship_type_for(name: str, peer_company: Company | None) -> str:
    lowered = name.lower()
    if any(term in lowered for term in ("platform", "wallet", "network", "cloud")):
        return CompetitiveRelationshipType.PLATFORM
    if any(term in lowered for term in ("substitute", "alternative")):
        return CompetitiveRelationshipType.SUBSTITUTE
    if peer_company is not None:
        return CompetitiveRelationshipType.DIRECT
    return CompetitiveRelationshipType.CATEGORY


def upsert_peer(
    snapshot: CompetitivePositionSnapshot,
    *,
    peer_name: str,
    peer_company: Company | None,
    relationship_type: str,
    scope: str,
    geography: str,
    products: list,
    customers: list,
    source: SourceDocument | None,
    evidence: str,
    confidence: str,
) -> dict[str, int]:
    peer, created = CompetitivePeer.objects.update_or_create(
        snapshot=snapshot,
        peer_name=peer_name,
        relationship_type=relationship_type,
        scope=scope,
        defaults={
            "peer_company": peer_company,
            "geography": geography,
            "product_overlap": [str(item) for item in products[:6]],
            "customer_overlap": [str(item) for item in customers[:6]],
            "evidence_text": evidence,
            "is_in_universe": peer_company is not None,
            "confidence_score": confidence,
        },
    )
    return {"created": 1 if created else 0, "updated": 0 if created else 1, "peer": peer}


def build_dimensions(
    snapshot: CompetitivePositionSnapshot,
    peer: CompetitivePeer,
    source: SourceDocument | None,
    products: list,
    customer_groups: list,
    geographies: list,
) -> list[dict[str, int]]:
    product_text = ", ".join(str(item) for item in products[:4]) or "company offerings disclosed in Company 360"
    customer_text = ", ".join(str(item) for item in customer_groups[:4]) or "customer groups disclosed in Company 360"
    geography_text = ", ".join(str(item) for item in geographies[:4]) or snapshot.company.country or "reported markets"
    rows = [
        (
            CompetitiveDimensionType.PRODUCT_OVERLAP,
            "Product and service overlap",
            f"{peer.peer_name} is compared against {snapshot.company.name} across {product_text}.",
        ),
        (
            CompetitiveDimensionType.CUSTOMER_OVERLAP,
            "Customer overlap",
            f"Comparison uses disclosed customer groups: {customer_text}.",
        ),
        (
            CompetitiveDimensionType.GEOGRAPHIC_OVERLAP,
            "Geographic overlap",
            f"Comparison is scoped to {geography_text}.",
        ),
        (
            CompetitiveDimensionType.SCALE_COMPARISON,
            "Scale context",
            "Scale comparison is limited to configured peer context until a reviewed market-share methodology is available.",
        ),
        (
            CompetitiveDimensionType.MOAT_EVIDENCE,
            "Potential moat evidence",
            "Durability evidence should be reviewed from switching costs, network effects, regulation, distribution, cost advantage, brand, or installed-base disclosures.",
        ),
        (
            CompetitiveDimensionType.OPPOSING_EVIDENCE,
            "Opposing evidence",
            "Competitive pressure remains an opposing-evidence category and is not treated as proof of moat erosion without reviewed outcomes.",
        ),
    ]
    counters = []
    for dimension_type, label, description in rows:
        _dimension, created = CompetitiveDimension.objects.update_or_create(
            snapshot=snapshot,
            peer=peer,
            dimension_type=dimension_type,
            label=label,
            defaults={
                "description": description,
                "evidence_text": peer.evidence_text,
                "source_document": source,
                "confidence_score": peer.confidence_score,
            },
        )
        counters.append({"created": 1 if created else 0, "updated": 0 if created else 1})
    return counters


def competitive_summary(company: Company, competitors: list[str], sector_peers: list[Company], products: list, geographies: list) -> str:
    competitor_text = ", ".join(competitors[:4]) if competitors else "reviewed same-sector peers"
    product_text = ", ".join(str(item) for item in products[:3]) if products else "reported offerings"
    geography_text = ", ".join(str(item) for item in geographies[:3]) if geographies else company.country or "reported markets"
    return (
        f"{company.name}'s competitive position baseline compares {product_text} in {geography_text} "
        f"against {competitor_text}. The view separates descriptive peer context from causation or outcome claims."
    )


def add_counts(total: dict[str, int], row: dict[str, int]) -> None:
    total["created"] += row.get("created", 0)
    total["updated"] += row.get("updated", 0)

from __future__ import annotations

from datetime import date
import re

from apps.companies.models import (
    Company,
    CompanyProfileSnapshot,
    CompanyProfileStatus,
    GeographicExpansionMarket,
    GeographicExpansionSnapshot,
    GeographicExpansionStatus,
)
from apps.curation.models import BusinessEvent
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_fallbacks import PROFILE_FALLBACKS


EXPANSION_EVENT_TYPES = {"GEOGRAPHIC_EXPANSION", "REGULATORY_RESPONSE"}
GENERIC_GEOGRAPHIES = {"global", "worldwide", "international", "international markets", "reported markets"}


def build_geographic_expansion(company: Company) -> dict[str, int]:
    profile = latest_profile(company)
    source = profile.source_document if profile else latest_source(company)
    effective_date = profile.effective_date if profile else date.today()
    markets = market_specs(company, profile, source)
    snapshot, created = GeographicExpansionSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": expansion_summary(company, markets),
            "methodology": (
                "Baseline generated from reviewed Company 360 geographies and source-backed expansion or regulatory events. "
                "Revenue contribution, local partnerships, barriers, and outcomes remain unavailable unless explicitly disclosed."
            ),
            "confidence_score": "0.820" if markets else "0.600",
        },
    )
    counters = {"snapshots_created": 1 if created else 0, "snapshots_updated": 0 if created else 1, "markets_created": 0, "markets_updated": 0}
    keep_ids = set()
    for spec in markets:
        market, market_created = GeographicExpansionMarket.objects.update_or_create(
            snapshot=snapshot,
            geography=spec["geography"][:255],
            market_type=spec["market_type"],
            defaults={
                "current_status": spec["current_status"],
                "entry_date": spec["entry_date"],
                "exit_date": spec["exit_date"],
                "local_partnerships": spec["local_partnerships"],
                "regulatory_barriers": spec["regulatory_barriers"],
                "revenue_contribution": None,
                "revenue_currency": "",
                "revenue_period": "",
                "expansion_rationale": spec["expansion_rationale"],
                "outcome_summary": spec["outcome_summary"],
                "evidence_text": spec["evidence_text"],
                "source_document": spec["source_document"],
                "linked_event": spec["linked_event"],
                "confidence_score": spec["confidence_score"],
                "review_status": "REVIEWED",
            },
        )
        keep_ids.add(market.id)
        counters["markets_created" if market_created else "markets_updated"] += 1
    if keep_ids:
        snapshot.markets.exclude(id__in=keep_ids).delete()
    return counters


def geographic_expansion_quality_issues(company: Company) -> list[str]:
    snapshot = (
        GeographicExpansionSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("markets")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed geographic expansion snapshot"]
    issues = []
    if not snapshot.markets.exists():
        issues.append("no reviewed geographic markets")
    if not snapshot.markets.exclude(revenue_contribution__isnull=True).exists():
        issues.append("regional revenue contribution unavailable")
    if not snapshot.markets.exclude(regulatory_barriers=[]).exists():
        issues.append("regulatory barriers unavailable")
    return issues


def latest_profile(company: Company) -> CompanyProfileSnapshot | None:
    return (
        CompanyProfileSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .select_related("source_document")
        .order_by("-effective_date", "-updated_at")
        .first()
    )


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def market_specs(company: Company, profile: CompanyProfileSnapshot | None, source: SourceDocument | None) -> list[dict[str, object]]:
    rows = []
    for geography in profile_geographies(company, profile):
        rows.append(
            spec(
                geography=geography,
                source=source,
                event=None,
                status=GeographicExpansionStatus.ACTIVE,
                rationale=f"{company.name} discloses {geography} as a reviewed operating geography.",
                outcome="Current operating presence is reviewed; market-specific outcome is not separately disclosed.",
                confidence="0.820",
            )
        )
    for event in expansion_events(company):
        geography = event_geography(event) or company.country or "Reported market"
        rows.append(
            spec(
                geography=geography,
                source=event.source_document or source,
                event=event,
                status=GeographicExpansionStatus.EXPANDING,
                rationale=event.actual_change or event.source_claim or event.decision_theme,
                outcome=event.outcome or "Expansion outcome requires later reviewed evidence.",
                confidence="0.760",
            )
        )
    return unique_specs(rows)


def profile_geographies(company: Company, profile: CompanyProfileSnapshot | None) -> list[str]:
    profile_rows = profile.geographies if profile and isinstance(profile.geographies, list) else []
    fallback_rows = PROFILE_FALLBACKS.get(company.slug, {}).get("geographies", [])
    rows = profile_rows if profile_rows else fallback_rows
    if not rows and company.country:
        rows = [company.country]
    return [clean_label(str(row)) for row in rows if clean_label(str(row))]


def expansion_events(company: Company) -> list[BusinessEvent]:
    return list(
        BusinessEvent.objects.filter(company=company, event_type__in=EXPANSION_EVENT_TYPES)
        .select_related("source_document")
        .exclude(actual_change="")
        .order_by("-event_date", "-created_at")[:12]
    )


def event_geography(event: BusinessEvent) -> str:
    text = " ".join([event.actual_change or "", event.source_claim or "", event.evidence_text or ""])
    for pattern in (r"\bin ([A-Z][A-Za-z& .-]{2,40})", r"\binto ([A-Z][A-Za-z& .-]{2,40})"):
        match = re.search(pattern, text)
        if match:
            return clean_label(match.group(1))
    return ""


def spec(
    *,
    geography: str,
    source: SourceDocument | None,
    event: BusinessEvent | None,
    status: str,
    rationale: str,
    outcome: str,
    confidence: str,
) -> dict[str, object]:
    return {
        "geography": geography,
        "market_type": market_type_for(geography),
        "current_status": status,
        "entry_date": event.event_date if event else None,
        "exit_date": None,
        "local_partnerships": [],
        "regulatory_barriers": [],
        "expansion_rationale": rationale,
        "outcome_summary": outcome,
        "evidence_text": event.evidence_text if event and event.evidence_text else f"Reviewed geography: {geography}.",
        "source_document": source,
        "linked_event": event,
        "confidence_score": confidence,
    }


def market_type_for(geography: str) -> str:
    lowered = geography.lower()
    if lowered in GENERIC_GEOGRAPHIES:
        return "GLOBAL_REGION"
    if any(term in lowered for term in ("europe", "asia", "latin america", "middle east", "africa", "international")):
        return "REGION"
    return "COUNTRY_OR_MARKET"


def expansion_summary(company: Company, markets: list[dict[str, object]]) -> str:
    if not markets:
        return f"No reviewed geographic expansion evidence is available for {company.name}."
    labels = ", ".join(str(row["geography"]) for row in markets[:5])
    return f"{company.name} has reviewed geographic presence or expansion evidence for {labels}."


def unique_specs(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen = set()
    unique = []
    for row in rows:
        key = (str(row["geography"]).lower(), row["market_type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip(" .;:-")

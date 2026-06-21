from __future__ import annotations

from datetime import date
import re

from apps.companies.models import (
    Company,
    CompanyProfileSnapshot,
    CompanyProfileStatus,
    OwnershipHolderType,
    OwnershipInsiderSnapshot,
    OwnershipPosition,
    OwnershipPositionType,
)
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_fallbacks import PROFILE_FALLBACKS


def build_ownership_insider_activity(company: Company) -> dict[str, int]:
    profile = latest_profile(company)
    source = profile.source_document if profile else latest_source(company)
    effective_date = profile.effective_date if profile else date.today()
    holders = holder_specs(company, profile, source)
    snapshot, created = OwnershipInsiderSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": ownership_summary(company, holders),
            "methodology": (
                "Baseline generated from reviewed Company 360 leadership context and official source documents. "
                "Economic ownership, voting power, institutional positions, Form 4 transactions, and 10b5-1 plans "
                "are not inferred when the source does not disclose them."
            ),
            "confidence_score": "0.780" if holders else "0.600",
        },
    )
    counters = {
        "snapshots_created": 1 if created else 0,
        "snapshots_updated": 0 if created else 1,
        "positions_created": 0,
        "positions_updated": 0,
    }
    keep_ids = set()
    for spec in holders:
        position, position_created = OwnershipPosition.objects.update_or_create(
            snapshot=snapshot,
            holder_name=spec["holder_name"],
            holder_type=spec["holder_type"],
            position_type=OwnershipPositionType.INSIDER_CONTEXT,
            defaults={
                "economic_ownership_pct": None,
                "voting_power_pct": None,
                "shares_owned": None,
                "share_class": "",
                "filing_date": None,
                "report_period": "",
                "disclosure_form": "Company 360",
                "evidence_text": spec["evidence_text"],
                "source_document": spec["source_document"],
                "confidence_score": spec["confidence_score"],
                "review_status": "REVIEWED",
            },
        )
        keep_ids.add(position.id)
        counters["positions_created" if position_created else "positions_updated"] += 1
    if keep_ids:
        snapshot.positions.exclude(id__in=keep_ids).delete()
    return counters


def ownership_insider_quality_issues(company: Company) -> list[str]:
    snapshot = (
        OwnershipInsiderSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("positions", "insider_transactions")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed ownership and insider snapshot"]
    issues = []
    if not snapshot.positions.exists():
        issues.append("no reviewed insider context or ownership positions")
    if not snapshot.positions.exclude(economic_ownership_pct__isnull=True).exists():
        issues.append("ownership percentages unavailable")
    if not snapshot.positions.exclude(voting_power_pct__isnull=True).exists():
        issues.append("voting control unavailable")
    if not snapshot.insider_transactions.exists():
        issues.append("insider transactions unavailable")
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


def holder_specs(company: Company, profile: CompanyProfileSnapshot | None, source: SourceDocument | None) -> list[dict[str, object]]:
    leaders = profile.leadership if profile and isinstance(profile.leadership, list) else []
    if not leaders:
        leaders = PROFILE_FALLBACKS.get(company.slug, {}).get("leadership", [])
    rows = []
    for raw in leaders:
        name, role = parse_leader(raw)
        if not name:
            continue
        rows.append({
            "holder_name": name[:255],
            "holder_type": OwnershipHolderType.EXECUTIVE,
            "evidence_text": (
                f"Reviewed leadership context for {name}"
                + (f" ({role})" if role else "")
                + "; ownership percentage and transaction activity are unavailable until a proxy, Form 4, 13D, or 13G source is reviewed."
            ),
            "source_document": source,
            "confidence_score": "0.780",
        })
    return unique_holders(rows)


def parse_leader(raw: object) -> tuple[str, str]:
    if isinstance(raw, dict):
        return clean_label(str(raw.get("name") or raw.get("person") or "")), clean_label(str(raw.get("role") or raw.get("title") or ""))
    value = clean_label(str(raw))
    if not value:
        return "", ""
    parts = re.split(r"\s+-\s+|\s+,\s+", value, maxsplit=1)
    return clean_label(parts[0]), clean_label(parts[1]) if len(parts) > 1 else ""


def ownership_summary(company: Company, holders: list[dict[str, object]]) -> str:
    if not holders:
        return f"No reviewed ownership or insider context is available for {company.name}."
    labels = ", ".join(str(row["holder_name"]) for row in holders[:5])
    return f"{company.name} has reviewed insider context for {labels}; ownership percentages and transactions require dedicated filings."


def unique_holders(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen = set()
    unique = []
    for row in rows:
        key = (str(row["holder_name"]).lower(), row["holder_type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip(" .;:-")

from __future__ import annotations

import re

from apps.companies.models import BusinessModelComponentType, BusinessModelSnapshot, CompanyProfileSnapshot


PROFILE_SNAPSHOT_LIMIT = 20


PROFILE_LIST_FIELDS = (
    "subsidiaries",
    "brands",
    "segments",
    "products",
    "customer_groups",
    "revenue_sources",
    "geographies",
    "operating_regions",
    "revenue_geographies",
    "leadership",
    "competitors",
    "strategic_priorities",
)
BLOCKED_LABELS = {"the", "our", "company", "ltd", "resource", "industries"}
BLOCKED_SUMMARY_MARKERS = (
    "documents incorporated by reference",
    "securities registered pursuant",
    "table of contents form 10-k",
    "aggregate market value",
    "☐ yes",
    "☒ no",
)





def profile_snapshot_has_content(snapshot: CompanyProfileSnapshot) -> bool:
    return bool(snapshot.summary or snapshot.business_model or any(getattr(snapshot, field) for field in PROFILE_LIST_FIELDS))


def reviewed_profile_snapshot_window(company, *, as_of=None) -> list[CompanyProfileSnapshot]:
    queryset = CompanyProfileSnapshot.objects.filter(
        company=company,
        status__in=["PUBLISHED", "REVIEWED"],
    ).order_by("-effective_date", "-updated_at")
    if as_of is not None:
        queryset = queryset.filter(effective_date__lte=as_of)
    snapshots = []
    source_types = set()
    for snapshot in queryset.select_related("source_document"):
        if not profile_snapshot_has_content(snapshot):
            continue
        source_type = snapshot.source_document.source_api if snapshot.source_document_id else "MANUAL"
        if source_type in source_types:
            continue
        snapshots.append(snapshot)
        source_types.add(source_type)
        if len(snapshots) == PROFILE_SNAPSHOT_LIMIT:
            break
    return snapshots


def company_profile_quality_issues(company) -> list[str]:
    profiles = reviewed_profile_snapshot_window(company)
    if not profiles:
        return ["no reviewed Company 360 profile"]

    business_model = (
        BusinessModelSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .prefetch_related("components", "relationships")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    values = {
        "summary": next((row.summary for row in profiles if row.summary), company.description),
        "business_model": business_model.summary if business_model else next((row.business_model for row in profiles if row.business_model), ""),
        **{
            field: next((getattr(row, field) for row in profiles if getattr(row, field)), [])
            for field in PROFILE_LIST_FIELDS
        },
    }

    issues = [f"{field} unavailable" for field, value in values.items() if not value]
    summary = str(values["business_model"]).strip()
    if summary and len(summary) < 80:
        issues.append("business model summary is too short")
    if any(marker in summary.lower() for marker in BLOCKED_SUMMARY_MARKERS):
        issues.append("business model summary contains filing boilerplate")

    for field in PROFILE_LIST_FIELDS:
        for item in values[field]:
            label = str(item).strip()
            if label.lower() in BLOCKED_LABELS:
                issues.append(f"{field} contains parser fragment: {label}")
            if re.search(r"\b([A-Za-z][A-Za-z0-9&+.-]*)\s+\1\b", label, re.IGNORECASE):
                issues.append(f"{field} contains duplicated words: {label}")

    if business_model is None:
        issues.append("reviewed Business Model Map unavailable")
    else:
        expected_types = {choice for choice, _label in BusinessModelComponentType.choices}
        present_types = set(business_model.components.values_list("component_type", flat=True))
        missing_types = sorted(expected_types - present_types)
        if missing_types:
            issues.append(f"Business Model Map missing component types: {', '.join(missing_types)}")
        if not business_model.relationships.exists():
            issues.append("Business Model Map has no relationships")
    return list(dict.fromkeys(issues))

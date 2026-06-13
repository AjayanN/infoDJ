from __future__ import annotations

from datetime import date

import requests
from bs4 import BeautifulSoup

from apps.companies.models import (
    BusinessModelComponent,
    BusinessModelComponentType,
    BusinessModelRelationship,
    BusinessModelSnapshot,
    CompanyProfileStatus,
)
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_client import clean_text, robots_allows
from apps.ingestion.services.company_profile_fallbacks import (
    BUSINESS_MODEL_FALLBACKS,
    PROFILE_FALLBACKS,
    SECTOR_BUSINESS_MODEL_FALLBACKS,
)
from apps.ingestion.services.url_utils import url_hash
from apps.ingestion.services.wikidata_client import DEFAULT_USER_AGENT


def build_business_model_from_profile(company) -> BusinessModelSnapshot:
    profiles = list(
        company.profile_snapshots.filter(status__in=["PUBLISHED", "REVIEWED"])
        .select_related("source_document")
        .order_by("-effective_date", "-updated_at")
    )
    if not profiles:
        raise ValueError(f"{company.name} has no reviewed Company 360 profile")
    values = aggregate_profile_values(profiles)
    profile = profiles[0]
    profile_fallbacks = PROFILE_FALLBACKS.get(company.slug, {})
    for field in ("business_model", "products", "customer_groups", "revenue_sources", "geographies"):
        if profile_fallbacks.get(field):
            values[field] = profile_fallbacks[field]
    component_values = {
        "PAYER": values["customer_groups"],
        "USER": values["customer_groups"],
        "OFFERING": values["products"],
        "REVENUE": values["revenue_sources"],
        "GEOGRAPHY": values["geographies"],
    }
    reviewed_fallbacks = BUSINESS_MODEL_FALLBACKS.get(company.slug, {})
    sector_fallbacks = SECTOR_BUSINESS_MODEL_FALLBACKS.get(company.industry, {})
    for component_type, fallback_values in reviewed_fallbacks.items():
        component_values[component_type] = fallback_values
    for component_type, fallback_values in sector_fallbacks.items():
        component_values.setdefault(component_type, fallback_values)

    snapshot, _created = BusinessModelSnapshot.objects.update_or_create(
        company=company,
        effective_date=profile.effective_date,
        source_document=profile.source_document,
        defaults={
            "status": CompanyProfileStatus.REVIEWED,
            "summary": values["business_model"],
            "confidence_score": min(profile.confidence_score, 0.650),
        },
    )
    snapshot.components.all().delete()

    components = {
        component_type: create_components(
            snapshot,
            component_type,
            component_values.get(component_type, []),
            profile.evidence_text,
            inferred=component_type in sector_fallbacks and component_type not in reviewed_fallbacks,
        )
        for component_type, _label in BusinessModelComponentType.choices
    }

    for payer in components["PAYER"]:
        for revenue in components["REVENUE"]:
            create_relationship(snapshot, payer, revenue, "PAYS_THROUGH", "Reviewed profile categories connect payer groups to revenue mechanisms.")
    for user in components["USER"]:
        for offering in components["OFFERING"]:
            create_relationship(snapshot, user, offering, "USES", "Profile categories imply use; analyst review required.")
    for offering in components["OFFERING"]:
        for revenue in components["REVENUE"]:
            create_relationship(snapshot, offering, revenue, "MONETIZED_BY", "Profile categories imply monetization; analyst review required.")
        for channel in components["CHANNEL"]:
            create_relationship(snapshot, offering, channel, "DELIVERED_THROUGH", "Reviewed operating context connects offerings to distribution channels.")
    return snapshot


def aggregate_profile_values(profiles) -> dict[str, object]:
    fields = ("business_model", "products", "customer_groups", "revenue_sources", "geographies")
    values = {}
    for field in fields:
        values[field] = next((getattr(profile, field) for profile in profiles if getattr(profile, field)), "" if field == "business_model" else [])
    return values


def create_components(snapshot, component_type: str, values, evidence_text: str, *, inferred: bool):
    rows = []
    for value in values or []:
        name = value.get("name") if isinstance(value, dict) else value
        description = value.get("description", "") if isinstance(value, dict) else ""
        scope = value.get("scope", "") if isinstance(value, dict) else ""
        if not name:
            continue
        rows.append(
            BusinessModelComponent.objects.create(
                snapshot=snapshot,
                component_type=component_type,
                name=str(name),
                description=str(description),
                scope=str(scope),
                evidence_text=evidence_text,
                is_inferred=inferred,
                confidence_score="0.600" if inferred else snapshot.confidence_score,
            )
        )
    return rows


def create_relationship(snapshot, from_component, to_component, relationship_type: str, description: str):
    return BusinessModelRelationship.objects.create(
        snapshot=snapshot,
        from_component=from_component,
        to_component=to_component,
        relationship_type=relationship_type,
        description=description,
        evidence_text="",
        is_inferred=True,
        confidence_score="0.450",
    )


def collect_business_model_page(
    company,
    *,
    url: str,
    effective_date: date,
    session: requests.Session | None = None,
) -> BusinessModelSnapshot:
    session = session or requests.Session()
    session.headers["User-Agent"] = DEFAULT_USER_AGENT
    if not robots_allows(url, session=session):
        raise PermissionError(f"robots.txt does not allow business-model collection for {url}")
    response = session.get(url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    description = soup.select_one('meta[name="description"]') or soup.select_one('meta[property="og:description"]')
    summary = clean_text(description.get("content")) if description else ""
    title = clean_text(soup.title.string if soup.title else "") or f"{company.name} business-model source"
    source, _created = SourceDocument.objects.update_or_create(
        url_hash=url_hash(response.url or url),
        defaults={
            "company": company,
            "source_api": "ARCHIVED_WEB" if "archive.org" in (response.url or url) else "OFFICIAL_WEBSITE",
            "url": response.url or url,
            "canonical_url": response.url or url,
            "title": title,
            "publisher": company.name,
            "snippet": summary,
            "language": "en",
            "status": "APPROVED",
        },
    )
    snapshot, _created = BusinessModelSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        source_document=source,
        defaults={
            "status": CompanyProfileStatus.DRAFT,
            "summary": summary,
            "confidence_score": "0.500",
        },
    )
    return snapshot

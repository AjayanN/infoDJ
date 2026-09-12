from __future__ import annotations

from datetime import date

from apps.companies.models import (
    Company,
    CompanyProfileSnapshot,
    CompanyProfileStatus,
    ProductCatalogSnapshot,
    ProductChange,
    ProductChangeType,
    ProductOffering,
    ProductOfferingType,
)
from apps.curation.models import BusinessEvent
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_fallbacks import PROFILE_FALLBACKS


PRODUCT_EVENT_TYPES = {"PRODUCT_EXPANSION", "PRICING_CHANGE", "REVENUE_MODEL_EXPANSION", "BRAND_REPOSITIONING"}


def build_product_pricing_history(company: Company) -> dict[str, int]:
    profile = latest_profile(company)
    effective_date = profile.effective_date if profile else date.today()
    source = profile.source_document if profile else latest_source(company)
    fallback = PROFILE_FALLBACKS.get(company.slug, {})
    products = profile.products if profile and isinstance(profile.products, list) and profile.products else list(fallback.get("products", []))
    brands = profile.brands if profile and isinstance(profile.brands, list) and profile.brands else list(fallback.get("brands", []))
    geographies = profile.geographies if profile and isinstance(profile.geographies, list) else ([company.country] if company.country else [])
    customers = profile.customer_groups if profile and isinstance(profile.customer_groups, list) else []
    snapshot, created = ProductCatalogSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": catalog_summary(company, products, brands),
            "chronology_note": "Announcement dates and effective dates are stored separately. Current baseline offerings come from reviewed Company 360 profile data; unavailable list prices are not estimated.",
            "confidence_score": "0.850" if products else "0.650",
        },
    )
    counters = {"snapshots_created": 1 if created else 0, "snapshots_updated": 0 if created else 1, "offerings_created": 0, "offerings_updated": 0, "changes_created": 0, "changes_updated": 0}
    for brand in brands[:8]:
        result = upsert_offering(snapshot, ProductOfferingType.FAMILY, str(brand), source, geographies, customers)
        counters["offerings_created"] += result["created"]
        counters["offerings_updated"] += result["updated"]
    for product in products[:16]:
        result = upsert_offering(snapshot, offering_type_for(str(product)), str(product), source, geographies, customers)
        counters["offerings_created"] += result["created"]
        counters["offerings_updated"] += result["updated"]
    offerings = list(snapshot.offerings.all())
    for event in product_events(company):
        offering = matching_offering(offerings, event)
        change_type = change_type_for_event(event)
        change, change_created = ProductChange.objects.update_or_create(
            snapshot=snapshot,
            title=(event.actual_change or event.source_claim or event.decision or event.get_event_type_display())[:512],
            change_type=change_type,
            announcement_date=event.event_date,
            defaults={
                "offering": offering,
                "effective_date": event.event_date,
                "before_state": event.before_state,
                "after_state": event.after_state,
                "evidence_text": event.evidence_text or event.source_claim,
                "source_document": event.source_document,
                "linked_event": event,
                "confidence_score": event.confidence_score,
            },
        )
        counters["changes_created" if change_created else "changes_updated"] += 1
    if not snapshot.changes.exists():
        for offering in offerings[:8]:
            change, change_created = ProductChange.objects.update_or_create(
                snapshot=snapshot,
                offering=offering,
                title=f"{offering.name} listed in reviewed product catalog",
                change_type=ProductChangeType.UPDATE,
                announcement_date=effective_date,
                defaults={
                    "effective_date": effective_date,
                    "before_state": "",
                    "after_state": offering.description or offering.name,
                    "evidence_text": offering.evidence_text,
                    "source_document": source,
                    "confidence_score": offering.confidence_score,
                },
            )
            counters["changes_created" if change_created else "changes_updated"] += 1
    return counters


def product_pricing_quality_issues(company: Company) -> list[str]:
    snapshot = (
        ProductCatalogSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .prefetch_related("offerings", "changes")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed product catalog snapshot"]
    issues = []
    if not snapshot.offerings.exists():
        issues.append("no reviewed product offerings")
    if not snapshot.changes.exists():
        issues.append("no product timeline changes")
    if not snapshot.chronology_note:
        issues.append("chronology note unavailable")
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


def upsert_offering(snapshot, offering_type, name, source, geographies, customers) -> dict[str, int]:
    offering, created = ProductOffering.objects.update_or_create(
        snapshot=snapshot,
        offering_type=offering_type,
        name=name.strip()[:255],
        defaults={
            "description": f"{name.strip()} is listed in the reviewed Company 360 product catalog.",
            "availability": "Current reviewed catalog",
            "geography": ", ".join(str(item) for item in geographies[:3]),
            "customer_segment": ", ".join(str(item) for item in customers[:3]),
            "evidence_text": f"Reviewed profile lists {name.strip()} as a product, plan, service, brand, feature, or offering.",
            "confidence_score": "0.850",
        },
    )
    return {"created": 1 if created else 0, "updated": 0 if created else 1, "offering": offering}


def offering_type_for(name: str) -> str:
    lowered = name.lower()
    if any(term in lowered for term in ("plan", "membership", "subscription", "tier")):
        return ProductOfferingType.PLAN
    if any(term in lowered for term in ("service", "services", "software", "cloud", "advertising")):
        return ProductOfferingType.PRODUCT
    if any(term in lowered for term in ("feature", "connectivity", "analytics")):
        return ProductOfferingType.FEATURE
    return ProductOfferingType.PRODUCT


def product_events(company: Company) -> list[BusinessEvent]:
    return list(
        BusinessEvent.objects.filter(company=company, event_type__in=PRODUCT_EVENT_TYPES)
        .exclude(actual_change="")
        .select_related("source_document")
        .order_by("-event_date", "-created_at")[:40]
    )


def matching_offering(offerings: list[ProductOffering], event: BusinessEvent) -> ProductOffering | None:
    text = " ".join([event.actual_change or "", event.source_claim or "", event.decision or ""]).lower()
    return next((offering for offering in offerings if offering.name.lower() in text), offerings[0] if offerings else None)


def change_type_for_event(event: BusinessEvent) -> str:
    if event.event_type == "PRICING_CHANGE":
        return ProductChangeType.PRICE_CHANGE
    if event.event_type == "PRODUCT_EXPANSION":
        return ProductChangeType.LAUNCH
    if event.event_type == "BRAND_REPOSITIONING":
        return ProductChangeType.PACKAGING_CHANGE
    return ProductChangeType.UPDATE


def catalog_summary(company: Company, products: list, brands: list) -> str:
    product_text = ", ".join(str(item) for item in products[:5]) if products else "reviewed products are unavailable"
    brand_text = ", ".join(str(item) for item in brands[:3]) if brands else "reviewed brands unavailable"
    return f"{company.name}'s reviewed product catalog covers {product_text}. Brand or family context: {brand_text}."


def reviewed_claim_pricing_rows(company: Company) -> list[dict]:
    """Expose reviewed historical price terms without replacing legacy catalog reads."""
    from apps.history.models import HistoricalClaim, ReviewState
    from apps.history.services.projections import projection_rows
    claims = HistoricalClaim.objects.filter(subject__company=company, track="pricing", review_state=ReviewState.REVIEWED).order_by("date_min", "recorded_at")
    return [row for row in projection_rows(claims) if row["projection"] == "price"]

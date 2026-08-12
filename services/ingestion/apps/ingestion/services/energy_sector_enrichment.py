from __future__ import annotations

from datetime import date
import re

from apps.companies.models import (
    Company,
    CompanyProfileStatus,
    ProductCatalogSnapshot,
    ProductOffering,
    ProductOfferingType,
)
from apps.curation.models import BusinessEvent, EventType, ReviewStatus
from apps.ingestion.models import ArticleExtraction


PRIMARY_SOURCE_APIS = {"OFFICIAL_WEBSITE", "SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"}
ENERGY_LOCATIONS = {
    "Guyana": "Guyana",
    "Permian": "Permian Basin",
    "Brazil": "Brazil",
    "LNG": "LNG",
}
ENERGY_PRODUCT_FAMILIES = {
    "performance chemicals": "Performance chemicals",
    "performance lubricants": "Performance lubricants",
    "lower-emission fuels": "Lower-emission fuels",
}


def enrich_energy_disclosures(company: Company, *, limit: int = 80) -> dict[str, int]:
    if company.industry != "Energy":
        return {"events_created": 0, "events_updated": 0, "offerings_created": 0, "offerings_updated": 0}

    counters = {"events_created": 0, "events_updated": 0, "offerings_created": 0, "offerings_updated": 0}
    seen_locations = set()
    seen_product_families = set()
    extractions = (
        ArticleExtraction.objects.filter(
            source_document__company=company,
            source_document__source_api__in=PRIMARY_SOURCE_APIS,
            extraction_status="SUCCEEDED",
        )
        .select_related("source_document")
        .order_by("-source_document__published_date", "-source_document__updated_at")[:limit]
    )
    for extraction in extractions:
        evidence = extraction.clean_text or ""
        for marker, geography in ENERGY_LOCATIONS.items():
            if marker in seen_locations or not re.search(rf"\b{re.escape(marker)}\b", evidence, re.IGNORECASE):
                continue
            event, created = BusinessEvent.objects.update_or_create(
                company=company,
                source_document=extraction.source_document,
                event_type=EventType.GEOGRAPHIC_EXPANSION,
                decision_theme=f"ENERGY_ASSET_{marker.upper().replace(' ', '_')}",
                defaults={
                    "article_extraction": extraction,
                    "event_date": source_date(extraction),
                    "lifecycle_stage": "",
                    "decision": f"Advance the disclosed {geography} energy asset or market position.",
                    "source_claim": excerpt(evidence, marker),
                    "actual_change": f"{company.name} identifies {geography} in its disclosed Energy growth portfolio.",
                    "outcome": "Later operating outcome requires a separate source-backed disclosure.",
                    "evidence_text": excerpt(evidence, marker),
                    "confidence_score": "0.850",
                    "review_status": ReviewStatus.APPROVED,
                },
            )
            seen_locations.add(marker)
            counters["events_created" if created else "events_updated"] += 1
        counters = merge(counters, upsert_product_families(company, extraction, evidence, seen_product_families))
    return counters


def upsert_product_families(
    company: Company, extraction: ArticleExtraction, evidence: str, seen_product_families: set[str]
) -> dict[str, int]:
    matches = [
        label
        for marker, label in ENERGY_PRODUCT_FAMILIES.items()
        if label not in seen_product_families and re.search(rf"\b{re.escape(marker)}\b", evidence, re.IGNORECASE)
    ]
    if not matches:
        return {"offerings_created": 0, "offerings_updated": 0}
    snapshot, _ = ProductCatalogSnapshot.objects.update_or_create(
        company=company,
        effective_date=source_date(extraction),
        defaults={
            "source_document": extraction.source_document,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": "First-party Energy product families disclosed in a company filing or official source.",
            "chronology_note": "Product-family availability is sourced; prices are shown only when an explicit official list price is available.",
            "confidence_score": "0.850",
        },
    )
    created = updated = 0
    for label in matches:
        seen_product_families.add(label)
        _, was_created = ProductOffering.objects.update_or_create(
            snapshot=snapshot,
            offering_type=ProductOfferingType.FAMILY,
            name=label,
            defaults={
                "description": "Source-disclosed Energy product family.",
                "availability": "As disclosed by the source.",
                "evidence_text": excerpt(evidence, label),
                "confidence_score": "0.850",
            },
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"offerings_created": created, "offerings_updated": updated}


def source_date(extraction: ArticleExtraction) -> date:
    published = extraction.source_document.published_date
    return published.date() if published else date.today()


def excerpt(text: str, term: str) -> str:
    match = re.search(re.escape(term), text, re.IGNORECASE)
    if match is None:
        return text[:800]
    return re.sub(r"\s+", " ", text[max(0, match.start() - 180): match.end() + 420]).strip()


def merge(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return {key: left.get(key, 0) + right.get(key, 0) for key in set(left) | set(right)}

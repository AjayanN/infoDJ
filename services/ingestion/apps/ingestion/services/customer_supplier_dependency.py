from __future__ import annotations

from datetime import date

from django.utils.text import slugify

from apps.companies.models import (
    BusinessModelComponent,
    BusinessModelComponentType,
    BusinessModelSnapshot,
    Company,
    CompanyProfileSnapshot,
    CompanyProfileStatus,
    CustomerSupplierDependency,
    CustomerSupplierDependencySnapshot,
    DependencyDisclosureConfidence,
    DependencyMaterialityBand,
    DependencyType,
)
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_fallbacks import (
    BUSINESS_MODEL_FALLBACKS,
    PROFILE_FALLBACKS,
    SECTOR_BUSINESS_MODEL_FALLBACKS,
)


def build_customer_supplier_dependency(company: Company) -> dict[str, int]:
    profile = latest_profile(company)
    business_model = latest_business_model(company)
    effective_date = profile.effective_date if profile else (business_model.effective_date if business_model else date.today())
    source = profile.source_document if profile else (business_model.source_document if business_model else latest_source(company))
    relationships = dependency_specs(company, profile, business_model)
    snapshot, created = CustomerSupplierDependencySnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": dependency_summary(company, relationships),
            "methodology": (
                "Baseline generated from reviewed Company 360 customer groups and reviewed business-model channel/partner components. "
                "Category-only dependencies are not treated as named counterparties, and absence of a disclosure is not treated as absence of dependency."
            ),
            "confidence_score": "0.820" if relationships else "0.600",
        },
    )
    counters = {"snapshots_created": 1 if created else 0, "snapshots_updated": 0 if created else 1, "dependencies_created": 0, "dependencies_updated": 0}
    keep_keys = set()
    for spec in relationships:
        dependency, dep_created = CustomerSupplierDependency.objects.update_or_create(
            snapshot=snapshot,
            dependency_type=spec["dependency_type"],
            counterparty_name=spec["counterparty_name"][:255],
            product_scope=spec["product_scope"][:255],
            defaults={
                "counterparty_company": match_company(spec["counterparty_name"]) if spec["is_named_counterparty"] else None,
                "is_named_counterparty": spec["is_named_counterparty"],
                "materiality_band": spec["materiality_band"],
                "disclosure_confidence": spec["disclosure_confidence"],
                "concentration_percent": None,
                "geography": spec["geography"][:255],
                "relationship_summary": spec["relationship_summary"],
                "risk_summary": spec["risk_summary"],
                "evidence_text": spec["evidence_text"],
                "source_document": spec["source_document"],
                "confidence_score": spec["confidence_score"],
            },
        )
        keep_keys.add(dependency.id)
        counters["dependencies_created" if dep_created else "dependencies_updated"] += 1
    if keep_keys:
        snapshot.dependencies.exclude(id__in=keep_keys).delete()
    return counters


def customer_supplier_dependency_quality_issues(company: Company) -> list[str]:
    snapshot = (
        CustomerSupplierDependencySnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .prefetch_related("dependencies")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed dependency snapshot"]
    issues = []
    if not snapshot.dependencies.exists():
        issues.append("no reviewed dependency relationships")
    if not snapshot.dependencies.filter(dependency_type=DependencyType.CUSTOMER_SEGMENT).exists():
        issues.append("customer dependency categories unavailable")
    if not snapshot.dependencies.filter(dependency_type__in=[DependencyType.SUPPLIER, DependencyType.DISTRIBUTOR, DependencyType.PLATFORM, DependencyType.PARTNER]).exists():
        issues.append("supplier or partner dependency categories unavailable")
    return issues


def latest_profile(company: Company) -> CompanyProfileSnapshot | None:
    return (
        CompanyProfileSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .select_related("source_document")
        .order_by("-effective_date", "-updated_at")
        .first()
    )


def latest_business_model(company: Company) -> BusinessModelSnapshot | None:
    return (
        BusinessModelSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .select_related("source_document")
        .prefetch_related("components")
        .order_by("-effective_date", "-updated_at")
        .first()
    )


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def dependency_specs(
    company: Company,
    profile: CompanyProfileSnapshot | None,
    business_model: BusinessModelSnapshot | None,
) -> list[dict[str, object]]:
    source = profile.source_document if profile else (business_model.source_document if business_model else latest_source(company))
    geographies = profile.geographies if profile and isinstance(profile.geographies, list) else ([company.country] if company.country else [])
    products = profile.products if profile and isinstance(profile.products, list) else []
    rows: list[dict[str, object]] = []
    customer_groups = profile_values(company, profile, "customer_groups")
    for customer in customer_groups[:8]:
        rows.append(spec(
            DependencyType.CUSTOMER_SEGMENT,
            customer,
            product_scope=", ".join(str(row) for row in products[:3]),
            geography=", ".join(str(row) for row in geographies[:3]),
            source=source,
            relationship=f"{company.name} discloses {customer} as a customer group or customer segment.",
            risk="Materiality, concentration percentage, and renewal exposure are not disclosed in the reviewed baseline.",
        ))
    components = business_model_components(company, business_model)
    for channel in components.get(BusinessModelComponentType.CHANNEL, [])[:6]:
        rows.append(spec(
            dependency_type_for_channel(channel),
            channel,
            product_scope="Distribution and access",
            geography=", ".join(str(row) for row in geographies[:3]),
            source=source,
            relationship=f"{channel} is part of the reviewed business-model channel or distribution structure.",
            risk="Dependency level is category-only unless a named counterparty and contract term are reviewed.",
        ))
    for partner in components.get(BusinessModelComponentType.PARTNER, [])[:6]:
        rows.append(spec(
            dependency_type_for_partner(partner),
            partner,
            product_scope="Supply, operations, or ecosystem support",
            geography=", ".join(str(row) for row in geographies[:3]),
            source=source,
            relationship=f"{partner} is part of the reviewed business-model partner structure.",
            risk="Named supplier/customer concentration is unavailable unless explicitly disclosed.",
        ))
    return unique_specs(rows)


def spec(
    dependency_type: str,
    counterparty_name: str,
    *,
    product_scope: str,
    geography: str,
    source: SourceDocument | None,
    relationship: str,
    risk: str,
) -> dict[str, object]:
    name = clean_label(str(counterparty_name))
    return {
        "dependency_type": dependency_type,
        "counterparty_name": name,
        "is_named_counterparty": False,
        "materiality_band": DependencyMaterialityBand.CONTEXT,
        "disclosure_confidence": DependencyDisclosureConfidence.CATEGORY_ONLY,
        "product_scope": product_scope,
        "geography": geography,
        "relationship_summary": relationship,
        "risk_summary": risk,
        "evidence_text": f"Reviewed dependency category: {name}.",
        "source_document": source,
        "confidence_score": "0.780",
    }


def profile_values(company: Company, profile: CompanyProfileSnapshot | None, field: str) -> list[str]:
    profile_rows = getattr(profile, field, []) if profile else []
    fallback_rows = PROFILE_FALLBACKS.get(company.slug, {}).get(field, [])
    rows = profile_rows if isinstance(profile_rows, list) and profile_rows else fallback_rows
    return [clean_label(str(row)) for row in rows if clean_label(str(row))]


def business_model_components(company: Company, business_model: BusinessModelSnapshot | None) -> dict[str, list[str]]:
    components: dict[str, list[str]] = {}
    if business_model:
        for component in business_model.components.all():
            components.setdefault(component.component_type, []).append(clean_label(component.name))
    reviewed_fallbacks = BUSINESS_MODEL_FALLBACKS.get(company.slug, {})
    sector_fallbacks = SECTOR_BUSINESS_MODEL_FALLBACKS.get(company.industry, {})
    for component_type in (BusinessModelComponentType.CHANNEL, BusinessModelComponentType.PARTNER):
        if not components.get(component_type):
            fallback = reviewed_fallbacks.get(component_type) or sector_fallbacks.get(component_type) or []
            components[component_type] = [clean_label(str(row)) for row in fallback if clean_label(str(row))]
    return components


def dependency_type_for_channel(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("platform", "app store", "marketplace", "digital")):
        return DependencyType.PLATFORM
    if any(term in lowered for term in ("dealer", "distributor", "retail", "wholesale", "pharmacy", "channel")):
        return DependencyType.DISTRIBUTOR
    if "contract" in lowered:
        return DependencyType.CONTRACT
    return DependencyType.PARTNER


def dependency_type_for_partner(value: str) -> str:
    lowered = value.lower()
    if "supplier" in lowered or "equipment" in lowered:
        return DependencyType.SUPPLIER
    if "manufacturer" in lowered:
        return DependencyType.MANUFACTURER
    if any(term in lowered for term in ("platform", "cloud", "infrastructure", "data center")):
        return DependencyType.INFRASTRUCTURE
    if "licens" in lowered:
        return DependencyType.LICENSOR
    if "distributor" in lowered or "dealer" in lowered or "delivery" in lowered:
        return DependencyType.DISTRIBUTOR
    return DependencyType.PARTNER


def unique_specs(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen = set()
    unique = []
    for row in rows:
        key = (row["dependency_type"], slugify(str(row["counterparty_name"])), row["product_scope"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def dependency_summary(company: Company, relationships: list[dict[str, object]]) -> str:
    customer_count = sum(1 for row in relationships if row["dependency_type"] == DependencyType.CUSTOMER_SEGMENT)
    supply_count = len(relationships) - customer_count
    return f"{company.name} dependency baseline includes {customer_count} customer-segment categories and {supply_count} supplier, platform, distribution, or partner categories."


def match_company(name: str) -> Company | None:
    key = slugify(name).replace("-", "")
    for company in Company.objects.filter(is_active=True):
        names = [company.name, company.slug, *(company.aliases if isinstance(company.aliases, list) else [])]
        if any(slugify(str(row)).replace("-", "") == key for row in names):
            return company
    return None


def clean_label(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip(" .;:-")

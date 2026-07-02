from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.utils.text import slugify

from apps.companies.models import (
    CapitalAllocationCategory,
    CapitalAllocationItem,
    CapitalAllocationPeriod,
    Company,
    CompanyProfileStatus,
    CompanyThemeExposure,
    KpiDefinition,
    SectorTheme,
    SectorThemeSnapshot,
    ThemeExposureType,
    ThemeMateriality,
    ThemeTaxonomyType,
)
from apps.curation.models import BusinessEvent, StrategicTurn
from apps.ingestion.models import SourceDocument


METHODOLOGY = (
    "Built from reviewed event themes, active KPI definitions, reviewed capital-allocation rows, and company sector metadata. "
    "Material operating exposure requires source-backed operating evidence; broad sector labels remain narrative-only context."
)


@dataclass(frozen=True)
class ThemeSpec:
    name: str
    taxonomy_type: str = ThemeTaxonomyType.THEME
    parent: str = ""
    description: str = ""
    aliases: tuple[str, ...] = ()


CORE_THEMES = (
    ThemeSpec("Artificial Intelligence", description="AI-enabled products, infrastructure, automation, or investment.", aliases=("AI", "machine learning")),
    ThemeSpec("Cloud and Digital Infrastructure", description="Cloud platforms, data centers, networks, and digital infrastructure.", aliases=("cloud", "data center")),
    ThemeSpec("Advertising Cycle", description="Advertising demand, ad products, ad-supported tiers, and marketing budgets.", aliases=("ads", "advertising")),
    ThemeSpec("Electric Vehicles", description="EV products, batteries, charging, and fleet electrification.", aliases=("EV", "battery")),
    ThemeSpec("Energy Transition", description="Low-carbon energy, emissions, electrification, renewables, and transition capex."),
    ThemeSpec("Commodity and Energy Prices", description="Commodity, fuel, power, metals, and energy price exposure."),
    ThemeSpec("Interest Rates and Credit", description="Rates, credit availability, debt, financing, and payment volume sensitivity."),
    ThemeSpec("Healthcare Pipeline", description="Drug development, approvals, clinical pipeline, and healthcare product cycles."),
    ThemeSpec("Streaming and Content", description="Streaming platforms, content investment, live events, gaming, and media distribution."),
    ThemeSpec("Supply Chain and Logistics", description="Suppliers, freight, inventory, distribution, production, and channel shifts."),
    ThemeSpec("Real Estate and Construction Demand", description="Real estate occupancy, leasing, construction, housing, and infrastructure demand."),
    ThemeSpec("Cybersecurity and Data Privacy", description="Security, privacy, data protection, and compliance exposure."),
    ThemeSpec("Regulatory and Legal Risk", description="Regulatory requirements, litigation, approvals, investigations, and compliance constraints."),
    ThemeSpec("Capital Intensity and R&D", description="Capex, research and development, production capacity, and long-horizon investment."),
    ThemeSpec("M&A and Industry Consolidation", description="Acquisitions, divestitures, integration, and consolidation themes."),
)


EVENT_THEME_RULES = (
    ("AD_SUPPORTED", "Advertising Cycle", ThemeExposureType.REVENUE),
    ("ADVERTISING", "Advertising Cycle", ThemeExposureType.REVENUE),
    ("ADS", "Advertising Cycle", ThemeExposureType.REVENUE),
    ("AI", "Artificial Intelligence", ThemeExposureType.PRODUCT),
    ("CLOUD", "Cloud and Digital Infrastructure", ThemeExposureType.PRODUCT),
    ("PLATFORM_AND_TECHNOLOGY_SHIFT", "Cloud and Digital Infrastructure", ThemeExposureType.PRODUCT),
    ("ELECTRIC", "Electric Vehicles", ThemeExposureType.PRODUCT),
    ("EV", "Electric Vehicles", ThemeExposureType.PRODUCT),
    ("ENERGY_TRANSITION", "Energy Transition", ThemeExposureType.CAPEX),
    ("COMMODITY", "Commodity and Energy Prices", ThemeExposureType.COST),
    ("CREDIT", "Interest Rates and Credit", ThemeExposureType.COST),
    ("R_AND_D", "Healthcare Pipeline", ThemeExposureType.PRODUCT),
    ("PIPELINE", "Healthcare Pipeline", ThemeExposureType.PRODUCT),
    ("STREAMING", "Streaming and Content", ThemeExposureType.PRODUCT),
    ("CONTENT", "Streaming and Content", ThemeExposureType.PRODUCT),
    ("GAMING", "Streaming and Content", ThemeExposureType.PRODUCT),
    ("LIVE_EVENTS", "Streaming and Content", ThemeExposureType.PRODUCT),
    ("SUPPLY_CHAIN", "Supply Chain and Logistics", ThemeExposureType.SUPPLY_CHAIN),
    ("CHANNEL", "Supply Chain and Logistics", ThemeExposureType.SUPPLY_CHAIN),
    ("REAL_ESTATE", "Real Estate and Construction Demand", ThemeExposureType.CUSTOMER),
    ("CONSTRUCTION", "Real Estate and Construction Demand", ThemeExposureType.CUSTOMER),
    ("REGULATORY", "Regulatory and Legal Risk", ThemeExposureType.REGULATORY),
    ("LEGAL", "Regulatory and Legal Risk", ThemeExposureType.REGULATORY),
    ("CAPITAL_ALLOCATION", "Capital Intensity and R&D", ThemeExposureType.CAPEX),
    ("ACQUISITION", "M&A and Industry Consolidation", ThemeExposureType.CAPEX),
)


SECTOR_THEME_RULES = {
    "Communication Services": ("Advertising Cycle", "Streaming and Content", "Cybersecurity and Data Privacy"),
    "Information Technology": ("Artificial Intelligence", "Cloud and Digital Infrastructure", "Cybersecurity and Data Privacy"),
    "Consumer Discretionary": ("Supply Chain and Logistics", "Advertising Cycle", "Interest Rates and Credit"),
    "Consumer Staples": ("Supply Chain and Logistics", "Commodity and Energy Prices"),
    "Industrials": ("Supply Chain and Logistics", "Real Estate and Construction Demand", "Capital Intensity and R&D"),
    "Energy": ("Commodity and Energy Prices", "Energy Transition", "Capital Intensity and R&D"),
    "Utilities": ("Energy Transition", "Commodity and Energy Prices", "Interest Rates and Credit"),
    "Materials": ("Commodity and Energy Prices", "Energy Transition", "Capital Intensity and R&D"),
    "Health Care": ("Healthcare Pipeline", "Regulatory and Legal Risk", "Capital Intensity and R&D"),
    "Financials": ("Interest Rates and Credit", "Cybersecurity and Data Privacy", "Regulatory and Legal Risk"),
    "Real Estate": ("Real Estate and Construction Demand", "Interest Rates and Credit", "Capital Intensity and R&D"),
}


def build_sector_theme_intelligence(company: Company) -> dict[str, int]:
    ensure_taxonomy(company)
    source = latest_source(company)
    effective_date = latest_evidence_date(company) or date.today()
    snapshot, created = SectorThemeSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": theme_summary(company),
            "methodology": METHODOLOGY,
            "confidence_score": "0.780",
        },
    )
    created_count = updated_count = 0
    keep_ids: set[int] = set()
    for spec in exposure_specs(company):
        exposure, was_created = CompanyThemeExposure.objects.update_or_create(
            snapshot=snapshot,
            source_key=spec["source_key"],
            defaults=spec,
        )
        keep_ids.add(exposure.id)
        created_count += 1 if was_created else 0
        updated_count += 0 if was_created else 1
    snapshot.exposures.exclude(id__in=keep_ids).delete()
    return {
        "snapshots_created": 1 if created else 0,
        "snapshots_updated": 0 if created else 1,
        "exposures_created": created_count,
        "exposures_updated": updated_count,
    }


def sector_theme_quality_issues(company: Company) -> list[str]:
    snapshot = latest_snapshot(company)
    if snapshot is None:
        return ["no reviewed sector and theme snapshot"]
    issues = []
    if not snapshot.exposures.exists():
        issues.append("no reviewed theme exposures")
    if not snapshot.exposures.exclude(materiality=ThemeMateriality.NARRATIVE_ONLY).exists():
        issues.append("no operating theme exposure")
    if not snapshot.exposures.filter(linked_event__isnull=False).exists():
        issues.append("no event-linked theme exposure")
    return issues


def ensure_taxonomy(company: Company) -> None:
    sector = sector_theme(company)
    for spec in CORE_THEMES:
        upsert_theme(spec)
    for theme_name in SECTOR_THEME_RULES.get(company.industry, ()):
        theme = SectorTheme.objects.get(slug=slugify(theme_name))
        if sector and theme.parent_id is None:
            theme.parent = sector
            theme.save(update_fields=["parent", "updated_at"])


def sector_theme(company: Company) -> SectorTheme | None:
    if not company.industry:
        return None
    return upsert_theme(
        ThemeSpec(
            name=company.industry,
            taxonomy_type=ThemeTaxonomyType.SECTOR,
            description=f"Configured company sector for {company.industry} companies.",
        )
    )


def upsert_theme(spec: ThemeSpec) -> SectorTheme:
    parent = SectorTheme.objects.filter(slug=slugify(spec.parent)).first() if spec.parent else None
    theme, _created = SectorTheme.objects.update_or_create(
        slug=slugify(spec.name),
        defaults={
            "name": spec.name,
            "taxonomy_type": spec.taxonomy_type,
            "parent": parent,
            "description": spec.description,
            "aliases": list(spec.aliases),
            "is_active": True,
        },
    )
    return theme


def exposure_specs(company: Company) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    sector = sector_theme(company)
    source = latest_source(company)
    if sector:
        specs.append({
            "theme": sector,
            "exposure_type": ThemeExposureType.NARRATIVE,
            "materiality": ThemeMateriality.NARRATIVE_ONLY,
            "source_key": f"sector:{sector.slug}",
            "evidence_date": None,
            "evidence_summary": f"{company.name} is classified in {company.industry}.",
            "evidence_text": company.description or f"Configured sector: {company.industry}.",
            "exposure_rationale": "Sector classification provides navigation context only and is not treated as operating exposure.",
            "source_document": source,
            "linked_event": None,
            "linked_kpi": None,
            "linked_capital_allocation_item": None,
            "confidence_score": "0.650",
            "review_status": "REVIEWED",
        })
    specs.extend(event_exposures(company))
    specs.extend(kpi_exposures(company))
    specs.extend(capital_allocation_exposures(company))
    return dedupe_specs(specs)


def event_exposures(company: Company) -> list[dict[str, object]]:
    rows = []
    events = (
        BusinessEvent.objects.filter(company=company, review_status__in=["NEEDS_REVIEW", "APPROVED"])
        .select_related("source_document")
        .order_by("-event_date", "-created_at")[:40]
    )
    for event in events:
        mapped = map_theme(event.decision_theme or event.event_type or event.actual_change or event.source_claim)
        if not mapped:
            continue
        theme_name, exposure_type = mapped
        theme = SectorTheme.objects.get(slug=slugify(theme_name))
        rows.append({
            "theme": theme,
            "exposure_type": exposure_type,
            "materiality": materiality_for_event(event),
            "source_key": f"event:{event.id}:{theme.slug}:{exposure_type}",
            "evidence_date": event.event_date,
            "evidence_summary": event.actual_change or event.source_claim or event.decision_theme,
            "evidence_text": event.evidence_text or event.source_claim or event.actual_change,
            "exposure_rationale": f"Mapped from reviewed event theme {event.decision_theme or event.event_type}.",
            "source_document": event.source_document,
            "linked_event": event,
            "linked_kpi": None,
            "linked_capital_allocation_item": None,
            "confidence_score": event.confidence_score,
            "review_status": "REVIEWED",
        })
    return rows


def kpi_exposures(company: Company) -> list[dict[str, object]]:
    rows = []
    for kpi in KpiDefinition.objects.filter(company=company, is_active=True).prefetch_related("observations")[:30]:
        mapped = map_kpi(kpi)
        if not mapped:
            continue
        theme_name, exposure_type = mapped
        theme = SectorTheme.objects.get(slug=slugify(theme_name))
        has_values = kpi.observations.exists()
        rows.append({
            "theme": theme,
            "exposure_type": exposure_type,
            "materiality": ThemeMateriality.OPERATING if has_values else ThemeMateriality.WATCH,
            "source_key": f"kpi:{kpi.id}:{theme.slug}:{exposure_type}",
            "evidence_date": latest_kpi_date(kpi),
            "evidence_summary": f"{kpi.name} is tracked as an operating KPI.",
            "evidence_text": kpi.description,
            "exposure_rationale": "Mapped from an active KPI definition, so it represents an operating metric rather than a marketing mention.",
            "source_document": None,
            "linked_event": None,
            "linked_kpi": kpi,
            "linked_capital_allocation_item": None,
            "confidence_score": "0.760" if has_values else "0.680",
            "review_status": "REVIEWED",
        })
    return rows


def capital_allocation_exposures(company: Company) -> list[dict[str, object]]:
    rows = []
    periods = CapitalAllocationPeriod.objects.filter(company=company, is_published=True, review_status="REVIEWED").prefetch_related("items").order_by("-period_end")[:4]
    for period in periods:
        for item in period.items.all():
            mapped = map_capital_item(item)
            if not mapped:
                continue
            theme_name, exposure_type = mapped
            theme = SectorTheme.objects.get(slug=slugify(theme_name))
            rows.append({
                "theme": theme,
                "exposure_type": exposure_type,
                "materiality": ThemeMateriality.MATERIAL_OPERATING if abs(item.value or 0) > Decimal("0") else ThemeMateriality.WATCH,
                "source_key": f"capital:{item.id}:{theme.slug}:{exposure_type}",
                "evidence_date": period.period_end,
                "evidence_summary": f"{item.label}: {item.value} {item.unit}",
                "evidence_text": item.evidence_text or period.headline,
                "exposure_rationale": "Mapped from reviewed capital allocation, so it reflects where resources are being deployed.",
                "source_document": item.source_document,
                "linked_event": None,
                "linked_kpi": None,
                "linked_capital_allocation_item": item,
                "confidence_score": item.confidence_score,
                "review_status": "REVIEWED",
            })
    return rows


def map_theme(text: str | None) -> tuple[str, str] | None:
    normalized = (text or "").upper()
    for needle, theme_name, exposure_type in EVENT_THEME_RULES:
        if needle in normalized:
            return theme_name, exposure_type
    return None


def map_kpi(kpi: KpiDefinition) -> tuple[str, str] | None:
    text = f"{kpi.name} {kpi.description} {kpi.scope}".lower()
    if any(word in text for word in ("subscriber", "user", "customer", "member")):
        return "Streaming and Content", ThemeExposureType.CUSTOMER
    if any(word in text for word in ("advertising", "ads", "ad ")):
        return "Advertising Cycle", ThemeExposureType.REVENUE
    if any(word in text for word in ("cloud", "data center", "compute")):
        return "Cloud and Digital Infrastructure", ThemeExposureType.PRODUCT
    if any(word in text for word in ("research", "pipeline", "clinical")):
        return "Healthcare Pipeline", ThemeExposureType.PRODUCT
    if any(word in text for word in ("production", "delivery", "store", "inventory", "freight")):
        return "Supply Chain and Logistics", ThemeExposureType.SUPPLY_CHAIN
    if "revenue" in text or "sales" in text:
        return "Advertising Cycle", ThemeExposureType.REVENUE
    return None


def map_capital_item(item: CapitalAllocationItem) -> tuple[str, str] | None:
    if item.category == CapitalAllocationCategory.R_AND_D:
        return "Capital Intensity and R&D", ThemeExposureType.CAPEX
    if item.category == CapitalAllocationCategory.CAPEX:
        return "Capital Intensity and R&D", ThemeExposureType.CAPEX
    if item.category == CapitalAllocationCategory.CONTENT_INVENTORY:
        return "Streaming and Content", ThemeExposureType.CAPEX
    if item.category == CapitalAllocationCategory.ACQUISITION_INVESTMENT:
        return "M&A and Industry Consolidation", ThemeExposureType.CAPEX
    if item.category in {CapitalAllocationCategory.DEBT_ISSUANCE, CapitalAllocationCategory.DEBT_REPAYMENT}:
        return "Interest Rates and Credit", ThemeExposureType.COST
    return None


def materiality_for_event(event: BusinessEvent) -> str:
    confidence = Decimal(str(event.confidence_score or 0))
    if event.source_document_id and event.actual_change and confidence >= Decimal("0.700"):
        return ThemeMateriality.OPERATING
    if event.source_document_id:
        return ThemeMateriality.WATCH
    return ThemeMateriality.NARRATIVE_ONLY


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def latest_evidence_date(company: Company) -> date | None:
    dates = [
        BusinessEvent.objects.filter(company=company, event_date__isnull=False).order_by("-event_date").values_list("event_date", flat=True).first(),
        StrategicTurn.objects.filter(company=company, start_date__isnull=False).order_by("-start_date").values_list("start_date", flat=True).first(),
        CapitalAllocationPeriod.objects.filter(company=company, period_end__isnull=False).order_by("-period_end").values_list("period_end", flat=True).first(),
    ]
    return next((row for row in dates if row), None)


def latest_snapshot(company: Company) -> SectorThemeSnapshot | None:
    return (
        SectorThemeSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("exposures")
        .order_by("-effective_date", "-updated_at")
        .first()
    )


def latest_kpi_date(kpi: KpiDefinition) -> date | None:
    observation = kpi.observations.order_by("-period_end").first()
    return observation.period_end if observation else None


def theme_summary(company: Company) -> str:
    sector_themes = SECTOR_THEME_RULES.get(company.industry, ())
    if sector_themes:
        return f"{company.name} is mapped to {company.industry} and monitored against {', '.join(sector_themes[:3])}."
    if company.industry:
        return f"{company.name} is mapped to {company.industry}; operating theme exposure depends on reviewed events, KPIs, and capital allocation."
    return f"{company.name} has no reviewed sector classification yet; theme exposure depends on reviewed events, KPIs, and capital allocation."


def dedupe_specs(specs: list[dict[str, object]]) -> list[dict[str, object]]:
    seen = set()
    rows = []
    for spec in specs:
        key = spec["source_key"]
        if key in seen:
            continue
        seen.add(key)
        rows.append(spec)
    return rows

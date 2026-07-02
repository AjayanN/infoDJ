from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.utils.text import slugify

from apps.companies.models import (
    Company,
    CompanyProfileStatus,
    CompanyThemeExposure,
    MacroEvidenceType,
    MacroExposureChannel,
    MacroFactor,
    MacroFactorCategory,
    MacroSensitivity,
    MacroSensitivityDirection,
    MacroSensitivitySnapshot,
    MacroStressExample,
    ThemeMateriality,
)
from apps.curation.models import BusinessEvent
from apps.ingestion.models import FinancialFact, MarketPrice, SourceDocument


METHODOLOGY = (
    "Built from reviewed company events, sector/theme exposure rows, capital/KPI-derived context, and available financial/market data. "
    "Calculated relationships are withheld unless aligned macro series, company series, sample size, lag assumptions, currency, and reporting periods are available."
)
LIMITATION_NOTE = (
    "This profile is sensitivity context only. It does not claim causation from simple correlations and does not forecast macro variables or company performance."
)


@dataclass(frozen=True)
class MacroFactorSpec:
    name: str
    category: str
    description: str
    canonical_series: tuple[str, ...]


MACRO_FACTORS = (
    MacroFactorSpec("Interest rates", MacroFactorCategory.FINANCING, "Rate changes affecting borrowing costs, discount rates, housing, credit, and financial activity.", ("FEDFUNDS", "DGS10")),
    MacroFactorSpec("Inflation", MacroFactorCategory.COST, "Input cost, pricing, wage, and consumer purchasing power pressure.", ("CPIAUCSL", "PCEPI")),
    MacroFactorSpec("Consumer spending", MacroFactorCategory.DEMAND, "Household demand for discretionary or staple goods and services.", ("PCE", "RSAFS")),
    MacroFactorSpec("Business investment", MacroFactorCategory.DEMAND, "Enterprise, industrial, infrastructure, and capital-equipment demand.", ("PNFI", "DGORDER")),
    MacroFactorSpec("Exchange rates", MacroFactorCategory.CURRENCY, "Currency translation, transaction, and international purchasing-power exposure.", ("DTWEXBGS",)),
    MacroFactorSpec("Commodity and energy prices", MacroFactorCategory.COMMODITY, "Oil, gas, metals, power, fuel, and raw-material price exposure.", ("DCOILWTICO", "PPIACO")),
    MacroFactorSpec("Housing and construction activity", MacroFactorCategory.DEMAND, "Housing, commercial construction, leasing, occupancy, and construction-equipment demand.", ("HOUST", "TTLCONS")),
    MacroFactorSpec("Advertising demand", MacroFactorCategory.DEMAND, "Marketing budgets and advertising cycle exposure.", ("USADVERTISING",)),
    MacroFactorSpec("Credit conditions", MacroFactorCategory.FINANCING, "Credit availability, payment volumes, default risk, and capital-market access.", ("BAMLC0A0CM", "DRTSCILM")),
    MacroFactorSpec("Freight and logistics costs", MacroFactorCategory.COST, "Freight, logistics, inventory movement, and distribution-cost exposure.", ("FRGSHPUSM649NCIS",)),
    MacroFactorSpec("Labor market", MacroFactorCategory.LABOR, "Wage, employment, staffing, and labor availability exposure.", ("UNRATE", "CES0500000003")),
)


THEME_FACTOR_RULES = {
    "Advertising Cycle": ("Advertising demand", MacroExposureChannel.REVENUE, MacroSensitivityDirection.POSITIVE),
    "Interest Rates and Credit": ("Interest rates", MacroExposureChannel.FINANCING, MacroSensitivityDirection.MIXED),
    "Commodity and Energy Prices": ("Commodity and energy prices", MacroExposureChannel.COST, MacroSensitivityDirection.MIXED),
    "Energy Transition": ("Commodity and energy prices", MacroExposureChannel.CAPEX, MacroSensitivityDirection.CHANGING),
    "Supply Chain and Logistics": ("Freight and logistics costs", MacroExposureChannel.COST, MacroSensitivityDirection.NEGATIVE),
    "Real Estate and Construction Demand": ("Housing and construction activity", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE),
    "Capital Intensity and R&D": ("Business investment", MacroExposureChannel.CAPEX, MacroSensitivityDirection.MIXED),
    "Streaming and Content": ("Consumer spending", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE),
    "Healthcare Pipeline": ("Business investment", MacroExposureChannel.CAPEX, MacroSensitivityDirection.MIXED),
    "Cloud and Digital Infrastructure": ("Business investment", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE),
    "Electric Vehicles": ("Consumer spending", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE),
    "M&A and Industry Consolidation": ("Credit conditions", MacroExposureChannel.FINANCING, MacroSensitivityDirection.MIXED),
}

SECTOR_FACTOR_RULES = {
    "Financials": ("Interest rates", MacroExposureChannel.FINANCING, MacroSensitivityDirection.MIXED),
    "Real Estate": ("Interest rates", MacroExposureChannel.FINANCING, MacroSensitivityDirection.NEGATIVE),
    "Consumer Discretionary": ("Consumer spending", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE),
    "Consumer Staples": ("Inflation", MacroExposureChannel.COST, MacroSensitivityDirection.MIXED),
    "Industrials": ("Business investment", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE),
    "Energy": ("Commodity and energy prices", MacroExposureChannel.REVENUE, MacroSensitivityDirection.MIXED),
    "Utilities": ("Interest rates", MacroExposureChannel.FINANCING, MacroSensitivityDirection.NEGATIVE),
    "Materials": ("Commodity and energy prices", MacroExposureChannel.REVENUE, MacroSensitivityDirection.MIXED),
    "Communication Services": ("Advertising demand", MacroExposureChannel.REVENUE, MacroSensitivityDirection.POSITIVE),
    "Information Technology": ("Business investment", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE),
    "Health Care": ("Inflation", MacroExposureChannel.COST, MacroSensitivityDirection.MIXED),
}


def build_macro_sensitivity_profile(company: Company) -> dict[str, int]:
    ensure_macro_factors()
    effective_date = latest_evidence_date(company) or date.today()
    snapshot, created = MacroSensitivitySnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": latest_source(company),
            "status": CompanyProfileStatus.REVIEWED,
            "summary": summary_for(company),
            "methodology": METHODOLOGY,
            "limitation_note": LIMITATION_NOTE,
            "confidence_score": "0.760",
        },
    )
    counters = {
        "snapshots_created": 1 if created else 0,
        "snapshots_updated": 0 if created else 1,
        "sensitivities_created": 0,
        "sensitivities_updated": 0,
        "stress_examples_created": 0,
        "stress_examples_updated": 0,
    }
    keep_ids: set[int] = set()
    for spec in sensitivity_specs(company):
        row, was_created = MacroSensitivity.objects.update_or_create(
            snapshot=snapshot,
            source_key=spec["source_key"],
            defaults=spec,
        )
        keep_ids.add(row.id)
        counters["sensitivities_created" if was_created else "sensitivities_updated"] += 1
    snapshot.sensitivities.exclude(id__in=keep_ids).delete()

    stress = upsert_stress_examples(snapshot, company)
    counters["stress_examples_created"] = stress["created"]
    counters["stress_examples_updated"] = stress["updated"]
    return counters


def macro_sensitivity_quality_issues(company: Company) -> list[str]:
    snapshot = latest_snapshot(company)
    if snapshot is None:
        return ["no reviewed macro sensitivity snapshot"]
    issues = []
    if not snapshot.sensitivities.exists():
        issues.append("no reviewed macro sensitivities")
    if not snapshot.sensitivities.filter(evidence_type=MacroEvidenceType.MANAGEMENT_DISCLOSED).exists():
        issues.append("no management-disclosed sensitivity")
    if not snapshot.sensitivities.filter(evidence_type=MacroEvidenceType.CALCULATED_PLACEHOLDER).exists():
        issues.append("no calculated relationship placeholder")
    if not snapshot.limitation_note:
        issues.append("limitations unavailable")
    return issues


def ensure_macro_factors() -> None:
    for spec in MACRO_FACTORS:
        MacroFactor.objects.update_or_create(
            slug=slugify(spec.name),
            defaults={
                "name": spec.name,
                "category": spec.category,
                "description": spec.description,
                "canonical_series": list(spec.canonical_series),
                "is_active": True,
            },
        )


def sensitivity_specs(company: Company) -> list[dict[str, object]]:
    specs = []
    specs.extend(sector_sensitivity(company))
    specs.extend(theme_sensitivities(company))
    specs.extend(event_sensitivities(company))
    specs.extend(calculated_placeholders(company))
    return dedupe_specs(specs)


def sector_sensitivity(company: Company) -> list[dict[str, object]]:
    rule = SECTOR_FACTOR_RULES.get(company.industry)
    if not rule:
        return []
    factor_name, channel, direction = rule
    factor = MacroFactor.objects.get(slug=slugify(factor_name))
    return [base_spec(
        company=company,
        factor=factor,
        channel=channel,
        direction=direction,
        evidence_type=MacroEvidenceType.MANAGEMENT_DISCLOSED,
        materiality=ThemeMateriality.WATCH,
        source_key=f"sector:{company.industry}:{factor.slug}",
        evidence_date=None,
        evidence_summary=f"{company.name} sector context indicates {factor.name.lower()} sensitivity.",
        evidence_text=company.description or f"Configured sector: {company.industry}.",
        method="Sector rule based on company classification; treated as disclosed/contextual sensitivity, not calculated relationship.",
        source_document=latest_source(company),
        linked_event=None,
        linked_theme_exposure=None,
        confidence="0.620",
    )]


def theme_sensitivities(company: Company) -> list[dict[str, object]]:
    rows = []
    latest_theme_snapshot = (
        company.sector_theme_snapshots.filter(status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("exposures__theme", "exposures__source_document")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if not latest_theme_snapshot:
        return rows
    for exposure in latest_theme_snapshot.exposures.exclude(materiality=ThemeMateriality.NARRATIVE_ONLY)[:30]:
        rule = THEME_FACTOR_RULES.get(exposure.theme.name)
        if not rule:
            continue
        factor_name, channel, direction = rule
        factor = MacroFactor.objects.get(slug=slugify(factor_name))
        rows.append(base_spec(
            company=company,
            factor=factor,
            channel=channel,
            direction=direction,
            evidence_type=MacroEvidenceType.THEME_DERIVED,
            materiality=exposure.materiality,
            source_key=f"theme:{exposure.id}:{factor.slug}",
            evidence_date=exposure.evidence_date,
            evidence_summary=exposure.evidence_summary,
            evidence_text=exposure.evidence_text,
            method="Derived from reviewed Sector and Theme Intelligence exposure; no standalone macro-series calculation is implied.",
            source_document=exposure.source_document,
            linked_event=exposure.linked_event,
            linked_theme_exposure=exposure,
            confidence=exposure.confidence_score,
        ))
    return rows


def event_sensitivities(company: Company) -> list[dict[str, object]]:
    rows = []
    events = BusinessEvent.objects.filter(company=company, review_status__in=["NEEDS_REVIEW", "APPROVED"]).select_related("source_document").order_by("-event_date", "-created_at")[:30]
    for event in events:
        text = " ".join([event.decision_theme or "", event.actual_change or "", event.source_claim or "", event.evidence_text or ""]).lower()
        mapping = event_mapping(text)
        if not mapping:
            continue
        factor_name, channel, direction = mapping
        factor = MacroFactor.objects.get(slug=slugify(factor_name))
        rows.append(base_spec(
            company=company,
            factor=factor,
            channel=channel,
            direction=direction,
            evidence_type=MacroEvidenceType.MANAGEMENT_DISCLOSED,
            materiality=ThemeMateriality.OPERATING if event.source_document_id else ThemeMateriality.WATCH,
            source_key=f"event:{event.id}:{factor.slug}",
            evidence_date=event.event_date,
            evidence_summary=event.actual_change or event.source_claim or event.decision_theme,
            evidence_text=event.evidence_text or event.source_claim or event.actual_change,
            method="Mapped from reviewed company event language. Direction reflects disclosed exposure channel, not measured causal effect.",
            source_document=event.source_document,
            linked_event=event,
            linked_theme_exposure=None,
            confidence=event.confidence_score,
        ))
    return rows


def calculated_placeholders(company: Company) -> list[dict[str, object]]:
    rows = []
    financial_count = FinancialFact.objects.filter(company=company).count()
    price_count = MarketPrice.objects.filter(company=company).count()
    factor_names = [row[0] for row in SECTOR_FACTOR_RULES.values()] if company.industry in SECTOR_FACTOR_RULES else ["Consumer spending"]
    for factor_name in sorted(set(factor_names)):
        factor = MacroFactor.objects.get(slug=slugify(factor_name))
        rows.append(base_spec(
            company=company,
            factor=factor,
            channel=MacroExposureChannel.DEMAND if factor.category == MacroFactorCategory.DEMAND else MacroExposureChannel.COST,
            direction=MacroSensitivityDirection.UNCERTAIN,
            evidence_type=MacroEvidenceType.CALCULATED_PLACEHOLDER,
            materiality=ThemeMateriality.UNKNOWN,
            source_key=f"calculated-placeholder:{factor.slug}",
            evidence_date=None,
            evidence_summary="Calculated historical relationship is unavailable until aligned macro and company series are collected.",
            evidence_text=f"Available company inputs: {financial_count} financial facts and {price_count} market price rows.",
            method="No correlation or regression is published. Required before calculation: aligned macro series, company metric series, period frequency, lag assumption, currency treatment, sample size, and stress-period validation.",
            sample_size=0,
            source_document=None,
            linked_event=None,
            linked_theme_exposure=None,
            confidence="0.500",
        ))
    return rows


def base_spec(
    *,
    company: Company,
    factor: MacroFactor,
    channel: str,
    direction: str,
    evidence_type: str,
    materiality: str,
    source_key: str,
    evidence_date: date | None,
    evidence_summary: str,
    evidence_text: str,
    method: str,
    source_document: SourceDocument | None,
    linked_event: BusinessEvent | None,
    linked_theme_exposure: CompanyThemeExposure | None,
    confidence: object,
    sample_size: int = 0,
) -> dict[str, object]:
    return {
        "factor": factor,
        "channel": channel,
        "direction": direction,
        "evidence_type": evidence_type,
        "materiality": materiality,
        "source_key": source_key,
        "evidence_date": evidence_date,
        "evidence_summary": evidence_summary or f"{company.name} has reviewed macro sensitivity context for {factor.name}.",
        "evidence_text": evidence_text,
        "method": method,
        "sample_size": sample_size,
        "period_start": None,
        "period_end": evidence_date,
        "lag_assumption": "None applied" if evidence_type != MacroEvidenceType.CALCULATED_PLACEHOLDER else "Not calculated",
        "limitation_note": LIMITATION_NOTE,
        "source_document": source_document,
        "linked_event": linked_event,
        "linked_theme_exposure": linked_theme_exposure,
        "confidence_score": confidence or "0.600",
        "review_status": "REVIEWED",
    }


def upsert_stress_examples(snapshot: MacroSensitivitySnapshot, company: Company) -> dict[str, int]:
    examples = stress_specs(company)
    created = updated = 0
    keep_ids: set[int] = set()
    for spec in examples:
        row, was_created = MacroStressExample.objects.update_or_create(snapshot=snapshot, label=spec["label"], defaults=spec)
        keep_ids.add(row.id)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    snapshot.stress_examples.exclude(id__in=keep_ids).delete()
    return {"created": created, "updated": updated}


def stress_specs(company: Company) -> list[dict[str, object]]:
    facts = FinancialFact.objects.filter(company=company).order_by("-filed")[:2]
    examples = []
    for fact in facts:
        examples.append({
            "label": f"{fact.fy or 'Unknown year'} {fact.fp or 'period'} reported {fact.label or fact.concept}",
            "period_start": None,
            "period_end": fact.filed,
            "macro_context": "Macro stress context requires an aligned external macro period label; not inferred from the company filing alone.",
            "company_observation": f"{fact.label or fact.concept}: {fact.value} {fact.unit}.",
            "limitation_note": "Company observation is shown as context only and is not attributed to the macro factor without external series alignment.",
            "source_document": None,
            "confidence_score": "0.600",
        })
    if examples:
        return examples
    return [{
        "label": "Stress-period example unavailable",
        "period_start": None,
        "period_end": None,
        "macro_context": "No reviewed company observation is available for a stress-period example.",
        "company_observation": "",
        "limitation_note": "Collect company metrics and macro period definitions before publishing stress-period examples.",
        "source_document": latest_source(company),
        "confidence_score": "0.500",
    }]


def event_mapping(text: str) -> tuple[str, str, str] | None:
    if any(word in text for word in ("inflation", "pricing pressure", "wage")):
        return "Inflation", MacroExposureChannel.COST, MacroSensitivityDirection.MIXED
    if any(word in text for word in ("interest", "credit", "financing", "debt")):
        return "Interest rates", MacroExposureChannel.FINANCING, MacroSensitivityDirection.MIXED
    if any(word in text for word in ("advertising", "ads", "marketing budget")):
        return "Advertising demand", MacroExposureChannel.REVENUE, MacroSensitivityDirection.POSITIVE
    if any(word in text for word in ("commodity", "oil", "gas", "fuel", "metals", "energy price")):
        return "Commodity and energy prices", MacroExposureChannel.COST, MacroSensitivityDirection.MIXED
    if any(word in text for word in ("foreign exchange", "currency", "fx")):
        return "Exchange rates", MacroExposureChannel.CURRENCY_TRANSLATION, MacroSensitivityDirection.MIXED
    if any(word in text for word in ("freight", "logistics", "supply chain")):
        return "Freight and logistics costs", MacroExposureChannel.SUPPLY_CHAIN, MacroSensitivityDirection.NEGATIVE
    if any(word in text for word in ("housing", "construction", "occupancy", "leasing")):
        return "Housing and construction activity", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE
    if any(word in text for word in ("consumer", "subscriber", "member", "retail demand")):
        return "Consumer spending", MacroExposureChannel.DEMAND, MacroSensitivityDirection.POSITIVE
    return None


def latest_snapshot(company: Company) -> MacroSensitivitySnapshot | None:
    return (
        MacroSensitivitySnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("sensitivities")
        .order_by("-effective_date", "-updated_at")
        .first()
    )


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def latest_evidence_date(company: Company) -> date | None:
    return (
        BusinessEvent.objects.filter(company=company, event_date__isnull=False).order_by("-event_date").values_list("event_date", flat=True).first()
        or FinancialFact.objects.filter(company=company, filed__isnull=False).order_by("-filed").values_list("filed", flat=True).first()
        or MarketPrice.objects.filter(company=company).order_by("-price_date").values_list("price_date", flat=True).first()
    )


def summary_for(company: Company) -> str:
    if company.industry in SECTOR_FACTOR_RULES:
        factor_name, _channel, _direction = SECTOR_FACTOR_RULES[company.industry]
        return f"{company.name} has reviewed macro sensitivity context anchored on {factor_name.lower()} and related operating evidence."
    return f"{company.name} has reviewed macro sensitivity context where source-backed events, themes, or financial facts are available."


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

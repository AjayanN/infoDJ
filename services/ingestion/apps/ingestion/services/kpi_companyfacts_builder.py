from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal

from django.utils.text import slugify

from apps.companies.models import KpiDefinition, KpiDefinitionVersion, KpiObservation
from apps.ingestion.models import FinancialFact, SourceDocument


def build_companyfacts_kpis(company) -> dict[str, int]:
    facts = list(FinancialFact.objects.filter(company=company).order_by("concept", "unit", "filed", "id"))
    grouped: dict[tuple[str, str, str], list[FinancialFact]] = defaultdict(list)
    for fact in facts:
        cadence = cadence_for_fact(fact)
        if cadence:
            grouped[(fact.concept, fact.unit, cadence)].append(fact)

    counters = {"definitions": 0, "observations": 0, "skipped": len(facts) - sum(map(len, grouped.values()))}
    for (concept, unit, cadence), rows in grouped.items():
        latest_by_period: dict[date, tuple[FinancialFact, date, bool]] = {}
        period_counts: dict[date, int] = defaultdict(int)
        for fact in rows:
            period_start, period_end = fact_period(fact)
            if period_end is None:
                counters["skipped"] += 1
                continue
            period_counts[period_end] += 1
            existing = latest_by_period.get(period_end)
            if existing is None or (fact.filed or date.min, fact.id) >= (existing[0].filed or date.min, existing[0].id):
                latest_by_period[period_end] = (fact, period_start or period_end, False)
        if not latest_by_period:
            continue

        sample = rows[-1]
        cadence_slug = cadence.lower()
        metric_slug = slugify(f"sec-{concept}-{unit}-{cadence_slug}")[:120]
        definition, _created = KpiDefinition.objects.update_or_create(
            company=company,
            slug=metric_slug,
            defaults={
                "name": f"{sample.label or concept} ({cadence.title()})",
                "description": f"Company-wide {cadence.lower()} fact reported through SEC XBRL Company Facts.",
                "unit": unit,
                "cadence": cadence,
                "value_type": "REPORTED",
                "scope": "Company-wide reported financial context",
                "aliases": [concept, sample.label or concept],
                "formula": "",
                "is_active": True,
                "peer_comparable": False,
            },
        )
        counters["definitions"] += 1
        first_period = min(latest_by_period)
        first_fact = latest_by_period[first_period][0]
        source = source_for_fact(company, first_fact)
        KpiDefinitionVersion.objects.update_or_create(
            kpi=definition,
            effective_date=first_period,
            defaults={
                "definition": f"{sample.label or concept}; SEC taxonomy concept {sample.taxonomy}:{concept}.",
                "scope": "Company-wide reported financial context",
                "change_note": "Standardized financial context, not a company-specific operating KPI such as users, stores, or production volume.",
                "source_document": source,
            },
        )
        for period_end, (fact, period_start, _restatement) in sorted(latest_by_period.items()):
            source = source_for_fact(company, fact)
            KpiObservation.objects.update_or_create(
                kpi=definition,
                period_end=period_end,
                segment="Company-wide",
                geography="",
                defaults={
                    "period_start": period_start,
                    "fiscal_year": fact.fy,
                    "fiscal_period": fact.fp,
                    "value": fact.value,
                    "source_document": source,
                    "evidence_text": f"SEC XBRL {fact.taxonomy}:{fact.concept}, accession {fact.accession_number}.",
                    "is_estimated": False,
                    "is_restatement": period_counts[period_end] > 1,
                    "is_non_comparable": True,
                    "definition_changed": False,
                    "confidence_score": Decimal("0.950"),
                },
            )
            counters["observations"] += 1
    return counters


def cadence_for_fact(fact: FinancialFact) -> str:
    fp = (fact.fp or "").upper()
    if fp in {"Q1", "Q2", "Q3", "Q4"}:
        start, end = fact_period(fact)
        if start and end and (end - start).days > 120:
            return ""
        return "QUARTERLY"
    if fp == "FY":
        return "ANNUAL"
    return ""


def fact_period(fact: FinancialFact) -> tuple[date | None, date | None]:
    raw = fact.raw if isinstance(fact.raw, dict) else {}
    start = parse_date(raw.get("start"))
    end = parse_date(raw.get("end"))
    if end is None:
        end = frame_end(fact.frame) or fact.filed
    return start, end


def parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def frame_end(frame: str) -> date | None:
    value = (frame or "").upper().removesuffix("I")
    if not value.startswith("CY"):
        return None
    try:
        year = int(value[2:6])
    except ValueError:
        return None
    suffix = value[6:]
    return {"": date(year, 12, 31), "Q1": date(year, 3, 31), "Q2": date(year, 6, 30), "Q3": date(year, 9, 30), "Q4": date(year, 12, 31)}.get(suffix)


def source_for_fact(company, fact: FinancialFact) -> SourceDocument:
    cik = str(company.sec_cik or "").lstrip("0")
    accession = (fact.accession_number or "").replace("-", "")
    if cik and accession:
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/"
    else:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(company.sec_cik or '').zfill(10)}.json"
    published = datetime.combine(fact.filed, time.min, tzinfo=timezone.utc) if fact.filed else None
    source, _created = SourceDocument.objects.update_or_create(
        url=url,
        defaults={
            "company": company,
            "source_api": "SEC_COMPANYFACTS",
            "canonical_url": url,
            "title": f"{company.name} SEC filing {fact.accession_number or fact.filed or ''}".strip(),
            "publisher": "SEC",
            "published_date": published,
            "snippet": f"Source for {fact.label or fact.concept} reported in {fact.fp or 'an SEC period'} {fact.fy or ''}.".strip(),
            "language": "en",
            "status": "APPROVED",
        },
    )
    return source

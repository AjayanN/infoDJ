"""SEC companyfacts API client and FinancialFact ingestion helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import socket
from time import sleep
from typing import Any, Iterable, Mapping

import requests
import urllib3.util.connection as urllib3_connection


SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
DEFAULT_USER_AGENT = "InfoDJ/0.1 business-event-research contact local-dev@example.com"

USEFUL_US_GAAP_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "CostOfRevenue",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "Assets",
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "OperatingCashFlow",
    "NetCashProvidedByUsedInOperatingActivities",
    "CapitalExpenditures",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "ResearchAndDevelopmentExpense",
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsForRepurchaseOfEquity",
    "PaymentsOfDividends",
    "PaymentsOfDividendsCommonStock",
    "PaymentsToAcquireBusinessesNetOfCashAcquired",
    "PaymentsToAcquireInvestments",
    "PaymentsToAcquireAvailableForSaleSecurities",
    "ProceedsFromIssuanceOfLongTermDebt",
    "ProceedsFromIssuanceOfDebt",
    "RepaymentsOfLongTermDebt",
    "RepaymentsOfDebt",
    "PaymentsOfDebtIssuanceCosts",
    "RestructuringCharges",
    "RestructuringAndRelatedCostIncurred",
    "InventoryWriteDown",
    "SellingGeneralAndAdministrativeExpense",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
)


def _allowed_gai_family() -> socket.AddressFamily:
    return socket.AF_INET


urllib3_connection.allowed_gai_family = _allowed_gai_family


@dataclass(frozen=True)
class SecCompanyFact:
    taxonomy: str
    concept: str
    label: str
    unit: str
    fy: int | None
    fp: str
    filed: date | None
    frame: str
    value: Decimal
    accession_number: str
    raw: Mapping[str, Any] = field(default_factory=dict)


class SecCompanyFactsClient:
    """Small official SEC companyfacts API client with conservative pacing."""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        request_delay: float = 0.25,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.request_delay = request_delay
        self.session.headers["User-Agent"] = DEFAULT_USER_AGENT
        self.session.headers["Accept-Encoding"] = "gzip, deflate"

    def get_companyfacts(self, cik: str) -> dict[str, Any]:
        return self._get_json(SEC_COMPANYFACTS_URL.format(cik=pad_cik(cik)))

    def useful_us_gaap_facts(
        self,
        cik: str,
        *,
        concepts: Iterable[str] = USEFUL_US_GAAP_CONCEPTS,
        forms: Iterable[str] = ("10-K", "10-Q"),
        limit: int = 500,
    ) -> list[SecCompanyFact]:
        payload = self.get_companyfacts(cik)
        return facts_from_companyfacts_payload(
            payload,
            concepts=concepts,
            forms=forms,
            limit=limit,
        )

    def _get_json(self, url: str) -> Any:
        sleep(self.request_delay)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


def ingest_sec_companyfacts_for_company(
    *,
    company: Any,
    financial_fact_model: Any,
    concepts: Iterable[str] = USEFUL_US_GAAP_CONCEPTS,
    forms: Iterable[str] = ("10-K", "10-Q"),
    limit: int = 500,
    client: SecCompanyFactsClient | None = None,
    job: Any | None = None,
) -> dict[str, int]:
    """Fetch useful SEC companyfacts and store them idempotently."""

    if not getattr(company, "sec_cik", ""):
        raise ValueError(f"{company} has no sec_cik")

    client = client or SecCompanyFactsClient()
    concepts = tuple(concept.strip() for concept in concepts if concept.strip())
    forms = tuple(form.strip().upper() for form in forms if form.strip())
    _mark_job_running(
        job,
        source="SEC_COMPANYFACTS",
        query=f"{company.sec_cik}: concepts={len(concepts)} forms={', '.join(forms)} limit={limit}",
    )
    try:
        facts = client.useful_us_gaap_facts(
            company.sec_cik,
            concepts=concepts,
            forms=forms,
            limit=limit,
        )
        counters = store_financial_facts(
            company=company,
            facts=facts,
            financial_fact_model=financial_fact_model,
        )
    except Exception as exc:
        _mark_job_failed(job, exc)
        raise

    _mark_job_counters(job, counters)
    _mark_job_succeeded(job)
    return counters


def store_financial_facts(
    *,
    company: Any,
    facts: Iterable[SecCompanyFact],
    financial_fact_model: Any,
) -> dict[str, int]:
    counters = {
        "facts_found": 0,
        "facts_inserted": 0,
        "facts_updated": 0,
        "duplicates_skipped": 0,
    }
    for fact in facts:
        counters["facts_found"] += 1
        lookup = {
            "company": company,
            "taxonomy": fact.taxonomy,
            "concept": fact.concept,
            "unit": fact.unit,
            "fy": fact.fy,
            "fp": fact.fp,
            "filed": fact.filed,
            "frame": fact.frame,
            "accession_number": fact.accession_number,
        }
        defaults = {
            "label": fact.label,
            "value": fact.value,
            "raw": dict(fact.raw),
        }
        obj, created = financial_fact_model.objects.get_or_create(
            **lookup,
            defaults=defaults,
        )
        if created:
            counters["facts_inserted"] += 1
        elif _fact_matches(obj, fact):
            counters["duplicates_skipped"] += 1
        else:
            for key, value in defaults.items():
                setattr(obj, key, value)
            obj.save(update_fields=list(defaults.keys()))
            counters["facts_updated"] += 1
    return counters


def facts_from_companyfacts_payload(
    payload: Mapping[str, Any],
    *,
    concepts: Iterable[str] = USEFUL_US_GAAP_CONCEPTS,
    forms: Iterable[str] = ("10-K", "10-Q"),
    limit: int = 500,
) -> list[SecCompanyFact]:
    wanted_concepts = set(concepts)
    wanted_forms = {form.upper() for form in forms}
    facts: list[SecCompanyFact] = []
    us_gaap = payload.get("facts", {}).get("us-gaap", {})

    for concept in wanted_concepts:
        concept_payload = us_gaap.get(concept)
        if not concept_payload:
            continue
        label = str(concept_payload.get("label") or concept)
        for unit, unit_facts in concept_payload.get("units", {}).items():
            for unit_fact in unit_facts:
                if wanted_forms and str(unit_fact.get("form", "")).upper() not in wanted_forms:
                    continue
                parsed = _fact_from_unit_payload(
                    taxonomy="us-gaap",
                    concept=concept,
                    label=label,
                    unit=str(unit),
                    unit_fact=unit_fact,
                )
                if parsed is not None:
                    facts.append(parsed)

    facts.sort(key=_fact_sort_key, reverse=True)
    return facts[:limit]


def pad_cik(value: Any) -> str:
    return str(value or "").strip().lstrip("0").zfill(10)


def parse_sec_date(value: Any) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value))


def _fact_from_unit_payload(
    *,
    taxonomy: str,
    concept: str,
    label: str,
    unit: str,
    unit_fact: Mapping[str, Any],
) -> SecCompanyFact | None:
    accession_number = str(unit_fact.get("accn") or "")
    value = _parse_decimal(unit_fact.get("val"))
    if not accession_number or value is None:
        return None
    return SecCompanyFact(
        taxonomy=taxonomy,
        concept=concept,
        label=label,
        unit=unit,
        fy=_parse_int(unit_fact.get("fy")),
        fp=str(unit_fact.get("fp") or ""),
        filed=parse_sec_date(unit_fact.get("filed")),
        frame=str(unit_fact.get("frame") or ""),
        value=value,
        accession_number=accession_number,
        raw=dict(unit_fact),
    )


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _fact_sort_key(fact: SecCompanyFact) -> tuple[date, int, str, str]:
    return (
        fact.filed or date.min,
        fact.fy or 0,
        fact.fp,
        fact.concept,
    )


def _fact_matches(obj: Any, fact: SecCompanyFact) -> bool:
    return (
        getattr(obj, "label", None) == fact.label
        and getattr(obj, "value", None) == fact.value
        and getattr(obj, "raw", None) == dict(fact.raw)
    )


def _mark_job_running(job: Any | None, *, source: str, query: str) -> None:
    if job is None:
        return
    job.source = source
    job.query = query
    job.status = "RUNNING"
    job.started_at = datetime.now(timezone.utc)
    if hasattr(job, "save"):
        job.save()


def _mark_job_counters(job: Any | None, counters: Mapping[str, int]) -> None:
    if job is None:
        return
    job.sources_found = counters["facts_found"]
    job.sources_inserted = counters["facts_inserted"]
    job.duplicates_skipped = counters["duplicates_skipped"]
    if hasattr(job, "save"):
        job.save()


def _mark_job_succeeded(job: Any | None) -> None:
    if job is None:
        return
    job.status = "SUCCEEDED"
    job.finished_at = datetime.now(timezone.utc)
    if hasattr(job, "save"):
        job.save()


def _mark_job_failed(job: Any | None, exc: Exception) -> None:
    if job is None:
        return
    job.status = "FAILED"
    job.error_message = str(exc)
    job.finished_at = datetime.now(timezone.utc)
    if hasattr(job, "save"):
        job.save()

"""Framework-light Wikidata client and company metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Mapping

import requests


WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
ENTITY_PREFIX = "http://www.wikidata.org/entity/"
DEFAULT_USER_AGENT = "InfoDJ/0.1 (business-event-research; https://github.com/AjayanN/infoDJ)"


@dataclass(frozen=True)
class WikidataCompany:
    wikidata_id: str
    name: str
    description: str = ""
    aliases: tuple[str, ...] = ()
    website: str = ""
    country: str = ""
    industry: str = ""
    founded_date: date | None = None
    subsidiaries: tuple[str, ...] = ()
    brands: tuple[str, ...] = ()
    products: tuple[str, ...] = ()
    leadership: tuple[str, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)


class WikidataClient:
    """Small wrapper around Wikidata APIs with injectable HTTP session."""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        api_url: str = WIKIDATA_API_URL,
        timeout: float = 15.0,
        language: str = "en",
    ) -> None:
        self.session = session or requests.Session()
        self.api_url = api_url
        self.timeout = timeout
        self.language = language
        self.session.headers["User-Agent"] = DEFAULT_USER_AGENT

    def search_companies(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Search Wikidata entities for a company-like query."""

        payload = self._get(
            {
                "action": "wbsearchentities",
                "search": query,
                "language": self.language,
                "uselang": self.language,
                "format": "json",
                "limit": limit,
            }
        )
        return list(payload.get("search", []))

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        entities = self.get_entities([entity_id], props="labels|descriptions|aliases|claims")
        return entities.get(entity_id, {})

    def get_entities(self, entity_ids: list[str], *, props: str = "labels") -> dict[str, Any]:
        if not entity_ids:
            return {}
        payload = self._get(
            {
                "action": "wbgetentities",
                "ids": "|".join(entity_ids),
                "languages": self.language,
                "props": props,
                "format": "json",
            }
        )
        return dict(payload.get("entities", {}))

    def get_company_details(self, entity_id: str) -> WikidataCompany:
        entity = self.get_entity(entity_id)
        claim_labels = self._claim_entity_labels(entity)
        return normalize_company_entity(entity, claim_labels=claim_labels, language=self.language)

    def resolve_company(self, company_name: str) -> WikidataCompany | None:
        """Search by name and return normalized details for the first result."""

        results = self.search_companies(company_name, limit=5)
        if not results:
            return None
        return self.get_company_details(results[0]["id"])

    def _claim_entity_labels(self, entity: Mapping[str, Any]) -> dict[str, str]:
        ids = sorted(
            {
                claim_id
                for prop in ("P17", "P452", "P355", "P1056", "P1716", "P169")
                for claim_id in _claim_entity_ids(entity, prop)
            }
        )
        entities = self.get_entities(ids, props="labels")
        return {
            entity_id: _localized_value(claim_entity.get("labels", {}), self.language)
            for entity_id, claim_entity in entities.items()
        }

    def _get(self, params: Mapping[str, Any]) -> dict[str, Any]:
        response = self.session.get(self.api_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


def normalize_company_entity(
    entity: Mapping[str, Any],
    *,
    claim_labels: Mapping[str, str] | None = None,
    language: str = "en",
) -> WikidataCompany:
    """Normalize a Wikidata entity payload to MVP company metadata."""

    labels = entity.get("labels", {})
    descriptions = entity.get("descriptions", {})
    aliases = entity.get("aliases", {})
    claim_labels = claim_labels or {}

    country_ids = _claim_entity_ids(entity, "P17")
    industry_ids = _claim_entity_ids(entity, "P452")

    return WikidataCompany(
        wikidata_id=str(entity.get("id") or ""),
        name=_localized_value(labels, language),
        description=_localized_value(descriptions, language),
        aliases=tuple(
            alias.get("value", "")
            for alias in aliases.get(language, [])
            if alias.get("value")
        ),
        website=_claim_string(entity, "P856"),
        country=_first_label(country_ids, claim_labels),
        industry=_first_label(industry_ids, claim_labels),
        founded_date=_claim_date(entity, "P571"),
        subsidiaries=tuple(_labels_for_claim(entity, "P355", claim_labels)),
        brands=tuple(_labels_for_claim(entity, "P1716", claim_labels)),
        products=tuple(_labels_for_claim(entity, "P1056", claim_labels)),
        leadership=tuple(_labels_for_claim(entity, "P169", claim_labels)),
        raw=entity,
    )


def update_company_from_wikidata(
    company: Any,
    *,
    client: WikidataClient | None = None,
    entity_id: str | None = None,
    save: bool = True,
) -> Any:
    """Update a Django-model-like Company object from Wikidata metadata."""

    client = client or WikidataClient()
    wikidata_id = entity_id or getattr(company, "wikidata_id", "") or None
    details = client.get_company_details(wikidata_id) if wikidata_id else client.resolve_company(company.name)
    if details is None:
        raise LookupError(f"No Wikidata entity found for company {company.name!r}")

    return _apply_company_details(company, details, save=save)


def _apply_company_details(company: Any, details: WikidataCompany, *, save: bool) -> Any:

    company.wikidata_id = details.wikidata_id
    company.description = details.description or getattr(company, "description", "")
    company.website = details.website or getattr(company, "website", "")
    company.country = details.country or getattr(company, "country", "")
    company.industry = details.industry or getattr(company, "industry", "")
    company.founded_date = details.founded_date or getattr(company, "founded_date", None)
    if details.aliases:
        company.aliases = list(details.aliases)

    if save and hasattr(company, "save"):
        company.save()
    return company


def sync_company_metadata(
    company: Any,
    *,
    client: WikidataClient | None = None,
    job: Any | None = None,
    entity_id: str | None = None,
) -> Any:
    """Resolve and persist company metadata while updating a job-like object."""

    _mark_job_running(job, source="WIKIDATA")
    try:
        client = client or WikidataClient()
        wikidata_id = entity_id or getattr(company, "wikidata_id", "") or None
        details = client.get_company_details(wikidata_id) if wikidata_id else client.resolve_company(company.name)
        if details is None:
            raise LookupError(f"No Wikidata entity found for company {company.name!r}")
        updated_company = _apply_company_details(company, details, save=True)
        _persist_company_profile_snapshot(updated_company, details=details, client=client)
    except Exception as exc:
        _mark_job_failed(job, exc)
        raise

    _mark_job_succeeded(job)
    return updated_company


def _persist_company_profile_snapshot(
    company: Any,
    *,
    details: WikidataCompany,
    client: WikidataClient | None,
) -> None:
    """Persist the source-backed Company 360 foundation after Wikidata sync."""

    if not hasattr(company, "profile_snapshots") or not getattr(company, "wikidata_id", ""):
        return

    from apps.companies.models import CompanyProfileSnapshot, CompanyProfileStatus
    from apps.ingestion.models import SourceDocument
    from apps.ingestion.services.url_utils import url_hash

    entity_url = f"https://www.wikidata.org/wiki/{company.wikidata_id}"
    source, _created = SourceDocument.objects.update_or_create(
        url_hash=url_hash(entity_url),
        defaults={
            "company": company,
            "source_api": "WIKIDATA",
            "url": entity_url,
            "canonical_url": entity_url,
            "title": f"{company.name} - Wikidata",
            "publisher": "Wikidata",
            "snippet": company.description,
            "language": getattr(client, "language", "en") if client else "en",
            "status": "APPROVED",
        },
    )
    CompanyProfileSnapshot.objects.update_or_create(
        company=company,
        effective_date=date.today(),
        source_document=source,
        defaults={
            "status": CompanyProfileStatus.REVIEWED,
            "summary": company.description,
            "subsidiaries": list(details.subsidiaries),
            "brands": list(details.brands),
            "products": list(details.products),
            "geographies": [company.country] if company.country else [],
            "leadership": list(details.leadership),
            "evidence_text": company.description,
            "confidence_score": "0.650",
        },
    )


def _localized_value(values: Mapping[str, Any], language: str) -> str:
    value = values.get(language) or values.get("en") or {}
    return str(value.get("value") or "")


def _claim_entity_ids(entity: Mapping[str, Any], prop: str) -> list[str]:
    ids: list[str] = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = (
            claim.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
        )
        entity_id = value.get("id") if isinstance(value, Mapping) else None
        if entity_id:
            ids.append(str(entity_id))
    return ids


def _claim_string(entity: Mapping[str, Any], prop: str) -> str:
    claims = entity.get("claims", {}).get(prop, [])
    if not claims:
        return ""
    value = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
    return str(value or "")


def _claim_date(entity: Mapping[str, Any], prop: str) -> date | None:
    claims = entity.get("claims", {}).get(prop, [])
    if not claims:
        return None
    value = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
    raw_time = value.get("time", "") if isinstance(value, Mapping) else ""
    try:
        return date.fromisoformat(str(raw_time).lstrip("+")[:10])
    except ValueError:
        return None


def _labels_for_claim(entity: Mapping[str, Any], prop: str, labels: Mapping[str, str]) -> list[str]:
    return [labels[entity_id] for entity_id in _claim_entity_ids(entity, prop) if labels.get(entity_id)]


def _first_label(entity_ids: list[str], labels: Mapping[str, str]) -> str:
    for entity_id in entity_ids:
        if labels.get(entity_id):
            return labels[entity_id]
    return ""


def _mark_job_running(job: Any | None, *, source: str) -> None:
    if job is None:
        return
    job.source = source
    job.status = "RUNNING"
    job.started_at = datetime.now(timezone.utc)
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

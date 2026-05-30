"""GDELT DOC 2.0 source discovery client and source persistence helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from time import sleep
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

import requests
from requests import HTTPError, RequestException

from .url_utils import find_duplicate_source, source_identity_values


GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_USER_AGENT = "InfoDJ/0.1 (business-event-research; https://github.com/AjayanN/infoDJ)"


@dataclass(frozen=True)
class GDELTArticle:
    title: str
    url: str
    publisher: str
    published_date: datetime | None
    snippet: str = ""
    language: str = ""
    source_api: str = "GDELT_DOC_2"
    raw: Mapping[str, Any] = field(default_factory=dict)

    def to_source_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(source_identity_values(data))
        return data


class GDELTClient:
    """Small GDELT DOC 2.0 client with injectable HTTP session."""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        api_url: str = GDELT_DOC_API_URL,
        timeout: float = 20.0,
        retries: int = 3,
        retry_delay: float = 8.0,
    ) -> None:
        self.session = session or requests.Session()
        self.api_url = api_url
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.session.headers["User-Agent"] = DEFAULT_USER_AGENT

    def search_articles(
        self,
        query: str,
        *,
        max_records: int = 25,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        sort: str = "HybridRel",
    ) -> list[GDELTArticle]:
        """Query GDELT DOC 2.0 in ArtList JSON mode."""

        params: dict[str, Any] = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": max(1, min(max_records, 250)),
            "sort": sort,
        }
        if start_datetime:
            params["startdatetime"] = _gdelt_datetime(start_datetime)
        if end_datetime:
            params["enddatetime"] = _gdelt_datetime(end_datetime)

        response = self._get(params)
        response.raise_for_status()
        payload = response.json()
        return [normalize_article(article) for article in payload.get("articles", [])]

    def _get(self, params: Mapping[str, Any]) -> requests.Response:
        last_response: requests.Response | None = None
        for attempt in range(self.retries + 1):
            response = self.session.get(self.api_url, params=params, timeout=self.timeout)
            if response.status_code != 429:
                return response
            last_response = response
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else self.retry_delay * (attempt + 1)
            sleep(delay)
        return last_response


def normalize_article(article: Mapping[str, Any]) -> GDELTArticle:
    url = str(article.get("url") or "")
    publisher = str(article.get("domain") or urlsplit(url).netloc.replace("www.", ""))
    return GDELTArticle(
        title=str(article.get("title") or ""),
        url=url,
        publisher=publisher,
        published_date=_parse_gdelt_seen_date(article.get("seendate")),
        snippet=str(article.get("snippet") or article.get("summary") or ""),
        language=str(article.get("language") or ""),
        raw=article,
    )


def collect_sources(
    queries: Iterable[str],
    *,
    client: GDELTClient | None = None,
    max_records_per_query: int = 25,
    query_delay: float = 2.0,
    allowed_languages: Iterable[str] | None = None,
    skip_failed_queries: bool = True,
) -> list[dict[str, Any]]:
    """Collect normalized source metadata without fetching article bodies."""

    client = client or GDELTClient()
    allowed_language_set = {
        language.strip().lower()
        for language in (allowed_languages or [])
        if language.strip()
    }
    sources: list[dict[str, Any]] = []
    seen_url_hashes: set[str] = set()
    for index, query in enumerate(queries):
        if index:
            sleep(query_delay)
        try:
            articles = client.search_articles(query, max_records=max_records_per_query)
        except (HTTPError, RequestException):
            if skip_failed_queries:
                continue
            raise
        for article in articles:
            if allowed_language_set and article.language.strip().lower() not in allowed_language_set:
                continue
            source = article.to_source_dict()
            if source["url_hash"] in seen_url_hashes:
                continue
            seen_url_hashes.add(source["url_hash"])
            sources.append(source)
    return sources


def store_source_documents(
    *,
    company: Any,
    sources: Iterable[Mapping[str, Any]],
    source_document_model: Any,
    existing_sources: Iterable[Any] | None = None,
    job: Any | None = None,
) -> dict[str, int]:
    """Persist normalized source metadata using a Django-model-like class."""

    counters = {"sources_found": 0, "sources_inserted": 0, "duplicates_skipped": 0}
    existing = list(existing_sources or _default_existing_sources(company))

    for source in sources:
        counters["sources_found"] += 1
        duplicate = find_duplicate_source(source, existing, company=company)
        if duplicate is not None and duplicate.reason == "url_hash":
            counters["duplicates_skipped"] += 1
            continue

        document = source_document_model(
            company=company,
            source_api=source.get("source_api", "GDELT_DOC_2"),
            url=source.get("url", ""),
            canonical_url=source.get("canonical_url", ""),
            title=source.get("title", ""),
            publisher=source.get("publisher", ""),
            published_date=source.get("published_date"),
            snippet=source.get("snippet", ""),
            language=source.get("language", ""),
            url_hash=source.get("url_hash", ""),
            title_hash=source.get("title_hash", ""),
            status="DUPLICATE" if duplicate is not None else "DISCOVERED",
        )
        if duplicate is not None:
            document.duplicate_of = duplicate.document
        if hasattr(document, "save"):
            document.save()
        existing.append(document)
        counters["sources_inserted"] += 1

    if job is not None:
        for key, value in counters.items():
            setattr(job, key, value)
        if hasattr(job, "save"):
            job.save()

    return counters


def discover_and_store_sources(
    *,
    company: Any,
    queries: Iterable[str],
    source_document_model: Any,
    client: GDELTClient | None = None,
    existing_sources: Iterable[Any] | None = None,
    job: Any | None = None,
    max_records_per_query: int = 25,
    query_delay: float = 2.0,
    allowed_languages: Iterable[str] | None = None,
    skip_failed_queries: bool = True,
) -> dict[str, int]:
    sources = collect_sources(
        queries,
        client=client,
        max_records_per_query=max_records_per_query,
        query_delay=query_delay,
        allowed_languages=allowed_languages,
        skip_failed_queries=skip_failed_queries,
    )
    return store_source_documents(
        company=company,
        sources=sources,
        source_document_model=source_document_model,
        existing_sources=existing_sources,
        job=job,
    )


def discover_sources_for_company(
    *,
    company: Any,
    queries: Iterable[str],
    source_document_model: Any,
    client: GDELTClient | None = None,
    existing_sources: Iterable[Any] | None = None,
    job: Any | None = None,
    max_records_per_query: int = 25,
    query_delay: float = 2.0,
    allowed_languages: Iterable[str] | None = ("English",),
    skip_failed_queries: bool = True,
) -> dict[str, int]:
    """Run GDELT source discovery with job status and counter updates."""

    query_list = list(queries)
    _mark_job_running(job, source="GDELT_DOC_2", query="\n".join(query_list))
    try:
        counters = discover_and_store_sources(
            company=company,
            queries=query_list,
            source_document_model=source_document_model,
            client=client,
            existing_sources=existing_sources,
            job=job,
            max_records_per_query=max_records_per_query,
            query_delay=query_delay,
            allowed_languages=allowed_languages,
            skip_failed_queries=skip_failed_queries,
        )
    except Exception as exc:
        _mark_job_failed(job, exc)
        raise

    _mark_job_succeeded(job)
    return counters


def _parse_gdelt_seen_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _gdelt_datetime(value: datetime) -> str:
    return value.strftime("%Y%m%d%H%M%S")


def _default_existing_sources(company: Any) -> Iterable[Any]:
    manager = getattr(company, "source_documents", None)
    if manager is None or not hasattr(manager, "all"):
        return []
    return manager.all()


def _mark_job_running(job: Any | None, *, source: str, query: str) -> None:
    if job is None:
        return
    job.source = source
    job.query = query
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

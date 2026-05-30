"""Wikipedia page and citation discovery via MediaWiki API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

import requests

from .url_utils import source_identity_values


WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
DEFAULT_USER_AGENT = "InfoDJ/0.1 business-event-research contact local-dev@example.com"


@dataclass(frozen=True)
class WikipediaSource:
    title: str
    url: str
    publisher: str
    snippet: str = ""
    source_api: str = "WIKIPEDIA_REFERENCES"
    language: str = "English"

    def to_source_dict(self) -> dict[str, Any]:
        data = {
            "source_api": self.source_api,
            "url": self.url,
            "title": self.title,
            "publisher": self.publisher,
            "published_date": datetime.now(timezone.utc),
            "snippet": self.snippet,
            "language": self.language,
        }
        data.update(source_identity_values(data))
        return data


class WikipediaClient:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        api_url: str = WIKIPEDIA_API_URL,
        timeout: float = 20.0,
    ) -> None:
        self.session = session or requests.Session()
        self.api_url = api_url
        self.timeout = timeout
        self.session.headers["User-Agent"] = DEFAULT_USER_AGENT

    def search_page_title(self, query: str) -> str | None:
        payload = self._get(
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "format": "json",
            }
        )
        rows = payload.get("query", {}).get("search", [])
        if not rows:
            return None
        return str(rows[0].get("title") or "")

    def page_extract(self, title: str) -> str:
        payload = self._get(
            {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "titles": title,
                "format": "json",
            }
        )
        pages = payload.get("query", {}).get("pages", {})
        for page in pages.values():
            return str(page.get("extract") or "")
        return ""

    def external_links(self, title: str, *, limit: int = 100) -> list[str]:
        links: list[str] = []
        params: dict[str, Any] = {
            "action": "query",
            "prop": "extlinks",
            "titles": title,
            "ellimit": min(limit, 500),
            "format": "json",
        }
        while True:
            payload = self._get(params)
            pages = payload.get("query", {}).get("pages", {})
            for page in pages.values():
                for link in page.get("extlinks", []):
                    url = link.get("*") or link.get("url")
                    if url:
                        links.append(str(url))
                        if len(links) >= limit:
                            return links
            cont = payload.get("continue")
            if not cont:
                return links
            params.update(cont)

    def discover_sources(self, company_name: str, *, limit: int = 100) -> list[WikipediaSource]:
        title = self.search_page_title(company_name) or company_name
        extract = self.page_extract(title)
        sources = [
            WikipediaSource(
                title=f"Wikipedia page: {title}",
                url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                publisher="Wikipedia",
                snippet=extract[:1000],
                source_api="WIKIPEDIA_PAGE",
            )
        ]
        for url in self.external_links(title, limit=limit):
            if should_skip_external_link(url):
                continue
            sources.append(
                WikipediaSource(
                    title=f"Wikipedia reference for {title}",
                    url=url,
                    publisher=domain(url),
                    snippet=f"External reference linked from Wikipedia page {title}.",
                )
            )
        return sources

    def _get(self, params: Mapping[str, Any]) -> dict[str, Any]:
        response = self.session.get(self.api_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


def store_wikipedia_sources(
    *,
    company: Any,
    sources: Iterable[WikipediaSource],
    source_document_model: Any,
) -> dict[str, int]:
    counters = {"sources_found": 0, "sources_inserted": 0, "duplicates_skipped": 0}
    for source_item in sources:
        source = source_item.to_source_dict()
        counters["sources_found"] += 1
        _, created = source_document_model.objects.get_or_create(
            url_hash=source["url_hash"],
            defaults={
                "company": company,
                "source_api": source["source_api"],
                "url": source["url"],
                "canonical_url": source["canonical_url"],
                "title": source["title"],
                "publisher": source["publisher"],
                "published_date": source["published_date"],
                "snippet": source["snippet"],
                "language": source["language"],
                "title_hash": source["title_hash"],
                "status": "DISCOVERED",
            },
        )
        if created:
            counters["sources_inserted"] += 1
        else:
            counters["duplicates_skipped"] += 1
    return counters


def should_skip_external_link(url: str) -> bool:
    host = domain(url)
    skip_hosts = ("web.archive.org", "archive.today", "archive.is")
    return not url.startswith(("http://", "https://")) or host in skip_hosts


def domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")

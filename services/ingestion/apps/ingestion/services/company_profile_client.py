from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from apps.companies.models import CompanyProfileSnapshot, CompanyProfileStatus
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.url_utils import url_hash
from apps.ingestion.services.wikidata_client import DEFAULT_USER_AGENT


@dataclass(frozen=True)
class OfficialProfileData:
    summary: str
    brands: tuple[str, ...]
    products: tuple[str, ...]
    geographies: tuple[str, ...]
    evidence_text: str


def parse_official_profile_html(html: str) -> OfficialProfileData:
    soup = BeautifulSoup(html, "html.parser")
    organizations: list[dict[str, Any]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or script.get_text() or "{}")
        except (TypeError, ValueError):
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") in {"Organization", "Corporation"}:
                organizations.append(candidate)

    organization = organizations[0] if organizations else {}
    summary = clean_text(organization.get("description"))
    if not summary:
        description = soup.select_one('meta[name="description"]') or soup.select_one('meta[property="og:description"]')
        summary = clean_text(description.get("content")) if description else ""

    brands = normalized_names(organization.get("brand"))
    products = normalized_offers(organization.get("makesOffer"))
    geographies = normalized_names(organization.get("areaServed"))
    evidence = summary or clean_text(soup.title.string if soup.title else "")
    return OfficialProfileData(summary, tuple(brands), tuple(products), tuple(geographies), evidence)


def collect_official_company_profile(company, *, session: requests.Session | None = None) -> CompanyProfileSnapshot:
    if not company.website:
        raise ValueError(f"{company.name} has no official website")

    session = session or requests.Session()
    session.headers["User-Agent"] = DEFAULT_USER_AGENT
    if not robots_allows(company.website, session=session):
        raise PermissionError(f"robots.txt does not allow Company 360 collection for {company.website}")

    response = session.get(company.website, timeout=20)
    response.raise_for_status()
    data = parse_official_profile_html(response.text)
    canonical_url = response.url or company.website
    source, _created = SourceDocument.objects.update_or_create(
        url_hash=url_hash(canonical_url),
        defaults={
            "company": company,
            "source_api": "OFFICIAL_WEBSITE",
            "url": canonical_url,
            "canonical_url": canonical_url,
            "title": clean_text(BeautifulSoup(response.text, "html.parser").title.string) if BeautifulSoup(response.text, "html.parser").title else f"{company.name} official website",
            "publisher": company.name,
            "snippet": data.summary,
            "language": "en",
            "status": "APPROVED",
        },
    )
    snapshot, _created = CompanyProfileSnapshot.objects.update_or_create(
        company=company,
        effective_date=date.today(),
        source_document=source,
        defaults={
            "status": CompanyProfileStatus.DRAFT,
            "summary": data.summary,
            "brands": list(data.brands),
            "products": list(data.products),
            "geographies": list(data.geographies),
            "evidence_text": data.evidence_text,
            "confidence_score": "0.600",
        },
    )
    return snapshot


def robots_allows(url: str, *, session: requests.Session) -> bool:
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    response = session.get(robots_url, timeout=10)
    if response.status_code == 404:
        return True
    response.raise_for_status()
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    return parser.can_fetch(DEFAULT_USER_AGENT, url)


def normalized_names(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    names = []
    for item in values:
        name = item.get("name") if isinstance(item, dict) else item
        normalized = clean_text(name)
        if normalized and normalized not in names:
            names.append(normalized)
    return names


def normalized_offers(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    products = []
    for item in values:
        offered = item.get("itemOffered", item) if isinstance(item, dict) else item
        name = offered.get("name") if isinstance(offered, dict) else offered
        normalized = clean_text(name)
        if normalized and normalized not in products:
            products.append(normalized)
    return products


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())

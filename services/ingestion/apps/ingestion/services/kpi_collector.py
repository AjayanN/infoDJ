from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import StringIO

import requests
from bs4 import BeautifulSoup

from apps.companies.models import KpiDefinition, KpiObservation
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_client import robots_allows
from apps.ingestion.services.url_utils import url_hash
from apps.ingestion.services.wikidata_client import DEFAULT_USER_AGENT


def collect_kpi_csv(company, *, url: str, metric_slug: str, metric_name: str, unit: str, session=None, check_robots=True):
    session = session or requests.Session()
    session.headers["User-Agent"] = DEFAULT_USER_AGENT
    if check_robots and not robots_allows(url, session=session):
        raise PermissionError(f"robots.txt does not allow KPI collection for {url}")
    response = session.get(url, timeout=20)
    response.raise_for_status()
    source, _created = SourceDocument.objects.update_or_create(
        url_hash=url_hash(response.url or url),
        defaults={
            "company": company, "source_api": "OFFICIAL_SPREADSHEET", "url": response.url or url,
            "canonical_url": response.url or url, "title": f"{company.name} {metric_name} data",
            "publisher": company.name, "snippet": "Structured KPI table collected for analyst review.",
            "language": "en", "status": "APPROVED",
        },
    )
    kpi, _created = KpiDefinition.objects.update_or_create(
        company=company, slug=metric_slug,
        defaults={
            "name": metric_name, "description": "Imported from a structured official table; definition review required.",
            "unit": unit, "cadence": "QUARTERLY", "value_type": "REPORTED", "is_active": False,
        },
    )
    count = 0
    for row in csv.DictReader(StringIO(response.text)):
        period_end = date.fromisoformat(row["period_end"])
        KpiObservation.objects.update_or_create(
            kpi=kpi, period_end=period_end, segment=(row.get("segment") or "").strip(),
            geography=(row.get("geography") or "").strip(),
            defaults={
                "period_start": date.fromisoformat(row.get("period_start") or row["period_end"]),
                "fiscal_year": int(row.get("fiscal_year") or period_end.year),
                "fiscal_period": (row.get("fiscal_period") or "").strip(), "value": Decimal(row["value"]),
                "source_document": source, "evidence_text": "Imported from structured official table; analyst review required.",
                "is_non_comparable": True, "confidence_score": Decimal("0.500"),
            },
        )
        count += 1
    return kpi, count


def collect_kpi_html_table(company, *, url: str, metric_slug: str, metric_name: str, unit: str, session=None):
    session = session or requests.Session()
    session.headers["User-Agent"] = DEFAULT_USER_AGENT
    if not robots_allows(url, session=session):
        raise PermissionError(f"robots.txt does not allow KPI collection for {url}")
    response = session.get(url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("no HTML table found")
    headers = [cell.get_text(" ", strip=True).lower().replace(" ", "_") for cell in table.find_all("th")]
    required = {"period_end", "value"}
    if not required.issubset(headers):
        raise ValueError("HTML table must include period_end and value headers")
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, [cell.get_text(" ", strip=True) for cell in cells])))
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)

    class HtmlTableResponse:
        def raise_for_status(self):
            return None

    class HtmlTableSession:
        def get(self, _url, timeout=20):
            return table_response

    table_response = HtmlTableResponse()
    table_response.text = csv_buffer.getvalue()
    table_response.url = response.url
    table_session = HtmlTableSession()
    table_session.headers = session.headers

    return collect_kpi_csv(
        company, url=response.url or url, metric_slug=metric_slug, metric_name=metric_name,
        unit=unit, session=table_session, check_robots=False,
    )

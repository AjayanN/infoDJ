"""SEC EDGAR company lookup and filing metadata ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
import socket
from time import sleep
from typing import Any, Iterable, Mapping

import requests
import urllib3.util.connection as urllib3_connection

from .url_utils import source_identity_values


SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data"
DEFAULT_USER_AGENT = "InfoDJ/0.1 business-event-research contact local-dev@example.com"


def _allowed_gai_family() -> socket.AddressFamily:
    return socket.AF_INET


urllib3_connection.allowed_gai_family = _allowed_gai_family


@dataclass(frozen=True)
class EdgarCompany:
    cik: str
    ticker: str
    title: str


@dataclass(frozen=True)
class EdgarFiling:
    cik: str
    company_name: str
    accession_number: str
    filing_date: date | None
    report_date: date | None
    form: str
    primary_document: str
    description: str = ""
    source_api: str = "SEC_EDGAR"
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        accession_no_dashes = self.accession_number.replace("-", "")
        return (
            f"{SEC_ARCHIVES_BASE_URL}/{int(self.cik)}/"
            f"{accession_no_dashes}/{self.primary_document}"
        )

    @property
    def published_date(self) -> datetime | None:
        if self.filing_date is None:
            return None
        return datetime.combine(self.filing_date, time.min, tzinfo=timezone.utc)

    @property
    def title(self) -> str:
        description = f" - {self.description}" if self.description else ""
        return f"{self.company_name} {self.form} filing {self.filing_date or 'unknown date'}{description}"

    def to_source_dict(self) -> dict[str, Any]:
        data = {
            "source_api": self.source_api,
            "url": self.url,
            "title": self.title,
            "publisher": "SEC EDGAR",
            "published_date": self.published_date,
            "snippet": (
                f"SEC EDGAR {self.form} filing for {self.company_name}. "
                f"Accession number: {self.accession_number}. "
                f"Report date: {self.report_date or 'unknown'}."
            ),
            "language": "English",
            "raw": self.raw,
        }
        data.update(source_identity_values(data))
        return data


class SecEdgarClient:
    """Small official SEC EDGAR data API client with conservative pacing."""

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

    def lookup_company_by_ticker(self, ticker: str) -> EdgarCompany | None:
        rows = self._get_json(SEC_COMPANY_TICKERS_URL)
        ticker_upper = ticker.strip().upper()
        for row in rows.values():
            if str(row.get("ticker", "")).upper() == ticker_upper:
                return EdgarCompany(
                    cik=pad_cik(row.get("cik_str")),
                    ticker=str(row.get("ticker", "")),
                    title=str(row.get("title", "")),
                )
        return None

    def get_submissions(self, cik: str) -> dict[str, Any]:
        return self._get_json(SEC_SUBMISSIONS_URL.format(cik=pad_cik(cik)))

    def recent_filings(
        self,
        cik: str,
        *,
        company_name: str = "Company",
        forms: Iterable[str] = ("10-K", "10-Q", "8-K"),
        limit: int = 25,
    ) -> list[EdgarFiling]:
        payload = self.get_submissions(cik)
        recent = payload.get("filings", {}).get("recent", {})
        return filings_from_recent_payload(
            recent,
            cik=pad_cik(cik),
            company_name=company_name,
            forms=forms,
            limit=limit,
        )

    def all_filings(
        self,
        cik: str,
        *,
        company_name: str = "Company",
        forms: Iterable[str] = ("10-K", "10-Q", "8-K", "S-1", "S-1/A"),
        limit: int = 250,
    ) -> list[EdgarFiling]:
        payload = self.get_submissions(cik)
        filings = filings_from_recent_payload(
            payload.get("filings", {}).get("recent", {}),
            cik=pad_cik(cik),
            company_name=company_name,
            forms=forms,
            limit=limit,
        )

        for file_info in payload.get("filings", {}).get("files", []):
            if len(filings) >= limit:
                break
            name = file_info.get("name")
            if not name:
                continue
            older_payload = self._get_json(f"https://data.sec.gov/submissions/{name}")
            filings.extend(
                filings_from_recent_payload(
                    older_payload,
                    cik=pad_cik(cik),
                    company_name=company_name,
                    forms=forms,
                    limit=limit - len(filings),
                )
            )
        return filings[:limit]

    def _get_json(self, url: str) -> Any:
        sleep(self.request_delay)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


def discover_sec_filings_for_company(
    *,
    company: Any,
    source_document_model: Any,
    ticker: str = "NFLX",
    forms: Iterable[str] = ("10-K", "10-Q", "8-K"),
    limit: int = 25,
    full_history: bool = False,
    client: SecEdgarClient | None = None,
    job: Any | None = None,
) -> dict[str, int]:
    """Resolve CIK and store recent SEC filing metadata as source documents."""

    client = client or SecEdgarClient()
    _mark_job_running(job, source="SEC_EDGAR", query=f"{ticker}: {', '.join(forms)}")
    try:
        edgar_company = client.lookup_company_by_ticker(ticker)
        if edgar_company is None:
            raise LookupError(f"No SEC company found for ticker {ticker!r}")
        company.sec_cik = edgar_company.cik
        if hasattr(company, "save"):
            company.save(update_fields=["sec_cik", "updated_at"])
        filing_loader = client.all_filings if full_history else client.recent_filings
        filings = filing_loader(
            edgar_company.cik,
            company_name=company.name,
            forms=forms,
            limit=limit,
        )
        counters = store_sec_source_documents(
            company=company,
            filings=filings,
            source_document_model=source_document_model,
        )
    except Exception as exc:
        _mark_job_failed(job, exc)
        raise
    if job is not None:
        for key, value in counters.items():
            setattr(job, key, value)
    _mark_job_succeeded(job)
    return counters


def store_sec_source_documents(
    *,
    company: Any,
    filings: Iterable[EdgarFiling],
    source_document_model: Any,
) -> dict[str, int]:
    counters = {"sources_found": 0, "sources_inserted": 0, "duplicates_skipped": 0}
    for filing in filings:
        source = filing.to_source_dict()
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


def filings_from_recent_payload(
    recent: Mapping[str, list[Any]],
    *,
    cik: str,
    company_name: str,
    forms: Iterable[str],
    limit: int,
) -> list[EdgarFiling]:
    wanted_forms = {form.upper() for form in forms}
    filings: list[EdgarFiling] = []
    for index, form in enumerate(recent.get("form", [])):
        if str(form).upper() not in wanted_forms:
            continue
        filing = EdgarFiling(
            cik=pad_cik(cik),
            company_name=company_name,
            accession_number=str(recent.get("accessionNumber", [])[index]),
            filing_date=parse_sec_date(recent.get("filingDate", [None])[index]),
            report_date=parse_sec_date(recent.get("reportDate", [None])[index]),
            form=str(form),
            primary_document=str(recent.get("primaryDocument", [""])[index]),
            description=str(recent.get("primaryDocDescription", [""])[index] or ""),
            raw={key: values[index] for key, values in recent.items() if index < len(values)},
        )
        if filing.primary_document:
            filings.append(filing)
        if len(filings) >= limit:
            break
    return filings


def pad_cik(value: Any) -> str:
    return str(value or "").strip().lstrip("0").zfill(10)


def parse_sec_date(value: Any) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value))


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

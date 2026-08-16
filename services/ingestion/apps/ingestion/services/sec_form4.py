"""Parse and persist SEC ownership-form transactions with filing provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from time import sleep
from typing import Iterable
from xml.etree import ElementTree

import requests
from django.utils import timezone

from apps.companies.models import Company, CompanyProfileStatus, InsiderTransaction, InsiderTransactionType, OwnershipInsiderSnapshot
from apps.ingestion.models import SourceDocument


SEC_USER_AGENT = "InfoDJ/0.1 business-event-research contact local-dev@example.com"
OWNERSHIP_FORMS = ("3", "3/A", "4", "4/A", "5", "5/A")
SEC_REQUEST_DELAY = 0.25


@dataclass(frozen=True)
class Form4Transaction:
    insider_name: str
    insider_role: str
    transaction_type: str
    transaction_date: date | None
    transaction_code: str
    shares: Decimal | None
    price: Decimal | None
    ownership_after: Decimal | None
    planned_sale: bool
    plan_reference: str

    @property
    def value(self) -> Decimal | None:
        if self.shares is None or self.price is None:
            return None
        return self.shares * self.price


def parse_ownership_xml(xml_text: str) -> list[Form4Transaction]:
    """Parse non-derivative Form 3/4/5 transactions without inferring omissions."""

    root = ElementTree.fromstring(xml_text)
    if local_name(root.tag) != "ownershipDocument":
        raise ValueError("SEC filing response is not an ownership XML document.")
    owner_name = text_at(root, "reportingOwner/reportingOwnerId/rptOwnerName")
    role = owner_role(root)
    footnotes = {
        node.attrib.get("id", ""): clean_text(node.text or "")
        for node in root.iter()
        if local_name(node.tag) == "footnote" and node.attrib.get("id")
    }
    rows: list[Form4Transaction] = []
    form_plan_flag = text_at(root, "aff10b5One") in {"1", "true", "True"}
    for node in root.iter():
        if local_name(node.tag) not in {"nonDerivativeTransaction", "derivativeTransaction"}:
            continue
        code = text_at(node, "transactionCoding/transactionCode").upper()
        shares = decimal_at(node, "transactionAmounts/transactionShares/value")
        price = decimal_at(node, "transactionAmounts/transactionPricePerShare/value")
        reference_ids = footnote_ids(node)
        references = " ".join(footnotes[item] for item in reference_ids if item in footnotes)
        rows.append(
            Form4Transaction(
                insider_name=owner_name[:255] or "Undisclosed reporting owner",
                insider_role=role[:255],
                transaction_type=transaction_type(code, text_at(node, "transactionAmounts/transactionAcquiredDisposedCode/value")),
                transaction_date=date_at(node, "transactionDate/value"),
                transaction_code=code[:16],
                shares=shares,
                price=price,
                ownership_after=decimal_at(node, "postTransactionAmounts/sharesOwnedFollowingTransaction/value"),
                planned_sale=form_plan_flag or "10b5-1" in references.lower(),
                plan_reference=(references or "Issuer marked this filing as Rule 10b5-1 planned.")[:255]
                if form_plan_flag or "10b5-1" in references.lower()
                else "",
            )
        )
    return rows


def ingest_form4_sources(
    *,
    company: Company,
    sources: Iterable[SourceDocument],
    session: requests.Session | None = None,
    timeout: float = 20.0,
    request_delay: float = SEC_REQUEST_DELAY,
) -> dict[str, int]:
    """Fetch Form 3/4/5 XML already discovered in EDGAR and upsert transactions."""

    session = session or requests.Session()
    session.headers.update({"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    counters = {"sources_seen": 0, "sources_parsed": 0, "sources_failed": 0, "transactions_found": 0, "transactions_inserted": 0, "transactions_updated": 0}
    for source in sources:
        counters["sources_seen"] += 1
        try:
            transactions = parse_ownership_response(session, ownership_xml_url(source.url), timeout=timeout, request_delay=request_delay)
        except (requests.RequestException, ElementTree.ParseError, ValueError):
            try:
                transactions = parse_ownership_fallback(session, source.url, timeout=timeout, request_delay=request_delay)
            except (requests.RequestException, ElementTree.ParseError, ValueError):
                counters["sources_failed"] += 1
                continue
        counters["sources_parsed"] += 1
        snapshot = snapshot_for_source(company, source)
        accession = accession_from_url(source.url)
        for transaction in transactions:
            counters["transactions_found"] += 1
            _, created = InsiderTransaction.objects.update_or_create(
                snapshot=snapshot,
                insider_name=transaction.insider_name,
                transaction_type=transaction.transaction_type,
                transaction_date=transaction.transaction_date,
                filing_accession_number=accession,
                transaction_code=transaction.transaction_code,
                shares=transaction.shares,
                price=transaction.price,
                defaults={
                    "insider_role": transaction.insider_role,
                    "value": transaction.value,
                    "planned_sale": transaction.planned_sale,
                    "plan_reference": transaction.plan_reference,
                    "ownership_after": transaction.ownership_after,
                    "evidence_text": evidence_text(transaction, source),
                    "source_document": source,
                    "confidence_score": "0.980",
                    "review_status": "REVIEWED",
                },
            )
            counters["transactions_inserted" if created else "transactions_updated"] += 1
    return counters


def form4_sources(company: Company, *, limit: int = 250) -> list[SourceDocument]:
    """Return recently filed ownership forms from existing SEC source discovery."""

    queryset = SourceDocument.objects.filter(company=company, source_api="SEC_EDGAR")
    form_pattern = r"\s(?:3|3/A|4|4/A|5|5/A) filing\s"
    return list(queryset.filter(title__regex=form_pattern).order_by("-published_date", "-id")[:limit])


def snapshot_for_source(company: Company, source: SourceDocument) -> OwnershipInsiderSnapshot:
    effective_date = source.published_date.date() if source.published_date else timezone.localdate()
    snapshot, _ = OwnershipInsiderSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": "SEC ownership-form activity reported on this filing date.",
            "methodology": "Transactions are parsed from SEC Forms 3, 4, and 5 XML. Values are reported, not estimated.",
            "confidence_score": "0.980",
        },
    )
    return snapshot


def transaction_type(code: str, acquired_disposed: str) -> str:
    if code == "P":
        return InsiderTransactionType.PURCHASE
    if code == "S":
        return InsiderTransactionType.SALE
    if code in {"M", "C"}:
        return InsiderTransactionType.EXERCISE
    if code in {"A", "G"}:
        return InsiderTransactionType.GRANT
    if acquired_disposed.upper() == "A":
        return InsiderTransactionType.GRANT
    return InsiderTransactionType.OTHER


def owner_role(root: ElementTree.Element) -> str:
    relationship = find_path(root, "reportingOwner/reportingOwnerRelationship")
    if relationship is None:
        return ""
    roles = []
    if text_at(relationship, "isDirector") == "1":
        roles.append("Director")
    if text_at(relationship, "isOfficer") == "1":
        title = text_at(relationship, "officerTitle")
        roles.append(title or "Officer")
    if text_at(relationship, "isTenPercentOwner") == "1":
        roles.append("10% owner")
    return "; ".join(roles)


def evidence_text(transaction: Form4Transaction, source: SourceDocument) -> str:
    details = [f"SEC ownership filing: {source.title}"]
    if transaction.transaction_code:
        details.append(f"transaction code {transaction.transaction_code}")
    if transaction.transaction_date:
        details.append(f"transaction date {transaction.transaction_date.isoformat()}")
    return "; ".join(details)


def accession_from_url(url: str) -> str:
    match = re.search(r"/data/\d+/(\d{18})/", url)
    if not match:
        return ""
    raw = match.group(1)
    return f"{raw[:10]}-{raw[10:12]}-{raw[12:]}"


def ownership_xml_url(url: str) -> str:
    """Remove the EDGAR XSL presentation path to request the original XML."""

    return re.sub(r"/(?:xslF345X\d+)/", "/", url, flags=re.IGNORECASE)


def parse_ownership_response(session: requests.Session, url: str, *, timeout: float, request_delay: float) -> list[Form4Transaction]:
    sleep(request_delay)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return parse_ownership_xml(response.text)


def parse_ownership_fallback(
    session: requests.Session,
    source_url: str,
    *,
    timeout: float,
    request_delay: float,
) -> list[Form4Transaction]:
    """Find the actual ownership XML through the SEC filing accession index."""

    sleep(request_delay)
    index_response = session.get(ownership_index_url(source_url), timeout=timeout)
    index_response.raise_for_status()
    for candidate_url in ownership_xml_candidates(source_url, index_response.json()):
        try:
            return parse_ownership_response(session, candidate_url, timeout=timeout, request_delay=request_delay)
        except (requests.RequestException, ElementTree.ParseError, ValueError):
            continue
    raise ValueError("No parseable ownership XML is listed in the SEC filing index.")


def ownership_index_url(url: str) -> str:
    match = re.search(r"^(https?://[^/]+/Archives/edgar/data/\d+/\d{18})/", url, flags=re.IGNORECASE)
    if not match:
        raise ValueError("SEC ownership filing URL does not include an accession directory.")
    return f"{match.group(1)}/index.json"


def ownership_xml_candidates(source_url: str, payload: dict) -> list[str]:
    """Return XML files listed by SEC for the same accession, excluding the first attempt."""

    items = payload.get("directory", {}).get("item", [])
    if not isinstance(items, list):
        raise ValueError("SEC filing index does not contain directory items.")
    base_url = ownership_index_url(source_url).removesuffix("index.json")
    primary_url = ownership_xml_url(source_url)
    candidates = []
    for item in items:
        name = item.get("name") if isinstance(item, dict) else ""
        if not isinstance(name, str) or not name.lower().endswith(".xml"):
            continue
        candidate = f"{base_url}{name}"
        if candidate != primary_url:
            candidates.append(candidate)
    return candidates


def footnote_ids(node: ElementTree.Element) -> list[str]:
    return [item.attrib["id"] for item in node.iter() if local_name(item.tag) == "footnoteId" and item.attrib.get("id")]


def date_at(node: ElementTree.Element, path: str) -> date | None:
    value = text_at(node, path)
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def decimal_at(node: ElementTree.Element, path: str) -> Decimal | None:
    value = text_at(node, path)
    try:
        return Decimal(value) if value else None
    except InvalidOperation:
        return None


def text_at(node: ElementTree.Element, path: str) -> str:
    element = find_path(node, path)
    return clean_text(element.text if element is not None and element.text else "")


def find_path(node: ElementTree.Element, path: str) -> ElementTree.Element | None:
    current = node
    for expected in path.split("/"):
        current = next((child for child in current if local_name(child.tag) == expected), None)
        if current is None:
            return None
    return current


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

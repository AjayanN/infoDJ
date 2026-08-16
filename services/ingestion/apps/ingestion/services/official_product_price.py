"""Extract explicit product prices from first-party JSON-LD Offer metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup

from apps.companies.models import ProductCatalogSnapshot, ProductOffering, ProductOfferingType, PriceObservation
from apps.ingestion.models import SourceDocument


@dataclass(frozen=True)
class OfficialPrice:
    name: str
    amount: Decimal
    currency: str
    evidence_text: str


def parse_official_prices(html: str) -> list[OfficialPrice]:
    """Return only prices explicitly supplied in JSON-LD Product/Offer records."""

    soup = BeautifulSoup(html, "html.parser")
    rows: list[OfficialPrice] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or script.get_text() or "{}")
        except (TypeError, ValueError):
            continue
        for node in walk_jsonld(payload):
            if not isinstance(node, dict):
                continue
            offers = node.get("offers")
            for offer in offers if isinstance(offers, list) else [offers]:
                price = official_price(node, offer)
                if price is not None:
                    rows.append(price)
    return unique_prices(rows)


def walk_jsonld(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_jsonld(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_jsonld(child)


def official_price(product: dict[str, Any], offer: Any) -> OfficialPrice | None:
    if not isinstance(offer, dict):
        return None
    price_specification = offer.get("priceSpecification")
    if not isinstance(price_specification, dict):
        price_specification = {}
    raw_amount = offer.get("price") or offer.get("lowPrice") or price_specification.get("price")
    currency = str(offer.get("priceCurrency") or price_specification.get("priceCurrency") or "").strip().upper()
    name = str(product.get("name") or offer.get("name") or "").strip()
    if not raw_amount or not currency or not name:
        return None
    try:
        amount = Decimal(str(raw_amount))
    except InvalidOperation:
        return None
    return OfficialPrice(name=name[:255], amount=amount, currency=currency[:16], evidence_text=f"First-party JSON-LD Offer: {name} {amount} {currency}.")


def unique_prices(rows: list[OfficialPrice]) -> list[OfficialPrice]:
    seen = set()
    result = []
    for row in rows:
        key = (row.name.lower(), row.amount, row.currency)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def store_official_prices(*, company, source: SourceDocument, html: str, observed_date: date | None = None) -> dict[str, int]:
    snapshot = (
        ProductCatalogSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return {"prices_found": 0, "prices_inserted": 0, "prices_updated": 0, "skipped": 0}
    counters = {"prices_found": 0, "prices_inserted": 0, "prices_updated": 0, "skipped": 0}
    for row in parse_official_prices(html):
        counters["prices_found"] += 1
        offering, _ = ProductOffering.objects.get_or_create(
            snapshot=snapshot,
            offering_type=ProductOfferingType.PLAN,
            name=row.name,
            defaults={"description": "First-party structured offer.", "evidence_text": row.evidence_text, "confidence_score": "0.950"},
        )
        _price, created = PriceObservation.objects.update_or_create(
            offering=offering,
            observed_date=observed_date or date.today(),
            currency=row.currency,
            geography="",
            customer_segment="",
            billing_period="",
            defaults={"amount": row.amount, "source_document": source, "evidence_text": row.evidence_text, "confidence_score": "0.950"},
        )
        counters["prices_inserted" if created else "prices_updated"] += 1
    return counters

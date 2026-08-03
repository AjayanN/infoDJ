"""Extract explicit product prices from first-party JSON-LD Offer metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup


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
    raw_amount = offer.get("price") or offer.get("lowPrice")
    currency = str(offer.get("priceCurrency") or "").strip().upper()
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

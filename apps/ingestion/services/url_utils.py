"""URL normalization, hashing, and source-document deduplication helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {
    "_hsenc",
    "_hsmi",
    "fbclid",
    "gad_source",
    "gbraid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "msclkid",
    "oly_anon_id",
    "oly_enc_id",
    "ref",
    "ref_src",
    "spm",
    "utm_campaign",
    "utm_content",
    "utm_id",
    "utm_medium",
    "utm_name",
    "utm_source",
    "utm_term",
    "vero_conv",
    "vero_id",
    "wbraid",
}


@dataclass(frozen=True)
class DuplicateMatch:
    """A duplicate source match and why it matched."""

    document: Any
    reason: str


def stable_hash(value: str) -> str:
    """Return a stable SHA-256 hash for normalized text values."""

    return sha256(value.encode("utf-8")).hexdigest()


def normalize_url(url: str | None) -> str:
    """Normalize URLs for duplicate detection without changing destination intent."""

    if not url:
        return ""

    parsed = urlsplit(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()

    if "@" in netloc:
        auth, host = netloc.rsplit("@", 1)
        host = _normalize_host_port(host, scheme)
        netloc = f"{auth}@{host}"
    else:
        netloc = _normalize_host_port(netloc, scheme)

    path = quote(unquote(parsed.path or "/"), safe="/:%@+~")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower in TRACKING_PARAMS or key_lower.startswith("utm_"):
            continue
        query_pairs.append((key, value))
    query = urlencode(sorted(query_pairs), doseq=True)

    return urlunsplit((scheme, netloc, path, query, ""))


def _normalize_host_port(netloc: str, scheme: str) -> str:
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if scheme == "http" and netloc.endswith(":80"):
        return netloc[:-3]
    if scheme == "https" and netloc.endswith(":443"):
        return netloc[:-4]
    return netloc


def url_hash(url: str | None) -> str:
    return stable_hash(normalize_url(url))


def normalize_title(title: str | None) -> str:
    """Normalize a title enough for conservative duplicate detection."""

    if not title:
        return ""
    value = title.lower()
    value = re.sub(r"\s+[-|]\s+[^-|]+$", "", value)
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_hash(title: str | None) -> str:
    return stable_hash(normalize_title(title))


def source_identity_values(source: Mapping[str, Any]) -> dict[str, str]:
    """Return canonical URL/title fields and hashes for a normalized source dict."""

    canonical_url = normalize_url(str(source.get("url") or ""))
    normalized_title = normalize_title(str(source.get("title") or ""))
    return {
        "canonical_url": canonical_url,
        "url_hash": stable_hash(canonical_url),
        "normalized_title": normalized_title,
        "title_hash": stable_hash(normalized_title),
    }


def find_duplicate_source(
    source: Mapping[str, Any],
    existing_sources: Iterable[Any],
    *,
    company: Any | None = None,
) -> DuplicateMatch | None:
    """Find exact URL or conservative same-company title duplicates."""

    identity = source_identity_values(source)
    publisher = _clean(source.get("publisher"))
    published_date = _date_only(source.get("published_date"))

    for document in existing_sources:
        if getattr(document, "url_hash", None) == identity["url_hash"]:
            return DuplicateMatch(document=document, reason="url_hash")

    for document in existing_sources:
        if company is not None and getattr(document, "company", None) not in (None, company):
            continue
        if getattr(document, "title_hash", None) != identity["title_hash"]:
            continue
        if _clean(getattr(document, "publisher", None)) != publisher:
            continue
        if _date_only(getattr(document, "published_date", None)) != published_date:
            continue
        return DuplicateMatch(document=document, reason="publisher_date_title")

    return None


def apply_source_hashes(source_document: Any) -> Any:
    """Populate canonical URL, URL hash, and title hash fields on a model-like object."""

    canonical_url = normalize_url(getattr(source_document, "url", ""))
    source_document.canonical_url = canonical_url
    source_document.url_hash = stable_hash(canonical_url)
    source_document.title_hash = title_hash(getattr(source_document, "title", ""))
    return source_document


def mark_duplicate(source_document: Any, duplicate_of: Any) -> Any:
    """Mark a model-like source document as duplicate without deleting it."""

    source_document.duplicate_of = duplicate_of
    source_document.status = "DUPLICATE"
    return source_document


def _clean(value: Any) -> str:
    return str(value or "").strip().lower()


def _date_only(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


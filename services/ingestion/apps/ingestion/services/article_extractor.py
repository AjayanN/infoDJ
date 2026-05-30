"""Article and filing text extraction helpers."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup
import requests
import trafilatura
import urllib3.util.connection as urllib3_connection


DEFAULT_USER_AGENT = "InfoDJ/0.1 business-event-research contact local-dev@example.com"


def _allowed_gai_family() -> socket.AddressFamily:
    return socket.AF_INET


urllib3_connection.allowed_gai_family = _allowed_gai_family


@dataclass(frozen=True)
class ExtractedText:
    clean_text: str
    extractor_name: str

    @property
    def word_count(self) -> int:
        return len(self.clean_text.split())


class ArticleExtractor:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers["User-Agent"] = DEFAULT_USER_AGENT
        self.session.headers["Accept-Encoding"] = "gzip, deflate"

    def extract_url(self, url: str) -> ExtractedText:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        html = response.text

        clean_text = trafilatura.extract(html, include_tables=True, favor_recall=True)
        if clean_text:
            return ExtractedText(clean_text=normalize_text(clean_text), extractor_name="trafilatura")

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ")
        return ExtractedText(clean_text=normalize_text(text), extractor_name="beautifulsoup")


def extract_source_document(
    source_document: Any,
    *,
    article_extraction_model: Any,
    extractor: ArticleExtractor | None = None,
) -> Any:
    extractor = extractor or ArticleExtractor()
    try:
        extracted = extractor.extract_url(source_document.url)
        extraction, _created = article_extraction_model.objects.update_or_create(
            source_document=source_document,
            defaults={
                "clean_text": extracted.clean_text,
                "word_count": extracted.word_count,
                "extractor_name": extracted.extractor_name,
                "extraction_status": "SUCCEEDED",
                "extraction_error": "",
            },
        )
        source_document.status = "EXTRACTED"
        source_document.save(update_fields=["status", "updated_at"])
        return extraction
    except Exception as exc:
        extraction, _created = article_extraction_model.objects.update_or_create(
            source_document=source_document,
            defaults={
                "clean_text": "",
                "word_count": 0,
                "extractor_name": "none",
                "extraction_status": "FAILED",
                "extraction_error": str(exc),
            },
        )
        source_document.status = "EXTRACTION_FAILED"
        source_document.save(update_fields=["status", "updated_at"])
        return extraction


def normalize_text(value: str) -> str:
    return " ".join(value.split())

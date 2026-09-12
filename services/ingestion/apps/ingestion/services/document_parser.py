"""Bounded document parsers that return stable evidence locators."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from bs4 import BeautifulSoup
import trafilatura


class DocumentParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    parser_name: str
    spans: tuple[tuple[str, str], ...]
    ocr_confidence: float | None = None


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def parse_document(content: bytes, media_type: str) -> ParsedDocument:
    if media_type in {"text/plain", "text/markdown"}:
        text = normalize_text(content.decode("utf-8", errors="replace"))
        return ParsedDocument(text=text, parser_name="plaintext", spans=(("char:0", text),))
    if media_type in {"text/html", "application/xhtml+xml"}:
        html = content.decode("utf-8", errors="replace")
        text = trafilatura.extract(html, include_tables=True, favor_recall=True)
        parser_name = "trafilatura"
        if not text:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(" ")
            parser_name = "beautifulsoup"
        text = normalize_text(text)
        return ParsedDocument(text=text, parser_name=parser_name, spans=(("char:0", text),))
    if media_type == "application/pdf":
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(content))
        except Exception as exc:
            raise DocumentParseError(f"PDF parsing failed: {exc}") from exc
        spans = []
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            page_text = normalize_text(page.extract_text() or "")
            pages.append(page_text)
            spans.append((f"page:{index}", page_text))
        if not any(pages):
            raise DocumentParseError("PDF has no extractable text; OCR is required before exact verification.")
        return ParsedDocument(text="\n".join(pages), parser_name="pypdf", spans=tuple(spans))
    raise DocumentParseError(f"Unsupported media type: {media_type}")


def parsed_bytes(parsed: ParsedDocument) -> bytes:
    return parsed.text.encode("utf-8")


def span_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

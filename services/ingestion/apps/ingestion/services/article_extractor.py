"""Legacy-compatible extraction backed by immutable source revisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.ingestion.models import EvidenceSpan, SourceRevision
from apps.ingestion.services.document_parser import parse_document, parsed_bytes, span_hash
from apps.ingestion.services.source_acquisition import FilesystemBlobStore, fetch_authorized_document, persist_source_revision


DEFAULT_USER_AGENT = "InfoDJ/0.1 business-event-research contact local-dev@example.com"


@dataclass(frozen=True)
class ExtractedText:
    clean_text: str
    extractor_name: str

    @property
    def word_count(self) -> int:
        return len(self.clean_text.split())


class ArticleExtractor:
    def __init__(self, *, session=None, timeout: float = 30.0, max_bytes: int = 20 * 1024 * 1024) -> None:
        self.session = session
        self.timeout = timeout
        self.max_bytes = max_bytes

    def extract_url(self, url: str) -> ExtractedText:
        acquired = fetch_authorized_document(url, session=self.session, timeout=self.timeout, max_bytes=self.max_bytes)
        parsed = parse_document(acquired.content, acquired.media_type)
        return ExtractedText(clean_text=parsed.text, extractor_name=parsed.parser_name)


def _preserve_failure(article_extraction_model: Any, source_document: Any, error: Exception) -> Any:
    extraction, created = article_extraction_model.objects.get_or_create(
        source_document=source_document,
        defaults={"clean_text": "", "word_count": 0, "extractor_name": "none", "extraction_status": "FAILED", "extraction_error": str(error)},
    )
    if not created:
        extraction.extraction_error = str(error)
        if extraction.extraction_status != "SUCCEEDED":
            extraction.extraction_status = "FAILED"
        extraction.save(update_fields=["extraction_error", "extraction_status", "updated_at"])
    if extraction.extraction_status != "SUCCEEDED":
        source_document.status = "EXTRACTION_FAILED"
        source_document.save(update_fields=["status", "updated_at"])
    return extraction


def extract_source_document(
    source_document: Any,
    *,
    article_extraction_model: Any,
    extractor: ArticleExtractor | None = None,
    blob_store: FilesystemBlobStore | None = None,
    revision_model: Any = SourceRevision,
) -> Any:
    """Acquire bytes before parsing and preserve previously successful legacy text."""
    extractor = extractor or ArticleExtractor()
    blob_store = blob_store or FilesystemBlobStore()
    try:
        acquired = fetch_authorized_document(source_document.url, session=extractor.session, timeout=extractor.timeout, max_bytes=extractor.max_bytes)
        revision, _created = persist_source_revision(source_document, acquired, blob_store=blob_store, revision_model=revision_model)
        parsed = parse_document(acquired.content, acquired.media_type)
        parsed_key = blob_store.put_bytes(parsed_bytes(parsed), prefix="parsed", suffix=".txt")
        if revision.parsed_storage_key != parsed_key:
            revision.parsed_storage_key = parsed_key
            revision.parser_version = parsed.parser_name
            revision.save(update_fields=["parsed_storage_key", "parser_version"])
        for locator, excerpt in parsed.spans:
            if excerpt:
                EvidenceSpan.objects.get_or_create(revision=revision, locator=locator, excerpt_sha256=span_hash(excerpt), defaults={"excerpt": excerpt})
        extraction, _created = article_extraction_model.objects.update_or_create(
            source_document=source_document,
            defaults={"clean_text": parsed.text, "word_count": len(parsed.text.split()), "extractor_name": parsed.parser_name, "extraction_status": "SUCCEEDED", "extraction_error": ""},
        )
        source_document.status = "EXTRACTED"
        source_document.save(update_fields=["status", "updated_at"])
        return extraction
    except Exception as exc:
        return _preserve_failure(article_extraction_model, source_document, exc)

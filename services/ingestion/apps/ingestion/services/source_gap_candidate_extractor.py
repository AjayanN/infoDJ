from __future__ import annotations

from dataclasses import dataclass
import re

from apps.ingestion.models import ArticleExtraction, SourceGapResolutionCandidate
from apps.ingestion.services.article_extractor import ArticleExtractor, extract_source_document
from apps.ingestion.services.source_gap_resolver import SOURCE_RULES, confidence_for


@dataclass(frozen=True)
class CandidateExtractionResult:
    candidates_checked: int
    documents_extracted: int
    candidates_updated: int
    candidates_failed: int


def extract_source_gap_candidates(
    *,
    limit: int = 100,
    dashboard: str = "",
    gap_type: str = "",
    timeout: float = 10.0,
    retry_failed: bool = False,
) -> CandidateExtractionResult:
    candidates = SourceGapResolutionCandidate.objects.filter(
        review_status="NEEDS_REVIEW",
        extraction_status="FAILED" if retry_failed else "CANDIDATE",
    ).select_related("source_document")
    if dashboard:
        candidates = candidates.filter(dashboard=dashboard)
    if gap_type:
        candidates = candidates.filter(gap_type=gap_type)
    checked = 0
    documents_extracted = 0
    updated = 0
    failed = 0
    extractions: dict[int, ArticleExtraction] = {}
    for candidate in candidates.order_by("company_id", "dashboard", "gap_type", "-confidence_score")[:limit]:
        checked += 1
        extraction = extractions.get(candidate.source_document_id)
        if extraction is None:
            extraction = ArticleExtraction.objects.filter(source_document=candidate.source_document).first()
            if extraction is not None:
                extractions[candidate.source_document_id] = extraction
        if extraction is None:
            extraction = extract_source_document(
                candidate.source_document,
                article_extraction_model=ArticleExtraction,
                extractor=ArticleExtractor(timeout=timeout),
            )
            extractions[candidate.source_document_id] = extraction
            if extraction.extraction_status == "SUCCEEDED":
                documents_extracted += 1
        elif extraction.extraction_status == "FAILED" and retry_failed:
            extraction = extract_source_document(
                candidate.source_document,
                article_extraction_model=ArticleExtraction,
                extractor=ArticleExtractor(timeout=timeout),
            )
            extractions[candidate.source_document_id] = extraction
        if extraction.extraction_status != "SUCCEEDED":
            candidate.extraction_status = "FAILED"
            candidate.metadata = {
                **safe_metadata(candidate),
                "extraction_error": extraction.extraction_error,
            }
            candidate.save(update_fields=["extraction_status", "metadata", "updated_at"])
            failed += 1
            continue
        rule = SOURCE_RULES.get((candidate.dashboard, candidate.gap_type), {})
        keywords = tuple(str(keyword) for keyword in rule.get("keywords", ()))
        evidence = full_text_excerpt(extraction.clean_text, keywords) or candidate.evidence_text
        confidence = confidence_for(
            candidate.source_document,
            evidence,
            tuple(str(source) for source in rule.get("sources", (candidate.source_document.source_api,))),
            keywords,
        )
        candidate.evidence_text = evidence
        candidate.confidence_score = f"{confidence:.3f}"
        candidate.extraction_status = "EXTRACTED"
        candidate.metadata = {
            **safe_metadata(candidate),
            "article_extraction_id": extraction.id,
            "word_count": extraction.word_count,
            "extractor_name": extraction.extractor_name,
            "full_text_evidence": True,
        }
        candidate.save(update_fields=["evidence_text", "confidence_score", "extraction_status", "metadata", "updated_at"])
        updated += 1
    return CandidateExtractionResult(
        candidates_checked=checked,
        documents_extracted=documents_extracted,
        candidates_updated=updated,
        candidates_failed=failed,
    )


def full_text_excerpt(text: str, keywords: tuple[str, ...], *, window: int = 900) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return ""
    lowered = normalized.lower()
    matches = [lowered.find(keyword.lower()) for keyword in keywords if keyword and keyword.lower() in lowered]
    first = min(matches) if matches else -1
    if first < 0:
        return normalized[:window].strip()
    start = max(first - window // 3, 0)
    end = min(first + window, len(normalized))
    return normalized[start:end].strip()


def safe_metadata(candidate: SourceGapResolutionCandidate) -> dict:
    return candidate.metadata if isinstance(candidate.metadata, dict) else {}

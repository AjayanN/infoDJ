"""Deterministic, evidence-first atomic claim extraction; no LLM is required."""
from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any, Iterable

from django.db import transaction

from apps.history.models import ClaimEvidence, EvidenceRole, HistoricalClaim, ReviewState
from apps.history.services.claim_validation import validate_candidate
from apps.ingestion.models import ExtractionRun

EXTRACTOR_VERSION = "deterministic-claim-v1"
PROMPT_VERSION = "none"


def extract_atomic_candidates(*, subject: Any, revision: Any, evidence_spans: Iterable[Any]) -> list[dict[str, Any]]:
    """Emit separate candidates for pricing, availability and distribution facts."""
    candidates = []
    for span in evidence_spans:
        for sentence in re.split(r"(?<=[.!?])\s+", span.excerpt):
            sentence = sentence.strip()
            if not sentence: continue
            lower = sentence.lower()
            tracks = []
            if re.search(r"[$€£]|\b(price|cost|fee|per month)\b", lower): tracks.append("pricing")
            if re.search(r"\b(available|retail|store|online|distribut)\w*\b", lower): tracks.append("marketing_distribution")
            if re.search(r"\b(release|launch|introduc)\w*\b", lower): tracks.append("product")
            for track in tracks:
                candidates.append({"schema_version": "1.0", "subject_id": str(subject.id), "track": track, "statement": sentence, "claim_kind": "source_attributed_claim", "event_kind": "release_detail", "time": {"precision": "UNKNOWN", "date_min": None, "date_max": None, "original_expression": ""}, "value": {"kind": "text", "text": sentence}, "evidence_span_ids": [str(span.id)]})
    return candidates


@transaction.atomic
def persist_candidates(*, subject: Any, revision: Any, candidates: list[dict[str, Any]], provider: str = "deterministic", budget_cents: int = 0, raw_candidate_response: dict[str, Any] | None = None) -> tuple[ExtractionRun, list[HistoricalClaim]]:
    spans = list(revision.evidence_spans.all())
    fingerprint = hashlib.sha256((str(revision.id) + EXTRACTOR_VERSION + repr(candidates)).encode()).hexdigest()
    run, created = ExtractionRun.objects.get_or_create(revision=revision, run_fingerprint=fingerprint, defaults={"schema_version": "1.0", "parser_version": revision.parser_version, "extractor_version": EXTRACTOR_VERSION, "prompt_version": PROMPT_VERSION, "provider": provider, "budget_cents": budget_cents, "raw_candidate_response": raw_candidate_response or {"candidates": candidates}, "status": "SUCCEEDED"})
    if not created:
        return run, list(run.historical_claims.order_by("recorded_at"))
    claims = []
    for candidate in candidates:
        validate_candidate(candidate, subject_id=subject.id, evidence_spans=spans)
        time = candidate["time"]
        claim = HistoricalClaim.objects.create(subject=subject, track=candidate["track"], claim_type=candidate["claim_kind"], event_kind=candidate["event_kind"], statement=candidate["statement"], value=candidate["value"], date_min=time["date_min"], date_max=time["date_max"], date_precision=time["precision"], original_date_expression=time["original_expression"], schema_version=candidate["schema_version"], extraction_run=run, review_state=ReviewState.PENDING)
        for span_id in candidate["evidence_span_ids"]:
            ClaimEvidence.objects.create(claim=claim, evidence_span=next(span for span in spans if str(span.id) == str(span_id)), role=EvidenceRole.SUPPORTS)
        claims.append(claim)
    return run, claims

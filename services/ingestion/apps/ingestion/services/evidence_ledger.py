from __future__ import annotations

from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import EvidenceRecord, EvidenceRecordType, FinancialFact


def rebuild_evidence_ledger(*, company_slug: str = "") -> dict[str, int]:
    company_filter = {"company__slug": company_slug} if company_slug else {}
    totals = {"business_events": 0, "strategic_turns": 0, "financial_facts": 0}

    for event in BusinessEvent.objects.filter(**company_filter).select_related("company", "source_document"):
        _upsert(
            fingerprint=f"business-event:{event.id}",
            company=event.company,
            source_document=event.source_document,
            record_type=EvidenceRecordType.BUSINESS_EVENT,
            event_date=event.event_date,
            title=f"{event.company.name}: {event.get_event_type_display()}",
            summary=event.actual_change,
            source_excerpt=event.evidence_text or event.source_claim,
            tags=[event.event_type, event.decision_theme] if event.decision_theme else [event.event_type],
            confidence_score=event.confidence_score,
            review_status=event.review_status,
            metadata={"business_event_id": event.id},
        )
        totals["business_events"] += 1

    for turn in StrategicTurn.objects.filter(**company_filter).select_related("company"):
        source_link = (
            StrategicTurnSource.objects.filter(strategic_turn=turn)
            .select_related("source_document")
            .order_by("id")
            .first()
        )
        _upsert(
            fingerprint=f"strategic-turn:{turn.id}",
            company=turn.company,
            source_document=source_link.source_document if source_link else None,
            record_type=EvidenceRecordType.STRATEGIC_TURN,
            event_date=turn.start_date,
            title=turn.title,
            summary=turn.summary or turn.decision,
            source_excerpt=turn.outcome,
            tags=[turn.turn_type],
            confidence_score=turn.confidence_score,
            review_status=turn.review_status,
            metadata={"strategic_turn_id": turn.id, "source_count": StrategicTurnSource.objects.filter(strategic_turn=turn).count()},
        )
        totals["strategic_turns"] += 1

    for fact in FinancialFact.objects.filter(**company_filter).select_related("company"):
        _upsert(
            fingerprint=f"financial-fact:{fact.id}",
            company=fact.company,
            source_document=None,
            record_type=EvidenceRecordType.FINANCIAL_FACT,
            event_date=fact.filed,
            title=f"{fact.company.name}: {fact.label or fact.concept}",
            summary=f"{fact.label or fact.concept}: {fact.value} {fact.unit}",
            source_excerpt="",
            tags=[fact.concept, fact.fp] if fact.fp else [fact.concept],
            confidence_score="1.000",
            review_status="NEEDS_REVIEW",
            metrics={"concept": fact.concept, "label": fact.label, "unit": fact.unit, "value": str(fact.value), "fy": fact.fy, "fp": fact.fp, "frame": fact.frame},
            metadata={"financial_fact_id": fact.id, "accession_number": fact.accession_number, "source_missing": True},
        )
        totals["financial_facts"] += 1

    return totals


def _upsert(*, fingerprint, company, source_document, record_type, event_date, title, summary, source_excerpt, tags, confidence_score, review_status, metadata, metrics=None):
    EvidenceRecord.objects.update_or_create(
        source_fingerprint=fingerprint,
        defaults={
            "company": company,
            "source_document": source_document,
            "record_type": record_type,
            "claim_type": "reported_fact",
            "sector": company.industry,
            "event_date": event_date,
            "published_date": source_document.published_date if source_document else None,
            "title": title[:512],
            "summary": summary,
            "source_excerpt": source_excerpt,
            "tags": [tag for tag in tags if tag],
            "metrics": metrics or {},
            "confidence_score": confidence_score or 0,
            "review_status": review_status if review_status in {"NEEDS_REVIEW", "REVIEWED", "REJECTED", "SUPERSEDED"} else "NEEDS_REVIEW",
            "metadata": metadata,
        },
    )


def rebuild_reviewed_history_claim_ledger(*, company_slug: str = "") -> int:
    """Project reviewed claims into the existing ledger with stable claim fingerprints."""
    from apps.history.models import HistoricalClaim, ReviewState
    query = HistoricalClaim.objects.filter(review_state=ReviewState.REVIEWED).select_related("subject__company").prefetch_related("evidence_links__evidence_span__revision__source_document")
    if company_slug: query = query.filter(subject__company__slug=company_slug)
    count = 0
    for claim in query:
        company = claim.subject.company
        if company is None: continue
        link = next((x for x in claim.evidence_links.all() if x.role == "SUPPORTS"), None)
        source = link.evidence_span.revision.source_document if link else None
        _upsert(fingerprint=f"history-claim:{claim.id}", company=company, source_document=source, record_type=EvidenceRecordType.BUSINESS_EVENT, event_date=claim.date_min, title=f"{company.name}: {claim.event_kind}", summary=claim.statement, source_excerpt=link.evidence_span.excerpt if link else "", tags=[claim.track, claim.event_kind], confidence_score="1.000", review_status="REVIEWED", metadata={"historical_claim_id": str(claim.id), "claim_date_max": claim.date_max.isoformat() if claim.date_max else None, "date_precision": claim.date_precision, "review_state": claim.review_state})
        count += 1
    return count

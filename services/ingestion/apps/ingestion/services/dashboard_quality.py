from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


MIN_EVENT_CONFIDENCE = Decimal("0.500")
MIN_TURN_CONFIDENCE = Decimal("0.500")

RISK_EVENT_TYPES = (
    "PERFORMANCE_DECLINE",
    "COST_RESTRUCTURING",
    "LEADERSHIP_CHANGE",
    "REGULATORY_RESPONSE",
    "CRISIS_RESPONSE",
    "COMPETITIVE_RESPONSE",
)

GENERIC_EVENT_PHRASES = (
    "disclosed performance pressure that may require strategic or operating response",
    "expanded its product, service, or capability set",
    "disclosed this legal/regulatory risk; no response action was extracted",
    "no response action was extracted",
    "becomes an explicit strategic and operating constraint",
    "become material operating requirements",
    "becomes a material growth and risk area",
    "becomes a lever for growth",
    "become part of operating and growth strategy",
    "becomes a growth and differentiation lever",
    "becomes an active strategic lever",
    "become part of the operating model",
    "forces operating, pricing, portfolio, or investment changes",
)

GENERIC_TURN_FRAGMENTS = (
    "adapts to regulatory and legal risk",
    "adapt to legal, regulatory, and compliance pressure",
    "adjusts pricing and packaging",
    "changes capital allocation",
    "expands international operations",
    "expands products and services",
    "responds to competitive pressure",
    "responds to performance pressure",
    "restructures costs and operations",
    "uses acquisitions and divestitures",
    "uses partnerships and alliances",
    "respond to intensifying competition",
    "scale operations across international markets",
    "scales international operations",
)

SPECIFIC_ACTION_MARKERS = (
    "introduced",
    "added",
    "launched",
    "settled",
    "paid",
    "recorded",
    "acquired",
    "divested",
    "expanded",
    "invested",
    "implemented",
    "changed",
    "restructured",
    "partnered",
    "agreed",
    "entered into",
    "announced",
    "appointed",
    "resigned",
    "completed",
    "closed",
)


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    status: str
    score: float
    reasons: tuple[str, ...]


def event_source_count(event: Any) -> int:
    raw = getattr(event, "raw_extraction_json", None) or {}
    return len(raw.get("additional_source_ids") or []) + (1 if getattr(event, "source_document_id", None) else 0)


def turn_source_count(turn_id: int, source_counts: dict[int, int]) -> int:
    return int(source_counts.get(turn_id, 0) or 0)


def event_eligibility(event: Any, *, require_specific_action: bool = True) -> EligibilityResult:
    reasons: list[str] = []
    score = 0.0
    actual_change = clean(getattr(event, "actual_change", ""))
    source_claim = clean(getattr(event, "source_claim", ""))
    evidence_text = clean(getattr(event, "evidence_text", ""))
    confidence = getattr(event, "confidence_score", 0) or 0
    source_count = event_source_count(event)

    if getattr(event, "event_date", None):
        score += 0.15
    else:
        reasons.append("missing_event_date")

    if source_count > 0:
        score += 0.25
    else:
        reasons.append("missing_source_document")

    if actual_change:
        score += 0.20
    else:
        reasons.append("missing_actual_change")

    if source_claim:
        score += 0.15
    else:
        reasons.append("missing_source_claim")

    if evidence_text:
        score += 0.10

    if Decimal(str(confidence)) >= MIN_EVENT_CONFIDENCE:
        score += 0.15
    else:
        reasons.append("low_confidence")

    if has_generic_event_text(actual_change) or has_generic_event_text(source_claim):
        reasons.append("generic_event_text")

    if require_specific_action and not has_specific_action(actual_change):
        reasons.append("missing_specific_company_action")

    eligible = not any(
        reason
        in {
            "missing_event_date",
            "missing_source_document",
            "missing_actual_change",
            "missing_source_claim",
            "low_confidence",
            "generic_event_text",
            "missing_specific_company_action",
        }
        for reason in reasons
    )
    return EligibilityResult(
        eligible=eligible,
        status="ELIGIBLE" if eligible else "INELIGIBLE",
        score=round(score, 3),
        reasons=tuple(reasons),
    )


def lifecycle_timing_eligibility(event: Any) -> EligibilityResult:
    """Strict admission rule for founder-comparison evidence."""
    reasons: list[str] = []
    score = 0.0
    context = getattr(event, "lifecycle_context_json", None) or {}
    company = getattr(event, "company", None)
    metrics = context.get("metrics") if isinstance(context, dict) else None

    if getattr(event, "lifecycle_timing_status", "") == "VERIFIED": score += 0.20
    else: reasons.append("lifecycle_timing_not_verified")
    if getattr(event, "action_date", None): score += 0.20
    else: reasons.append("missing_actual_action_date")
    if not getattr(event, "action_date_precision", ""):
        reasons.append("missing_action_date_precision")
    elif getattr(event, "action_date_precision") != "DAY":
        reasons.append("actual_action_date_must_be_exact_day")
    else:
        score += 0.10
    if clean(getattr(event, "action_date_evidence", "")): score += 0.15
    else: reasons.append("missing_action_date_evidence")
    if getattr(company, "founded_date", None): score += 0.15
    else: reasons.append("missing_founding_anchor")
    if isinstance(context, dict) and context.get("as_of_date") and context.get("source_url") and isinstance(metrics, list) and metrics:
        score += 0.20
    else:
        reasons.append("missing_contemporaneous_scale")

    eligible = not reasons
    return EligibilityResult(eligible=eligible, status="ELIGIBLE" if eligible else "INELIGIBLE", score=round(score, 3), reasons=tuple(reasons))


def risk_event_eligibility(event: Any) -> EligibilityResult:
    result = event_eligibility(event, require_specific_action=False)
    reasons = list(result.reasons)
    if getattr(event, "event_type", "") not in RISK_EVENT_TYPES:
        reasons.append("not_risk_event_type")
    eligible = result.eligible and "not_risk_event_type" not in reasons
    return EligibilityResult(
        eligible=eligible,
        status="ELIGIBLE" if eligible else "INELIGIBLE",
        score=result.score,
        reasons=tuple(reasons),
    )


def turn_eligibility(turn: Any, *, source_count: int) -> EligibilityResult:
    reasons: list[str] = []
    score = 0.0
    title = clean(getattr(turn, "title", ""))
    summary = clean(getattr(turn, "summary", ""))
    decision = clean(getattr(turn, "decision", ""))
    outcome = clean(getattr(turn, "outcome", ""))
    confidence = getattr(turn, "confidence_score", 0) or 0

    if getattr(turn, "start_date", None):
        score += 0.15
    else:
        reasons.append("missing_start_date")

    if source_count > 0:
        score += 0.30
    else:
        reasons.append("missing_turn_sources")

    if title:
        score += 0.10
    else:
        reasons.append("missing_title")

    if summary or decision or outcome:
        score += 0.20
    else:
        reasons.append("missing_turn_detail")

    if Decimal(str(confidence)) >= MIN_TURN_CONFIDENCE:
        score += 0.15
    else:
        reasons.append("low_confidence")

    if not is_specific_turn_text(title, summary, decision, outcome):
        reasons.append("generic_turn_text")

    eligible = not any(
        reason
        in {
            "missing_start_date",
            "missing_turn_sources",
            "missing_title",
            "missing_turn_detail",
            "low_confidence",
            "generic_turn_text",
        }
        for reason in reasons
    )
    return EligibilityResult(
        eligible=eligible,
        status="ELIGIBLE" if eligible else "INELIGIBLE",
        score=round(score, 3),
        reasons=tuple(reasons),
    )


def section_payload(
    *,
    key: str,
    items: list[dict],
    raw_count: int,
    eligible_count: int | None = None,
    page: int = 1,
    page_size: int | None = None,
    source_gaps: list[dict],
    required_data: list[str],
    next_action: str,
) -> dict:
    total = len(items) if eligible_count is None else eligible_count
    size = len(items) if page_size is None else page_size
    total_pages = max(1, ((total + size - 1) // size) if size else 1)
    status = "available" if items else "unavailable"
    return {
        "key": key,
        "status": status,
        "eligible_count": total,
        "raw_count": raw_count,
        "excluded_count": max(raw_count - total, 0),
        "page": page,
        "page_size": size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
        "items": items,
        "source_gaps": source_gaps,
        "required_data": required_data,
        "next_action": next_action,
    }


def source_gap_dict(
    *,
    key: str,
    reason: str,
    source: str,
    next_action: str,
    dashboard: str = "",
) -> dict[str, str]:
    return {
        "key": key,
        "dashboard": dashboard,
        "reason": reason,
        "source": source,
        "next_action": next_action,
    }


def clean(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def has_generic_event_text(value: str) -> bool:
    return any(phrase in value for phrase in GENERIC_EVENT_PHRASES)


def has_specific_action(value: str) -> bool:
    return any(marker in value for marker in SPECIFIC_ACTION_MARKERS)


def is_specific_turn_text(title: str, summary: str, decision: str, outcome: str) -> bool:
    combined = " ".join([title, summary, decision, outcome])
    if any(fragment in combined for fragment in GENERIC_TURN_FRAGMENTS):
        return False
    if summary and summary == decision:
        return False
    return has_specific_action(" ".join([summary, decision, outcome]))

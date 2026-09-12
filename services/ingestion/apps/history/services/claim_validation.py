"""Strict semantic validation for versioned, evidence-bound claim candidates."""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable
from uuid import UUID

from django.core.exceptions import ValidationError

TRACKS = {"product", "customers", "pricing", "team", "marketing_distribution", "intellectual_property", "legal_regulatory", "operations_finance"}
CLAIM_KINDS = {"documented_action", "source_reported_intent", "source_reported_outcome", "measurement", "source_attributed_claim"}
PRECISIONS = {"DAY", "MONTH", "QUARTER", "YEAR", "RANGE", "UNKNOWN"}
INJECTION_MARKERS = ("ignore previous", "system message", "developer message", "disregard instructions", "reveal prompt")


def validate_candidate(candidate: dict[str, Any], *, subject_id: Any, evidence_spans: Iterable[Any]) -> None:
    """Reject malformed, uncited, cross-revision, or non-entailing candidates.

    This deliberately does not grant review approval: schema-valid candidates remain
    PENDING until a reviewer journals a decision.
    """
    required = {"schema_version", "subject_id", "track", "statement", "claim_kind", "event_kind", "time", "value", "evidence_span_ids"}
    if set(candidate) != required:
        raise ValidationError("Candidate fields do not match claim-v1 schema.")
    if candidate["schema_version"] != "1.0" or str(candidate["subject_id"]) != str(subject_id):
        raise ValidationError("Candidate schema version or subject is invalid.")
    if candidate["track"] not in TRACKS or candidate["claim_kind"] not in CLAIM_KINDS:
        raise ValidationError("Candidate track or claim kind is not registered.")
    statement = candidate["statement"]
    if not isinstance(statement, str) or not statement.strip() or len(statement) > 4000:
        raise ValidationError("Candidate statement is invalid.")
    if any(marker in statement.lower() for marker in INJECTION_MARKERS):
        raise ValidationError("Prompt-injection text cannot become a claim.")
    if not isinstance(candidate["event_kind"], str) or not candidate["event_kind"].strip():
        raise ValidationError("Candidate event kind is required.")
    _validate_time(candidate["time"])
    if not isinstance(candidate["value"], dict):
        raise ValidationError("Candidate value must be a JSON object.")
    requested = candidate["evidence_span_ids"]
    if not isinstance(requested, list) or not requested or len(requested) != len(set(requested)):
        raise ValidationError("Candidate must name unique evidence spans.")
    available = {str(span.id): span for span in evidence_spans}
    if any(str(item) not in available for item in requested):
        raise ValidationError("Candidate cites an unknown or unrelated evidence span.")
    excerpts = " ".join(available[str(item)].excerpt.lower() for item in requested)
    if not _statement_entails(statement, excerpts):
        raise ValidationError("Candidate statement is not entailed by its exact evidence excerpt.")


def _validate_time(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"precision", "date_min", "date_max", "original_expression"}:
        raise ValidationError("Candidate time is invalid.")
    precision = value["precision"]
    if precision not in PRECISIONS or not isinstance(value["original_expression"], str):
        raise ValidationError("Candidate time precision is invalid.")
    lower, upper = value["date_min"], value["date_max"]
    if precision == "UNKNOWN" and (lower or upper):
        raise ValidationError("Unknown time cannot carry bounds.")
    if lower:
        try: date.fromisoformat(lower)
        except (TypeError, ValueError) as exc: raise ValidationError("Invalid date lower bound.") from exc
    if upper:
        try: date.fromisoformat(upper)
        except (TypeError, ValueError) as exc: raise ValidationError("Invalid date upper bound.") from exc
    if lower and upper and lower > upper: raise ValidationError("Candidate dates are reversed.")
    if precision == "DAY" and lower != upper: raise ValidationError("Day precision requires equal bounds.")


def _statement_entails(statement: str, excerpts: str) -> bool:
    terms = [term.strip(".,;:!?()[]{}\"'").lower() for term in statement.split() if len(term.strip(".,;:!?()[]{}\"'")) >= 4]
    return bool(terms) and sum(term in excerpts for term in terms) / len(terms) >= 0.6

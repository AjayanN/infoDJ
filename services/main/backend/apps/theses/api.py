from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.theses.models import (
    EvidenceSide,
    EvidenceType,
    IndicatorDirection,
    StrategyThesis,
    ThesisEvidence,
    ThesisIndicator,
    ThesisMilestone,
    ThesisMilestoneStatus,
    ThesisRevision,
    ThesisState,
)


INGESTION_TIMEOUT_SECONDS = 10


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def theses(request):
    if request.method == "POST":
        payload = request.data
        thesis = StrategyThesis.objects.create(
            owner=request.user,
            title=clean_string(payload.get("title")) or "Untitled thesis",
            company_slug=clean_string(payload.get("company_slug")),
            company_name=clean_string(payload.get("company_name")),
            statement=clean_string(payload.get("statement")),
            state=choice_value(payload.get("state"), ThesisState.values, ThesisState.DRAFT),
            time_horizon=clean_string(payload.get("time_horizon")),
            review_date=parse_date(payload.get("review_date")),
            confidence_score=parse_decimal(payload.get("confidence_score"), Decimal("0")),
            confidence_reason=clean_string(payload.get("confidence_reason")),
            assumptions=list_payload(payload.get("assumptions")),
            is_shared=bool(payload.get("is_shared", False)),
            shared_label=clean_string(payload.get("shared_label")),
        )
        ThesisRevision.objects.create(
            thesis=thesis,
            changed_by=request.user,
            previous_state="",
            new_state=thesis.state,
            previous_confidence_score=None,
            new_confidence_score=thesis.confidence_score,
            reason="Thesis created.",
        )
        return Response({"thesis": serialize_thesis(thesis)}, status=201)

    queryset = StrategyThesis.objects.filter(owner=request.user).prefetch_related("evidence", "milestones", "indicators", "revisions")
    if request.GET.get("state"):
        queryset = queryset.filter(state=request.GET["state"])
    if request.GET.get("company"):
        queryset = queryset.filter(company_slug=request.GET["company"])
    if request.GET.get("q"):
        query = request.GET["q"].strip()
        queryset = queryset.filter(Q(title__icontains=query) | Q(statement__icontains=query) | Q(company_name__icontains=query))
    return Response(
        {
            "theses": [serialize_thesis(row, compact=True) for row in queryset],
            "summary": thesis_summary(request.user),
            "states": [{"value": value, "label": label} for value, label in ThesisState.choices],
            "evidence_sides": [{"value": value, "label": label} for value, label in EvidenceSide.choices],
            "evidence_types": [{"value": value, "label": label} for value, label in EvidenceType.choices],
        }
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def thesis_detail(request, thesis_id: int):
    thesis = get_owned_thesis(request.user, thesis_id)
    if request.method == "DELETE":
        thesis.delete()
        return Response({"status": "deleted"})
    if request.method == "PATCH":
        update_thesis_from_payload(thesis, request.data)
        thesis.save()
    thesis = get_owned_thesis(request.user, thesis_id)
    return Response({"thesis": serialize_thesis(thesis)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def thesis_evidence(request, thesis_id: int):
    thesis = get_owned_thesis(request.user, thesis_id)
    evidence = ThesisEvidence.objects.create(
        thesis=thesis,
        side=choice_value(request.data.get("side"), EvidenceSide.values, EvidenceSide.SUPPORTING),
        evidence_type=choice_value(request.data.get("evidence_type"), EvidenceType.values, EvidenceType.NOTE),
        company_slug=clean_string(request.data.get("company_slug")) or thesis.company_slug,
        external_id=clean_string(request.data.get("external_id")),
        title=clean_string(request.data.get("title")) or "Untitled evidence",
        summary=clean_string(request.data.get("summary")),
        source_url=clean_string(request.data.get("source_url")),
        source_date=parse_date(request.data.get("source_date")),
        source_payload=dict_payload(request.data.get("source_payload")),
        user_note=clean_string(request.data.get("user_note")),
    )
    thesis.save(update_fields=["updated_at"])
    return Response({"evidence": serialize_evidence(evidence), "balance": evidence_balance(thesis)}, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def thesis_evidence_detail(request, thesis_id: int, evidence_id: int):
    thesis = get_owned_thesis(request.user, thesis_id)
    evidence = get_child(thesis.evidence, evidence_id)
    if request.method == "DELETE":
        evidence.delete()
        thesis.save(update_fields=["updated_at"])
        return Response({"status": "deleted", "balance": evidence_balance(thesis)})
    update_evidence_from_payload(evidence, request.data)
    evidence.save()
    thesis.save(update_fields=["updated_at"])
    return Response({"evidence": serialize_evidence(evidence), "balance": evidence_balance(thesis)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def thesis_milestones(request, thesis_id: int):
    thesis = get_owned_thesis(request.user, thesis_id)
    milestone = ThesisMilestone.objects.create(
        thesis=thesis,
        title=clean_string(request.data.get("title")) or "Untitled milestone",
        due_date=parse_date(request.data.get("due_date")),
        status=choice_value(request.data.get("status"), ThesisMilestoneStatus.values, ThesisMilestoneStatus.PENDING),
        success_criteria=clean_string(request.data.get("success_criteria")),
        linked_evidence=get_optional_evidence(thesis, request.data.get("linked_evidence_id")),
    )
    thesis.save(update_fields=["updated_at"])
    return Response({"milestone": serialize_milestone(milestone)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def thesis_indicators(request, thesis_id: int):
    thesis = get_owned_thesis(request.user, thesis_id)
    indicator = ThesisIndicator.objects.create(
        thesis=thesis,
        name=clean_string(request.data.get("name")) or "Untitled indicator",
        direction=choice_value(request.data.get("direction"), IndicatorDirection.values, IndicatorDirection.QUALITATIVE),
        target=clean_string(request.data.get("target")),
        current_value=clean_string(request.data.get("current_value")),
        source_hint=clean_string(request.data.get("source_hint")),
    )
    thesis.save(update_fields=["updated_at"])
    return Response({"indicator": serialize_indicator(indicator)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def thesis_confidence(request, thesis_id: int):
    thesis = get_owned_thesis(request.user, thesis_id)
    previous_state = thesis.state
    previous_confidence = thesis.confidence_score
    thesis.state = choice_value(request.data.get("state"), ThesisState.values, thesis.state)
    thesis.confidence_score = parse_decimal(request.data.get("confidence_score"), thesis.confidence_score)
    thesis.confidence_reason = clean_string(request.data.get("reason"))
    thesis.save()
    revision = ThesisRevision.objects.create(
        thesis=thesis,
        changed_by=request.user,
        previous_state=previous_state,
        new_state=thesis.state,
        previous_confidence_score=previous_confidence,
        new_confidence_score=thesis.confidence_score,
        reason=thesis.confidence_reason or "Confidence updated.",
    )
    return Response({"thesis": serialize_thesis(thesis), "revision": serialize_revision(revision)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def evidence_suggestions(request):
    query = clean_string(request.GET.get("q")) or clean_string(request.GET.get("company"))
    company = clean_string(request.GET.get("company"))
    if not query:
        return Response({"suggestions": [], "source": "ingestion.search", "source_gaps": [{"key": "query_required", "reason": "Enter a company or evidence query to search InfoDJ evidence.", "next_action": "Provide q or company."}]})

    payload, error = ingestion_get("search", {"q": query, "language": "en", "limit": request.GET.get("limit") or 8})
    if error:
        return Response(
            {
                "suggestions": [],
                "source": "ingestion.search",
                "source_gaps": [
                    {
                        "key": "thesis_evidence_search_unavailable",
                        "reason": error,
                        "next_action": "Restore ingestion search before attaching reviewed InfoDJ evidence.",
                    }
                ],
            },
            status=503,
        )

    return Response({"suggestions": normalize_search_suggestions(payload or {}, company), "source": "ingestion.search", "source_gaps": []})


def update_thesis_from_payload(thesis: StrategyThesis, payload: dict) -> None:
    for field in ("title", "company_slug", "company_name", "statement", "time_horizon", "confidence_reason", "shared_label"):
        if field in payload:
            setattr(thesis, field, clean_string(payload.get(field)))
    if "state" in payload:
        thesis.state = choice_value(payload.get("state"), ThesisState.values, thesis.state)
    if "review_date" in payload:
        thesis.review_date = parse_date(payload.get("review_date"))
    if "confidence_score" in payload:
        thesis.confidence_score = parse_decimal(payload.get("confidence_score"), thesis.confidence_score)
    if "assumptions" in payload:
        thesis.assumptions = list_payload(payload.get("assumptions"))
    if "is_shared" in payload:
        thesis.is_shared = bool(payload.get("is_shared"))


def update_evidence_from_payload(evidence: ThesisEvidence, payload: dict) -> None:
    for field in ("company_slug", "external_id", "title", "summary", "source_url", "user_note"):
        if field in payload:
            setattr(evidence, field, clean_string(payload.get(field)))
    if "side" in payload:
        evidence.side = choice_value(payload.get("side"), EvidenceSide.values, evidence.side)
    if "evidence_type" in payload:
        evidence.evidence_type = choice_value(payload.get("evidence_type"), EvidenceType.values, evidence.evidence_type)
    if "source_date" in payload:
        evidence.source_date = parse_date(payload.get("source_date"))
    if "source_payload" in payload:
        evidence.source_payload = dict_payload(payload.get("source_payload"))


def get_owned_thesis(user, thesis_id: int) -> StrategyThesis:
    try:
        return (
            StrategyThesis.objects.filter(owner=user)
            .prefetch_related("evidence", "milestones", "indicators", "revisions")
            .get(id=thesis_id)
        )
    except StrategyThesis.DoesNotExist as exc:
        raise Http404("Thesis not found") from exc


def get_child(manager, child_id: int):
    try:
        return manager.get(id=child_id)
    except manager.model.DoesNotExist as exc:
        raise Http404("Record not found") from exc


def get_optional_evidence(thesis: StrategyThesis, evidence_id) -> ThesisEvidence | None:
    if not evidence_id:
        return None
    return get_child(thesis.evidence, int(evidence_id))


def serialize_thesis(thesis: StrategyThesis, compact: bool = False) -> dict:
    payload = {
        "id": thesis.id,
        "title": thesis.title,
        "company_slug": thesis.company_slug,
        "company_name": thesis.company_name,
        "statement": thesis.statement,
        "state": thesis.state,
        "state_label": thesis.get_state_display(),
        "time_horizon": thesis.time_horizon,
        "review_date": thesis.review_date.isoformat() if thesis.review_date else None,
        "confidence_score": float(thesis.confidence_score),
        "confidence_reason": thesis.confidence_reason,
        "assumptions": thesis.assumptions,
        "is_shared": thesis.is_shared,
        "shared_label": thesis.shared_label,
        "balance": evidence_balance(thesis),
        "updated_at": thesis.updated_at.isoformat(),
        "created_at": thesis.created_at.isoformat(),
    }
    if not compact:
        payload.update(
            {
                "evidence": [serialize_evidence(row) for row in thesis.evidence.all()],
                "milestones": [serialize_milestone(row) for row in thesis.milestones.all()],
                "indicators": [serialize_indicator(row) for row in thesis.indicators.all()],
                "revisions": [serialize_revision(row) for row in thesis.revisions.all()],
                "privacy_note": "This is private user-authored analysis unless explicitly shared. User notes are not published InfoDJ facts.",
            }
        )
    return payload


def serialize_evidence(evidence: ThesisEvidence) -> dict:
    return {
        "id": evidence.id,
        "side": evidence.side,
        "side_label": evidence.get_side_display(),
        "evidence_type": evidence.evidence_type,
        "evidence_type_label": evidence.get_evidence_type_display(),
        "company_slug": evidence.company_slug,
        "external_id": evidence.external_id,
        "title": evidence.title,
        "summary": evidence.summary,
        "source_url": evidence.source_url,
        "source_date": evidence.source_date.isoformat() if evidence.source_date else None,
        "source_payload": evidence.source_payload,
        "user_note": evidence.user_note,
        "separation_note": "summary/source_payload describe referenced evidence; user_note is private user-authored commentary.",
        "updated_at": evidence.updated_at.isoformat(),
    }


def serialize_milestone(milestone: ThesisMilestone) -> dict:
    return {
        "id": milestone.id,
        "title": milestone.title,
        "due_date": milestone.due_date.isoformat() if milestone.due_date else None,
        "status": milestone.status,
        "status_label": milestone.get_status_display(),
        "success_criteria": milestone.success_criteria,
        "linked_evidence_id": milestone.linked_evidence_id,
    }


def serialize_indicator(indicator: ThesisIndicator) -> dict:
    return {
        "id": indicator.id,
        "name": indicator.name,
        "direction": indicator.direction,
        "direction_label": indicator.get_direction_display(),
        "target": indicator.target,
        "current_value": indicator.current_value,
        "source_hint": indicator.source_hint,
    }


def serialize_revision(revision: ThesisRevision) -> dict:
    return {
        "id": revision.id,
        "previous_state": revision.previous_state,
        "new_state": revision.new_state,
        "previous_confidence_score": float(revision.previous_confidence_score) if revision.previous_confidence_score is not None else None,
        "new_confidence_score": float(revision.new_confidence_score),
        "reason": revision.reason,
        "changed_by": revision.changed_by.username,
        "created_at": revision.created_at.isoformat(),
    }


def evidence_balance(thesis: StrategyThesis) -> dict:
    counts = dict(thesis.evidence.values("side").annotate(count=Count("id")).values_list("side", "count"))
    supporting = counts.get(EvidenceSide.SUPPORTING, 0)
    opposing = counts.get(EvidenceSide.OPPOSING, 0)
    total = sum(counts.values())
    return {
        "supporting": supporting,
        "opposing": opposing,
        "neutral": counts.get(EvidenceSide.NEUTRAL, 0),
        "total": total,
        "support_ratio": round((supporting / total) * 100, 1) if total else 0,
        "opposition_ratio": round((opposing / total) * 100, 1) if total else 0,
    }


def thesis_summary(user) -> dict:
    rows = StrategyThesis.objects.filter(owner=user).values("state").annotate(count=Count("id"))
    by_state = {row["state"]: row["count"] for row in rows}
    return {
        "total": sum(by_state.values()),
        "by_state": [{"state": value, "label": label, "count": by_state.get(value, 0)} for value, label in ThesisState.choices],
    }


def normalize_search_suggestions(payload: dict, company: str) -> list[dict]:
    suggestions: list[dict] = []
    groups = payload.get("results") or payload
    for row in group_items(groups, "companies"):
        if company and row.get("slug") != company:
            continue
        suggestions.append({"evidence_type": EvidenceType.COMPANY, "company_slug": row.get("slug", ""), "external_id": str(row.get("id", "")), "title": row.get("name", "Company"), "summary": row.get("description", "") or row.get("sector", ""), "source_payload": row})
    for key, evidence_type in (("events", EvidenceType.EVENT), ("strategic_turns", EvidenceType.STRATEGIC_TURN), ("sources", EvidenceType.SOURCE)):
        for row in group_items(groups, key):
            row_company = row.get("company_slug") or row.get("company", {}).get("slug", "")
            if company and row_company and row_company != company:
                continue
            suggestions.append(
                {
                    "evidence_type": evidence_type,
                    "company_slug": row_company,
                    "external_id": str(row.get("id", "")),
                    "title": row.get("title") or row.get("event_type") or row.get("summary") or "Evidence",
                    "summary": row.get("summary") or row.get("actual_change") or row.get("snippet") or "",
                    "source_url": row.get("url", ""),
                    "source_date": row.get("event_date") or row.get("start_date") or row.get("published_date"),
                    "source_payload": row,
                }
            )
    return suggestions[:20]


def group_items(groups: dict, key: str) -> list[dict]:
    rows = groups.get(key, [])
    if isinstance(rows, dict):
        rows = rows.get("items", [])
    return rows if isinstance(rows, list) else []


def ingestion_get(path: str, params: dict[str, object] | None = None) -> tuple[dict | None, str]:
    base_url = settings.INGESTION_API_URL.rstrip("/") + "/"
    url = urljoin(base_url, path)
    try:
        response = requests.get(url, params=params, timeout=INGESTION_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json(), ""
    except requests.RequestException as exc:
        return None, str(exc)
    except ValueError as exc:
        return None, f"Invalid JSON from ingestion service: {exc}"


def clean_string(value) -> str:
    return str(value or "").strip()


def choice_value(value, choices, default):
    value = clean_string(value).upper()
    return value if value in choices else default


def parse_date(value) -> date | None:
    value = clean_string(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_decimal(value, default: Decimal) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def list_payload(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def dict_payload(value) -> dict:
    return value if isinstance(value, dict) else {}

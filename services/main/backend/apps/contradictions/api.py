from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.db.models import Q
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.contradictions.models import (
    ConflictType,
    ContradictionCase,
    ContradictionCategory,
    ContradictionClaim,
    ContradictionResolution,
    Materiality,
    ReviewLabel,
)


INGESTION_TIMEOUT_SECONDS = 10


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def contradiction_cases(request):
    if request.method == "POST":
        case = ContradictionCase.objects.create(
            owner=request.user,
            company_slug=clean_string(request.data.get("company_slug")),
            company_name=clean_string(request.data.get("company_name")),
            title=clean_string(request.data.get("title")) or "Untitled contradiction review",
            category=choice_value(request.data.get("category"), ContradictionCategory.values, ContradictionCategory.SOURCE_VS_SOURCE),
            conflict_type=choice_value(request.data.get("conflict_type"), ConflictType.values, ConflictType.CONTRADICTION),
            review_label=ReviewLabel.UNREVIEWED,
            materiality=choice_value(request.data.get("materiality"), Materiality.values, Materiality.MEDIUM),
            confidence_score=parse_decimal(request.data.get("confidence_score"), Decimal("0")),
            neutral_summary=clean_string(request.data.get("neutral_summary")),
            explanation=clean_string(request.data.get("explanation")),
            correction_path=clean_string(request.data.get("correction_path")),
        )
        for claim in request.data.get("claims", []) if isinstance(request.data.get("claims"), list) else []:
            create_claim(case, claim)
        return Response({"case": serialize_case(case)}, status=201)

    rows = ContradictionCase.objects.filter(owner=request.user).prefetch_related("claims", "resolutions")
    if request.GET.get("company"):
        rows = rows.filter(company_slug=request.GET["company"])
    if request.GET.get("review_label"):
        rows = rows.filter(review_label=request.GET["review_label"])
    if request.GET.get("category"):
        rows = rows.filter(category=request.GET["category"])
    if request.GET.get("q"):
        q = request.GET["q"].strip()
        rows = rows.filter(Q(title__icontains=q) | Q(neutral_summary__icontains=q) | Q(company_name__icontains=q))
    return Response(
        {
            "cases": [serialize_case(row, compact=True) for row in rows],
            "categories": [{"value": value, "label": label} for value, label in ContradictionCategory.choices],
            "conflict_types": [{"value": value, "label": label} for value, label in ConflictType.choices],
            "review_labels": [{"value": value, "label": label} for value, label in ReviewLabel.choices],
            "materialities": [{"value": value, "label": label} for value, label in Materiality.choices],
            "neutrality_note": neutrality_note(),
        }
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def contradiction_detail(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    if request.method == "DELETE":
        case.delete()
        return Response({"status": "deleted"})
    if request.method == "PATCH":
        update_case(case, request.data)
        case.save()
    return Response({"case": serialize_case(get_owned_case(request.user, case_id))})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contradiction_claims(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    claim = create_claim(case, request.data)
    case.save(update_fields=["updated_at"])
    return Response({"claim": serialize_claim(claim)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contradiction_review(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    previous = case.review_label
    new_label = choice_value(request.data.get("review_label"), ReviewLabel.values, case.review_label)
    case.review_label = new_label
    case.conflict_type = choice_value(request.data.get("conflict_type"), ConflictType.values, case.conflict_type)
    case.explanation = clean_string(request.data.get("explanation")) or case.explanation
    case.correction_path = clean_string(request.data.get("correction_path")) or case.correction_path
    case.is_published = bool(request.data.get("is_published", False)) and new_label != ReviewLabel.UNREVIEWED
    case.save()
    resolution = ContradictionResolution.objects.create(
        case=case,
        changed_by=request.user,
        previous_label=previous,
        new_label=new_label,
        explanation=case.explanation or "Human review updated the contradiction label.",
    )
    return Response({"case": serialize_case(case), "resolution": serialize_resolution(resolution)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contradiction_evidence_suggestions(request):
    query = clean_string(request.GET.get("q")) or clean_string(request.GET.get("company"))
    company = clean_string(request.GET.get("company"))
    if not query:
        return Response({"suggestions": [], "source_gaps": [{"key": "query_required", "reason": "Provide q or company to find possible claim evidence."}]})
    payload, error = ingestion_get("search", {"q": query, "language": "en", "limit": request.GET.get("limit") or 8})
    if error:
        return Response({"suggestions": [], "source_gaps": [{"key": "contradiction_evidence_unavailable", "reason": error}]}, status=503)
    return Response({"suggestions": normalize_evidence(payload or {}, company), "source_gaps": []})


def create_claim(case: ContradictionCase, payload: dict) -> ContradictionClaim:
    return ContradictionClaim.objects.create(
        case=case,
        label=clean_string(payload.get("label")) or "Claim",
        claim_text=clean_string(payload.get("claim_text")),
        claim_date=parse_date(payload.get("claim_date")),
        speaker=clean_string(payload.get("speaker")),
        scope=clean_string(payload.get("scope")),
        source_label=clean_string(payload.get("source_label")),
        source_url=clean_string(payload.get("source_url")),
        source_type=clean_string(payload.get("source_type")),
        source_payload=payload.get("source_payload") if isinstance(payload.get("source_payload"), dict) else {},
    )


def update_case(case: ContradictionCase, payload: dict) -> None:
    for field in ("company_slug", "company_name", "title", "neutral_summary", "explanation", "correction_path"):
        if field in payload:
            setattr(case, field, clean_string(payload.get(field)))
    if "category" in payload:
        case.category = choice_value(payload.get("category"), ContradictionCategory.values, case.category)
    if "conflict_type" in payload:
        case.conflict_type = choice_value(payload.get("conflict_type"), ConflictType.values, case.conflict_type)
    if "materiality" in payload:
        case.materiality = choice_value(payload.get("materiality"), Materiality.values, case.materiality)
    if "confidence_score" in payload:
        case.confidence_score = parse_decimal(payload.get("confidence_score"), case.confidence_score)


def serialize_case(case: ContradictionCase, compact: bool = False) -> dict:
    payload = {
        "id": case.id,
        "company_slug": case.company_slug,
        "company_name": case.company_name,
        "title": case.title,
        "category": case.category,
        "category_label": case.get_category_display(),
        "conflict_type": case.conflict_type,
        "conflict_type_label": case.get_conflict_type_display(),
        "review_label": case.review_label,
        "review_label_display": case.get_review_label_display(),
        "materiality": case.materiality,
        "materiality_label": case.get_materiality_display(),
        "confidence_score": float(case.confidence_score),
        "neutral_summary": case.neutral_summary,
        "explanation": case.explanation,
        "correction_path": case.correction_path,
        "human_review_required": case.human_review_required,
        "is_published": case.is_published,
        "neutrality_note": neutrality_note(),
        "updated_at": case.updated_at.isoformat(),
    }
    if not compact:
        payload["claims"] = [serialize_claim(row) for row in case.claims.all()]
        payload["resolutions"] = [serialize_resolution(row) for row in case.resolutions.all()]
    return payload


def serialize_claim(claim: ContradictionClaim) -> dict:
    return {
        "id": claim.id,
        "label": claim.label,
        "claim_text": claim.claim_text,
        "claim_date": claim.claim_date.isoformat() if claim.claim_date else None,
        "speaker": claim.speaker,
        "scope": claim.scope,
        "source_label": claim.source_label,
        "source_url": claim.source_url,
        "source_type": claim.source_type,
        "source_payload": claim.source_payload,
    }


def serialize_resolution(row: ContradictionResolution) -> dict:
    return {
        "id": row.id,
        "previous_label": row.previous_label,
        "new_label": row.new_label,
        "explanation": row.explanation,
        "changed_by": row.changed_by.username,
        "created_at": row.created_at.isoformat(),
    }


def normalize_evidence(payload: dict, company: str) -> list[dict]:
    groups = payload.get("results") or {}
    suggestions = []
    for key, source_type in (("companies", "COMPANY"), ("events", "EVENT"), ("strategic_turns", "STRATEGIC_TURN"), ("sources", "SOURCE")):
        for row in group_items(groups, key):
            row_company = row.get("slug") if key == "companies" else row.get("company_slug", "")
            if company and row_company and row_company != company:
                continue
            suggestions.append(
                {
                    "source_type": source_type,
                    "source_id": str(row.get("id", "")),
                    "company_slug": row_company,
                    "title": row.get("name") or row.get("title") or row.get("event_type") or "Evidence",
                    "claim_text": row.get("actual_change") or row.get("summary") or row.get("sector") or "",
                    "source_url": row.get("url", ""),
                    "source_payload": row,
                }
            )
    return suggestions[:20]


def get_owned_case(user, case_id: int) -> ContradictionCase:
    try:
        return ContradictionCase.objects.filter(owner=user).prefetch_related("claims", "resolutions").get(id=case_id)
    except ContradictionCase.DoesNotExist as exc:
        raise Http404("Contradiction case not found") from exc


def group_items(groups: dict, key: str) -> list[dict]:
    rows = groups.get(key, [])
    if isinstance(rows, dict):
        rows = rows.get("items", [])
    return rows if isinstance(rows, list) else []


def neutrality_note() -> str:
    return "This view compares sourced claims neutrally. It must not imply deception, intent, or wrongdoing without authoritative support."


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


def choice_value(value, choices, default):
    value = clean_string(value).upper()
    return value if value in choices else default


def clean_string(value) -> str:
    return str(value or "").strip()


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

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

from apps.failures.models import (
    EditorialStatus,
    FailureCategory,
    FailureClassification,
    FailureEvidence,
    FailureRelatedLink,
    FailureReview,
    FailureStage,
    FailureWarningSign,
    RelatedFeatureType,
    StrategyFailureCase,
)


INGESTION_TIMEOUT_SECONDS = 10


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def failure_cases(request):
    if request.method == "POST":
        case = StrategyFailureCase.objects.create(
            owner=request.user,
            title=clean_string(request.data.get("title")) or "Untitled strategy failure case",
            company_slug=clean_string(request.data.get("company_slug")),
            company_name=clean_string(request.data.get("company_name")),
            sector=clean_string(request.data.get("sector")),
            category=choice_value(request.data.get("category"), FailureCategory.values, FailureCategory.EXECUTION_BREAKDOWN),
            classification=choice_value(request.data.get("classification"), FailureClassification.values, FailureClassification.TOO_EARLY),
            stage=choice_value(request.data.get("stage"), FailureStage.values, FailureStage.THESIS),
            decision_date=parse_date(request.data.get("decision_date")),
            review_start=parse_date(request.data.get("review_start")),
            review_end=parse_date(request.data.get("review_end")),
            minimum_evidence=clean_string(request.data.get("minimum_evidence")),
            elapsed_time_definition=clean_string(request.data.get("elapsed_time_definition")),
            decision_context=clean_string(request.data.get("decision_context")),
            management_rationale=clean_string(request.data.get("management_rationale")),
            original_thesis=clean_string(request.data.get("original_thesis")),
            expected_result=clean_string(request.data.get("expected_result")),
            execution_issue=clean_string(request.data.get("execution_issue")),
            outcome_definition=clean_string(request.data.get("outcome_definition")),
            actual_outcome=clean_string(request.data.get("actual_outcome")),
            counterexamples=clean_string(request.data.get("counterexamples")),
            lessons=clean_string(request.data.get("lessons")),
            correction_path=clean_string(request.data.get("correction_path")),
            confidence_score=parse_decimal(request.data.get("confidence_score"), Decimal("0")),
        )
        for evidence in list_payload(request.data.get("evidence")):
            create_evidence(case, evidence)
        for warning in list_payload(request.data.get("warning_signs")):
            create_warning(case, warning)
        for link in list_payload(request.data.get("related_links")):
            create_related_link(case, link)
        sync_counts(case)
        return Response({"case": serialize_case(case)}, status=201)

    rows = StrategyFailureCase.objects.filter(owner=request.user).prefetch_related("evidence", "warning_signs", "related_links", "reviews")
    if request.GET.get("company"):
        rows = rows.filter(company_slug=request.GET["company"])
    if request.GET.get("category"):
        rows = rows.filter(category=request.GET["category"])
    if request.GET.get("classification"):
        rows = rows.filter(classification=request.GET["classification"])
    if request.GET.get("stage"):
        rows = rows.filter(stage=request.GET["stage"])
    if request.GET.get("sector"):
        rows = rows.filter(sector__iexact=request.GET["sector"])
    if request.GET.get("outcome"):
        rows = rows.filter(Q(outcome_definition__icontains=request.GET["outcome"]) | Q(actual_outcome__icontains=request.GET["outcome"]))
    if request.GET.get("q"):
        q = request.GET["q"].strip()
        rows = rows.filter(Q(title__icontains=q) | Q(company_name__icontains=q) | Q(decision_context__icontains=q) | Q(lessons__icontains=q))
    return Response(
        {
            "cases": [serialize_case(row, compact=True) for row in rows],
            "categories": choices(FailureCategory),
            "classifications": choices(FailureClassification),
            "stages": choices(FailureStage),
            "editorial_statuses": choices(EditorialStatus),
            "related_feature_types": choices(RelatedFeatureType),
            "guardrail_note": guardrail_note(),
        }
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def failure_detail(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    if request.method == "DELETE":
        case.delete()
        return Response({"status": "deleted"})
    if request.method == "PATCH":
        update_case(case, request.data)
        case.save()
        sync_counts(case)
    return Response({"case": serialize_case(get_owned_case(request.user, case_id))})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def failure_evidence(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    evidence = create_evidence(case, request.data)
    sync_counts(case)
    return Response({"evidence": serialize_evidence(evidence)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def failure_warning_signs(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    warning = create_warning(case, request.data)
    sync_counts(case)
    return Response({"warning_sign": serialize_warning(warning)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def failure_related_links(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    link = create_related_link(case, request.data)
    return Response({"related_link": serialize_related_link(link)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def failure_review(request, case_id: int):
    case = get_owned_case(request.user, case_id)
    previous = case.editorial_status
    new_status = choice_value(request.data.get("editorial_status"), EditorialStatus.values, case.editorial_status)
    case.editorial_status = new_status
    case.classification = choice_value(request.data.get("classification"), FailureClassification.values, case.classification)
    if "confidence_score" in request.data:
        case.confidence_score = parse_decimal(request.data.get("confidence_score"), case.confidence_score)
    case.correction_path = clean_string(request.data.get("correction_path")) or case.correction_path
    case.is_published = bool(request.data.get("is_published", False)) and publishable(case, new_status)
    case.save()
    review = FailureReview.objects.create(
        case=case,
        changed_by=request.user,
        previous_status=previous,
        new_status=new_status,
        classification=case.classification,
        note=clean_string(request.data.get("note")) or "Editorial review updated the failure case.",
    )
    return Response({"case": serialize_case(case), "review": serialize_review(review)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def failure_evidence_suggestions(request):
    query = clean_string(request.GET.get("q")) or clean_string(request.GET.get("company"))
    company = clean_string(request.GET.get("company"))
    if not query:
        return Response({"suggestions": [], "source_gaps": [{"key": "query_required", "reason": "Provide q or company to find source-backed failure evidence."}]})
    payload, error = ingestion_get("search", {"q": query, "language": "en", "limit": request.GET.get("limit") or 8})
    if error:
        return Response({"suggestions": [], "source_gaps": [{"key": "failure_evidence_unavailable", "reason": error}]}, status=503)
    return Response({"suggestions": normalize_evidence(payload or {}, company), "source_gaps": []})


def create_evidence(case: StrategyFailureCase, payload: dict) -> FailureEvidence:
    return FailureEvidence.objects.create(
        case=case,
        evidence_type=clean_string(payload.get("evidence_type")),
        label=clean_string(payload.get("label")) or "Evidence",
        summary=clean_string(payload.get("summary")),
        evidence_date=parse_date(payload.get("evidence_date")),
        source_url=clean_string(payload.get("source_url")),
        source_payload=payload.get("source_payload") if isinstance(payload.get("source_payload"), dict) else {},
    )


def create_warning(case: StrategyFailureCase, payload: dict) -> FailureWarningSign:
    return FailureWarningSign.objects.create(
        case=case,
        signal_date=parse_date(payload.get("signal_date")),
        signal=clean_string(payload.get("signal")) or "Warning sign",
        why_it_mattered=clean_string(payload.get("why_it_mattered")),
        observable_at_time=bool(payload.get("observable_at_time", True)),
        source_label=clean_string(payload.get("source_label")),
        source_url=clean_string(payload.get("source_url")),
    )


def create_related_link(case: StrategyFailureCase, payload: dict) -> FailureRelatedLink:
    return FailureRelatedLink.objects.create(
        case=case,
        feature_type=choice_value(payload.get("feature_type"), RelatedFeatureType.values, RelatedFeatureType.OTHER),
        object_label=clean_string(payload.get("object_label")) or "Related record",
        object_id=clean_string(payload.get("object_id")),
        relationship_note=clean_string(payload.get("relationship_note")),
        source_url=clean_string(payload.get("source_url")),
    )


def update_case(case: StrategyFailureCase, payload: dict) -> None:
    for field in (
        "title",
        "company_slug",
        "company_name",
        "sector",
        "minimum_evidence",
        "elapsed_time_definition",
        "decision_context",
        "management_rationale",
        "original_thesis",
        "expected_result",
        "execution_issue",
        "outcome_definition",
        "actual_outcome",
        "counterexamples",
        "lessons",
        "correction_path",
    ):
        if field in payload:
            setattr(case, field, clean_string(payload.get(field)))
    for field in ("decision_date", "review_start", "review_end"):
        if field in payload:
            setattr(case, field, parse_date(payload.get(field)))
    if "category" in payload:
        case.category = choice_value(payload.get("category"), FailureCategory.values, case.category)
    if "classification" in payload:
        case.classification = choice_value(payload.get("classification"), FailureClassification.values, case.classification)
    if "stage" in payload:
        case.stage = choice_value(payload.get("stage"), FailureStage.values, case.stage)
    if "confidence_score" in payload:
        case.confidence_score = parse_decimal(payload.get("confidence_score"), case.confidence_score)


def serialize_case(case: StrategyFailureCase, compact: bool = False) -> dict:
    payload = {
        "id": case.id,
        "title": case.title,
        "company_slug": case.company_slug,
        "company_name": case.company_name,
        "sector": case.sector,
        "category": case.category,
        "category_label": case.get_category_display(),
        "classification": case.classification,
        "classification_label": case.get_classification_display(),
        "stage": case.stage,
        "stage_label": case.get_stage_display(),
        "decision_date": case.decision_date.isoformat() if case.decision_date else None,
        "review_start": case.review_start.isoformat() if case.review_start else None,
        "review_end": case.review_end.isoformat() if case.review_end else None,
        "minimum_evidence": case.minimum_evidence,
        "elapsed_time_definition": case.elapsed_time_definition,
        "decision_context": case.decision_context,
        "management_rationale": case.management_rationale,
        "original_thesis": case.original_thesis,
        "expected_result": case.expected_result,
        "execution_issue": case.execution_issue,
        "outcome_definition": case.outcome_definition,
        "actual_outcome": case.actual_outcome,
        "counterexamples": case.counterexamples,
        "lessons": case.lessons,
        "correction_path": case.correction_path,
        "editorial_status": case.editorial_status,
        "editorial_status_label": case.get_editorial_status_display(),
        "evidence_count": case.evidence_count,
        "warning_sign_count": case.warning_sign_count,
        "confidence_score": float(case.confidence_score),
        "is_published": case.is_published,
        "guardrail_note": guardrail_note(),
        "updated_at": case.updated_at.isoformat(),
        "created_at": case.created_at.isoformat(),
    }
    if not compact:
        payload["evidence"] = [serialize_evidence(row) for row in case.evidence.all()]
        payload["warning_signs"] = [serialize_warning(row) for row in case.warning_signs.all()]
        payload["related_links"] = [serialize_related_link(row) for row in case.related_links.all()]
        payload["reviews"] = [serialize_review(row) for row in case.reviews.all()]
        payload["quality"] = quality_summary(case)
    return payload


def serialize_evidence(evidence: FailureEvidence) -> dict:
    return {
        "id": evidence.id,
        "evidence_type": evidence.evidence_type,
        "label": evidence.label,
        "summary": evidence.summary,
        "evidence_date": evidence.evidence_date.isoformat() if evidence.evidence_date else None,
        "source_url": evidence.source_url,
        "source_payload": evidence.source_payload,
    }


def serialize_warning(warning: FailureWarningSign) -> dict:
    return {
        "id": warning.id,
        "signal_date": warning.signal_date.isoformat() if warning.signal_date else None,
        "signal": warning.signal,
        "why_it_mattered": warning.why_it_mattered,
        "observable_at_time": warning.observable_at_time,
        "source_label": warning.source_label,
        "source_url": warning.source_url,
    }


def serialize_related_link(link: FailureRelatedLink) -> dict:
    return {
        "id": link.id,
        "feature_type": link.feature_type,
        "feature_type_label": link.get_feature_type_display(),
        "object_label": link.object_label,
        "object_id": link.object_id,
        "relationship_note": link.relationship_note,
        "source_url": link.source_url,
    }


def serialize_review(review: FailureReview) -> dict:
    return {
        "id": review.id,
        "previous_status": review.previous_status,
        "new_status": review.new_status,
        "classification": review.classification,
        "note": review.note,
        "changed_by": review.changed_by.username,
        "created_at": review.created_at.isoformat(),
    }


def quality_summary(case: StrategyFailureCase) -> dict:
    checks = {
        "has_outcome_definition": bool(case.outcome_definition),
        "has_review_period": bool(case.review_start and case.review_end),
        "has_minimum_evidence": bool(case.minimum_evidence),
        "has_evidence": case.evidence_count > 0,
        "has_warning_signs": case.warning_sign_count > 0,
        "has_management_rationale": bool(case.management_rationale),
        "has_correction_path": bool(case.correction_path),
    }
    return {"checks": checks, "ready_for_review": all(checks.values())}


def sync_counts(case: StrategyFailureCase) -> None:
    case.evidence_count = case.evidence.count()
    case.warning_sign_count = case.warning_signs.count()
    case.save(update_fields=["evidence_count", "warning_sign_count", "updated_at"])


def publishable(case: StrategyFailureCase, status: str) -> bool:
    case.evidence_count = case.evidence.count()
    case.warning_sign_count = case.warning_signs.count()
    return (
        status == EditorialStatus.REVIEWED
        and bool(case.outcome_definition)
        and bool(case.minimum_evidence)
        and bool(case.review_start and case.review_end)
        and case.evidence_count > 0
        and case.warning_sign_count > 0
    )


def normalize_evidence(payload: dict, company: str) -> list[dict]:
    groups = payload.get("results") or {}
    suggestions = []
    for key, evidence_type in (("companies", "COMPANY"), ("events", "EVENT"), ("strategic_turns", "STRATEGIC_TURN"), ("sources", "SOURCE")):
        for row in group_items(groups, key):
            row_company = row.get("slug") if key == "companies" else row.get("company_slug", "")
            if company and row_company and row_company != company:
                continue
            suggestions.append(
                {
                    "evidence_type": evidence_type,
                    "evidence_id": str(row.get("id", "")),
                    "company_slug": row_company,
                    "title": row.get("name") or row.get("title") or row.get("event_type") or "Evidence",
                    "summary": row.get("summary") or row.get("actual_change") or row.get("sector") or "",
                    "url": row.get("url", ""),
                }
            )
    return suggestions[:20]


def get_owned_case(user, case_id: int) -> StrategyFailureCase:
    try:
        return StrategyFailureCase.objects.filter(owner=user).prefetch_related("evidence", "warning_signs", "related_links", "reviews").get(id=case_id)
    except StrategyFailureCase.DoesNotExist as exc:
        raise Http404("Strategy failure case not found") from exc


def group_items(groups: dict, key: str) -> list[dict]:
    rows = groups.get(key, [])
    if isinstance(rows, dict):
        rows = rows.get("items", [])
    return rows if isinstance(rows, list) else []


def choices(enum_class) -> list[dict]:
    return [{"value": value, "label": label} for value, label in enum_class.choices]


def list_payload(value) -> list[dict]:
    return value if isinstance(value, list) else []


def guardrail_note() -> str:
    return "Failure cases require elapsed review time, visible evidence, management rationale, warning signs observable at the time, and editorial review before publication."


def parse_date(value) -> date | None:
    value = clean_string(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_decimal(value, default=None):
    value = clean_string(value)
    if not value:
        return default
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
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

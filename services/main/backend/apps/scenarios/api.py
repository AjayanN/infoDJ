from __future__ import annotations

from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.db.models import Q
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.scenarios.models import (
    ScenarioActualResult,
    ScenarioAssumption,
    ScenarioCase,
    ScenarioDriverType,
    ScenarioIndicator,
    ScenarioIndicatorStatus,
    ScenarioKind,
    ScenarioRevision,
    ScenarioSet,
    ScenarioSetStatus,
    ScenarioSourceType,
)


INGESTION_TIMEOUT_SECONDS = 10


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def scenario_sets(request):
    if request.method == "POST":
        scenario_set = ScenarioSet.objects.create(
            owner=request.user,
            title=clean_string(request.data.get("title")) or "Untitled scenario set",
            company_slug=clean_string(request.data.get("company_slug")),
            company_name=clean_string(request.data.get("company_name")),
            thesis=clean_string(request.data.get("thesis")),
            horizon_start=parse_date(request.data.get("horizon_start")),
            horizon_end=parse_date(request.data.get("horizon_end")),
            status=choice_value(request.data.get("status"), ScenarioSetStatus.values, ScenarioSetStatus.DRAFT),
            source_type=choice_value(request.data.get("source_type"), ScenarioSourceType.values, ScenarioSourceType.USER_CREATED),
            is_shared=bool(request.data.get("is_shared", False)),
        )
        create_default_cases(scenario_set)
        ScenarioRevision.objects.create(
            scenario_set=scenario_set,
            changed_by=request.user,
            previous_status="",
            new_status=scenario_set.status,
            reason="Scenario set created.",
        )
        return Response({"scenario_set": serialize_scenario_set(scenario_set)}, status=201)

    rows = ScenarioSet.objects.filter(owner=request.user).prefetch_related("cases__assumptions", "indicators", "actual_results", "revisions")
    if request.GET.get("company"):
        rows = rows.filter(company_slug=request.GET["company"])
    if request.GET.get("status"):
        rows = rows.filter(status=request.GET["status"])
    if request.GET.get("q"):
        q = request.GET["q"].strip()
        rows = rows.filter(Q(title__icontains=q) | Q(thesis__icontains=q) | Q(company_name__icontains=q))
    return Response(
        {
            "scenario_sets": [serialize_scenario_set(row, compact=True) for row in rows],
            "templates": scenario_templates(),
            "statuses": [{"value": value, "label": label} for value, label in ScenarioSetStatus.choices],
            "driver_types": [{"value": value, "label": label} for value, label in ScenarioDriverType.choices],
            "non_prediction_note": "Scenarios are assumption workspaces, not predictions, investment advice, or probability-weighted forecasts.",
        }
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def scenario_detail(request, scenario_id: int):
    scenario_set = get_owned_scenario(request.user, scenario_id)
    if request.method == "DELETE":
        scenario_set.delete()
        return Response({"status": "deleted"})
    if request.method == "PATCH":
        previous_status = scenario_set.status
        update_scenario_set(scenario_set, request.data)
        scenario_set.save()
        if scenario_set.status != previous_status:
            ScenarioRevision.objects.create(
                scenario_set=scenario_set,
                changed_by=request.user,
                previous_status=previous_status,
                new_status=scenario_set.status,
                reason=clean_string(request.data.get("reason")) or "Scenario status updated.",
            )
    return Response({"scenario_set": serialize_scenario_set(get_owned_scenario(request.user, scenario_id))})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def scenario_case_detail(request, scenario_id: int, case_id: int):
    scenario_set = get_owned_scenario(request.user, scenario_id)
    case = get_child(scenario_set.cases, case_id)
    for field in ("title", "narrative", "qualitative_outcome", "unit", "probability_label"):
        if field in request.data:
            setattr(case, field, clean_string(request.data.get(field)))
    if "low_value" in request.data:
        case.low_value = parse_decimal(request.data.get("low_value"))
    if "high_value" in request.data:
        case.high_value = parse_decimal(request.data.get("high_value"))
    case.save()
    scenario_set.save(update_fields=["updated_at"])
    return Response({"case": serialize_case(case)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def scenario_assumptions(request, scenario_id: int, case_id: int):
    scenario_set = get_owned_scenario(request.user, scenario_id)
    case = get_child(scenario_set.cases, case_id)
    assumption = ScenarioAssumption.objects.create(
        scenario_case=case,
        driver_type=choice_value(request.data.get("driver_type"), ScenarioDriverType.values, ScenarioDriverType.OTHER),
        driver_label=clean_string(request.data.get("driver_label")) or "Assumption driver",
        assumption=clean_string(request.data.get("assumption")),
        rationale=clean_string(request.data.get("rationale")),
        evidence_type=clean_string(request.data.get("evidence_type")),
        evidence_id=clean_string(request.data.get("evidence_id")),
        evidence_label=clean_string(request.data.get("evidence_label")),
        evidence_url=clean_string(request.data.get("evidence_url")),
        confidence_label=clean_string(request.data.get("confidence_label")),
    )
    scenario_set.save(update_fields=["updated_at"])
    return Response({"assumption": serialize_assumption(assumption), "differences": assumption_differences(scenario_set)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def scenario_indicators(request, scenario_id: int):
    scenario_set = get_owned_scenario(request.user, scenario_id)
    indicator = ScenarioIndicator.objects.create(
        scenario_set=scenario_set,
        name=clean_string(request.data.get("name")) or "Scenario indicator",
        driver_type=choice_value(request.data.get("driver_type"), ScenarioDriverType.values, ScenarioDriverType.OTHER),
        target=clean_string(request.data.get("target")),
        current_value=clean_string(request.data.get("current_value")),
        status=choice_value(request.data.get("status"), ScenarioIndicatorStatus.values, ScenarioIndicatorStatus.UNKNOWN),
        source_hint=clean_string(request.data.get("source_hint")),
    )
    scenario_set.save(update_fields=["updated_at"])
    return Response({"indicator": serialize_indicator(indicator)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def scenario_actual_results(request, scenario_id: int):
    scenario_set = get_owned_scenario(request.user, scenario_id)
    result = ScenarioActualResult.objects.create(
        scenario_set=scenario_set,
        result_date=parse_date(request.data.get("result_date")),
        metric_label=clean_string(request.data.get("metric_label")) or "Actual result",
        actual_value=clean_string(request.data.get("actual_value")),
        comparison_note=clean_string(request.data.get("comparison_note")),
        evidence_label=clean_string(request.data.get("evidence_label")),
        evidence_url=clean_string(request.data.get("evidence_url")),
    )
    scenario_set.save(update_fields=["updated_at"])
    return Response({"actual_result": serialize_actual_result(result)}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scenario_evidence_suggestions(request):
    query = clean_string(request.GET.get("q")) or clean_string(request.GET.get("company"))
    company = clean_string(request.GET.get("company"))
    if not query:
        return Response({"suggestions": [], "source_gaps": [{"key": "query_required", "reason": "Provide q or company to find source-backed drivers."}]})
    payload, error = ingestion_get("search", {"q": query, "language": "en", "limit": request.GET.get("limit") or 8})
    if error:
        return Response({"suggestions": [], "source_gaps": [{"key": "scenario_evidence_unavailable", "reason": error}]}, status=503)
    return Response({"suggestions": normalize_evidence(payload or {}, company), "source_gaps": []})


def create_default_cases(scenario_set: ScenarioSet) -> None:
    defaults = {
        ScenarioKind.BEST: "Upside case",
        ScenarioKind.BASE: "Base case",
        ScenarioKind.WORST: "Downside case",
    }
    for kind, title in defaults.items():
        ScenarioCase.objects.create(
            scenario_set=scenario_set,
            kind=kind,
            title=title,
            narrative="Add explicit assumptions, ranges, indicators, and evidence before using this case.",
            qualitative_outcome="Outcome not specified.",
        )


def scenario_templates() -> list[dict]:
    return [
        {"kind": ScenarioKind.BEST, "required_fields": ["narrative", "assumptions", "indicator", "evidence"]},
        {"kind": ScenarioKind.BASE, "required_fields": ["narrative", "assumptions", "indicator", "evidence"]},
        {"kind": ScenarioKind.WORST, "required_fields": ["narrative", "assumptions", "indicator", "evidence"]},
    ]


def update_scenario_set(scenario_set: ScenarioSet, payload: dict) -> None:
    for field in ("title", "company_slug", "company_name", "thesis"):
        if field in payload:
            setattr(scenario_set, field, clean_string(payload.get(field)))
    if "horizon_start" in payload:
        scenario_set.horizon_start = parse_date(payload.get("horizon_start"))
    if "horizon_end" in payload:
        scenario_set.horizon_end = parse_date(payload.get("horizon_end"))
    if "status" in payload:
        scenario_set.status = choice_value(payload.get("status"), ScenarioSetStatus.values, scenario_set.status)
    if "is_shared" in payload:
        scenario_set.is_shared = bool(payload.get("is_shared"))


def serialize_scenario_set(scenario_set: ScenarioSet, compact: bool = False) -> dict:
    payload = {
        "id": scenario_set.id,
        "title": scenario_set.title,
        "company_slug": scenario_set.company_slug,
        "company_name": scenario_set.company_name,
        "thesis": scenario_set.thesis,
        "horizon_start": scenario_set.horizon_start.isoformat() if scenario_set.horizon_start else None,
        "horizon_end": scenario_set.horizon_end.isoformat() if scenario_set.horizon_end else None,
        "status": scenario_set.status,
        "status_label": scenario_set.get_status_display(),
        "source_type": scenario_set.source_type,
        "source_type_label": scenario_set.get_source_type_display(),
        "non_prediction_note": scenario_set.non_prediction_note,
        "is_shared": scenario_set.is_shared,
        "updated_at": scenario_set.updated_at.isoformat(),
        "created_at": scenario_set.created_at.isoformat(),
    }
    if not compact:
        payload.update(
            {
                "cases": [serialize_case(row) for row in scenario_set.cases.all()],
                "indicators": [serialize_indicator(row) for row in scenario_set.indicators.all()],
                "actual_results": [serialize_actual_result(row) for row in scenario_set.actual_results.all()],
                "revisions": [serialize_revision(row) for row in scenario_set.revisions.all()],
                "differences": assumption_differences(scenario_set),
            }
        )
    return payload


def serialize_case(case: ScenarioCase) -> dict:
    return {
        "id": case.id,
        "kind": case.kind,
        "kind_label": case.get_kind_display(),
        "title": case.title,
        "narrative": case.narrative,
        "qualitative_outcome": case.qualitative_outcome,
        "low_value": float(case.low_value) if case.low_value is not None else None,
        "high_value": float(case.high_value) if case.high_value is not None else None,
        "unit": case.unit,
        "probability_label": case.probability_label,
        "assumptions": [serialize_assumption(row) for row in case.assumptions.all()],
    }


def serialize_assumption(assumption: ScenarioAssumption) -> dict:
    return {
        "id": assumption.id,
        "driver_type": assumption.driver_type,
        "driver_type_label": assumption.get_driver_type_display(),
        "driver_label": assumption.driver_label,
        "assumption": assumption.assumption,
        "rationale": assumption.rationale,
        "evidence_type": assumption.evidence_type,
        "evidence_id": assumption.evidence_id,
        "evidence_label": assumption.evidence_label,
        "evidence_url": assumption.evidence_url,
        "confidence_label": assumption.confidence_label,
    }


def serialize_indicator(indicator: ScenarioIndicator) -> dict:
    return {
        "id": indicator.id,
        "name": indicator.name,
        "driver_type": indicator.driver_type,
        "target": indicator.target,
        "current_value": indicator.current_value,
        "status": indicator.status,
        "status_label": indicator.get_status_display(),
        "source_hint": indicator.source_hint,
    }


def serialize_actual_result(result: ScenarioActualResult) -> dict:
    return {
        "id": result.id,
        "result_date": result.result_date.isoformat(),
        "metric_label": result.metric_label,
        "actual_value": result.actual_value,
        "comparison_note": result.comparison_note,
        "evidence_label": result.evidence_label,
        "evidence_url": result.evidence_url,
    }


def serialize_revision(revision: ScenarioRevision) -> dict:
    return {"id": revision.id, "previous_status": revision.previous_status, "new_status": revision.new_status, "reason": revision.reason, "created_at": revision.created_at.isoformat(), "changed_by": revision.changed_by.username}


def assumption_differences(scenario_set: ScenarioSet) -> list[dict]:
    cases = {case.kind: case for case in scenario_set.cases.all()}
    driver_map: dict[str, dict] = {}
    for kind, case in cases.items():
        for assumption in case.assumptions.all():
            key = f"{assumption.driver_type}:{assumption.driver_label}"
            driver_map.setdefault(key, {"driver_type": assumption.driver_type, "driver_label": assumption.driver_label, "cases": {}})
            driver_map[key]["cases"][kind] = assumption.assumption
    return [row for row in driver_map.values() if len(set(row["cases"].values())) > 1]


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


def get_owned_scenario(user, scenario_id: int) -> ScenarioSet:
    try:
        return ScenarioSet.objects.filter(owner=user).prefetch_related("cases__assumptions", "indicators", "actual_results", "revisions").get(id=scenario_id)
    except ScenarioSet.DoesNotExist as exc:
        raise Http404("Scenario set not found") from exc


def get_child(manager, child_id: int):
    try:
        return manager.get(id=child_id)
    except manager.model.DoesNotExist as exc:
        raise Http404("Record not found") from exc


def group_items(groups: dict, key: str) -> list[dict]:
    rows = groups.get(key, [])
    if isinstance(rows, dict):
        rows = rows.get("items", [])
    return rows if isinstance(rows, list) else []


def parse_date(value):
    value = clean_string(value)
    if not value:
        return None
    from datetime import date

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_decimal(value):
    value = clean_string(value)
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


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

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.core.management import call_command
from django.db import connection
from django.db.models import Avg, Count, Max, Q
from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.companies.models import (
    AcquisitionLifecycleDeal,
    AcquisitionLifecycleEvent,
    AcquisitionOutcomeCategory,
    AcquisitionStage,
    AcquisitionTransactionType,
    BusinessModelComponentType,
    BusinessModelSnapshot,
    CapitalAllocationCategory,
    CapitalAllocationItem,
    CapitalAllocationPeriod,
    Company,
    CompanyProfileSnapshot,
    CompetitiveDimensionType,
    CompetitivePeer,
    CompetitivePositionSnapshot,
    CustomerSupplierDependency,
    CustomerSupplierDependencySnapshot,
    DependencyContractTerm,
    DependencyDisclosureConfidence,
    DependencyMaterialityBand,
    DependencyType,
    EarningsGuidanceComparison,
    EarningsPeriod,
    KpiDefinition,
    KpiObservation,
    ManagementPromise,
    MilestoneStatus,
    PriceObservation,
    ProductCatalogSnapshot,
    ProductChange,
    ProductOffering,
    StrategyMilestone,
)
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import FinancialFact, IngestionJob, MarketPrice, SourceDocument, SourceGap
from apps.ingestion.services.dashboard_quality import (
    RISK_EVENT_TYPES,
    event_eligibility,
    event_source_count,
    risk_event_eligibility,
    section_payload,
    source_gap_dict,
    turn_eligibility,
)
from apps.ingestion.services.capital_allocation import DEPLOYMENT_CATEGORIES


def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok", "service": "infodj-ingestion"})


@require_GET
def companies(_request: HttpRequest) -> JsonResponse:
    source_counts = dict(SourceDocument.objects.values("company_id").annotate(count=Count("id")).values_list("company_id", "count"))
    event_counts = dict(BusinessEvent.objects.values("company_id").annotate(count=Count("id")).values_list("company_id", "count"))
    turn_counts = dict(StrategicTurn.objects.values("company_id").annotate(count=Count("id")).values_list("company_id", "count"))
    kpi_counts = dict(KpiDefinition.objects.values("company_id").annotate(count=Count("id")).values_list("company_id", "count"))
    rows = []
    for company in Company.objects.order_by("industry", "name"):
        rows.append(
            {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "sector": company.industry,
                "country": company.country,
                "wikidata_id": company.wikidata_id,
                "sec_cik": company.sec_cik,
                "source_count": source_counts.get(company.id, 0),
                "event_count": event_counts.get(company.id, 0),
                "strategic_turn_count": turn_counts.get(company.id, 0),
                "kpi_count": kpi_counts.get(company.id, 0),
            }
        )
    return JsonResponse({"companies": rows})


@require_GET
def company_profile(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    snapshots = list(
        CompanyProfileSnapshot.objects.filter(company=company)
        .select_related("source_document")
        .order_by("-effective_date", "-updated_at")[:20]
    )
    as_of = parse_iso_date(request.GET.get("as_of"))
    eligible_snapshots = [
        row
        for row in snapshots
        if row.status in {"PUBLISHED", "REVIEWED"} and (as_of is None or row.effective_date <= as_of)
    ]
    current = eligible_snapshots[0] if eligible_snapshots else None
    effective_dates = list(dict.fromkeys(snapshot.effective_date for snapshot in eligible_snapshots))
    previous_date = effective_dates[1] if len(effective_dates) > 1 else None
    business_model_snapshot = (
        BusinessModelSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .filter(Q(effective_date__lte=as_of) if as_of else Q())
        .order_by("-effective_date", "-updated_at")
        .first()
    )

    events = list(
        BusinessEvent.objects.filter(company=company)
        .exclude(actual_change="")
        .select_related("source_document")
        .order_by("-event_date", "-created_at")[:6]
    )
    turns = list(
        StrategicTurn.objects.filter(company=company)
        .exclude(summary="")
        .order_by("-start_date", "-created_at")[:6]
    )
    turn_source_counts = dict(
        StrategicTurnSource.objects.filter(strategic_turn__in=turns)
        .values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    facts = list(
        FinancialFact.objects.filter(company=company)
        .order_by("-filed", "-fy", "concept")[:8]
    )
    sources = list(SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at")[:12])

    section_values = profile_section_values_from_snapshots(company, eligible_snapshots, business_model_snapshot)
    previous_sections = (
        profile_section_values_from_snapshots(
            company,
            [snapshot for snapshot in eligible_snapshots if snapshot.effective_date <= previous_date],
        )
        if previous_date
        else None
    )
    missing_sections = [key for key, value in section_values.items() if not value]
    source_gaps = [
        {
            "key": f"company_profile_{section}",
            "label": f"{section.replace('_', ' ').title()} unavailable",
            "reason": f"No reviewed, source-backed {section.replace('_', ' ')} information is available for {company.name}.",
            "source": "company-profile",
            "next_action": f"Review official filings and company pages for {section.replace('_', ' ')} data.",
        }
        for section in missing_sections
    ]
    persist_company_profile_gaps(company, source_gaps, section_values)
    completeness = round(((len(section_values) - len(missing_sections)) / len(section_values)) * 100)
    status = "available" if current and completeness == 100 else "partial" if sources or current else "unavailable"

    return JsonResponse(
        {
            "status": status,
            "company": serialize_company_detail(company),
            "profile": serialize_profile_snapshot(current, section_values),
            "snapshot_history": [
                {
                    "id": snapshot.id,
                    "effective_date": snapshot.effective_date.isoformat(),
                    "status": snapshot.status,
                    "confidence_score": decimal_to_float(snapshot.confidence_score),
                    "selected": bool(current and snapshot.id == current.id),
                }
                for snapshot in snapshots
                if snapshot.status in {"PUBLISHED", "REVIEWED"}
            ],
            "sections": {
                key: {
                    "status": "available" if value else "unavailable",
                    "items": value if isinstance(value, list) else [],
                    "text": value if isinstance(value, str) else "",
                    "source": "business_model_map" if key == "business_model" and business_model_snapshot else "company_profile",
                }
                for key, value in section_values.items()
            },
            "highlights": {
                "latest_events": [serialize_business_event(event) for event in events],
                "latest_turns": [serialize_strategic_turn(turn, source_count=turn_source_counts.get(turn.id, 0)) for turn in turns],
                "financial_facts": [serialize_financial_fact(fact) for fact in facts],
            },
            "changes": profile_value_changes(section_values, previous_sections, effective_dates[0] if effective_dates else None, previous_date),
            "conflicts": profile_conflicts(current, snapshots),
            "evidence": [serialize_profile_source(source) for source in sources],
            "coverage": {
                "completeness_percent": completeness,
                "available_sections": len(section_values) - len(missing_sections),
                "total_sections": len(section_values),
                "source_count": SourceDocument.objects.filter(company=company).count(),
                "snapshot_count": len(snapshots),
                "last_updated": max_date_iso(
                    max(
                        [company.updated_at, *[source.updated_at for source in sources], *[snapshot.updated_at for snapshot in snapshots]],
                        default=company.updated_at,
                    )
                ),
            },
            "source_gaps": source_gaps,
        }
    )


@require_GET
def company_business_model(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    snapshots = list(
        BusinessModelSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .select_related("source_document")
        .prefetch_related("components", "relationships__from_component", "relationships__to_component")
        .order_by("-effective_date", "-updated_at")
    )
    as_of = parse_iso_date(request.GET.get("as_of"))
    eligible = [snapshot for snapshot in snapshots if as_of is None or snapshot.effective_date <= as_of]
    current = eligible[0] if eligible else None
    compare_date = parse_iso_date(request.GET.get("compare_to"))
    comparison = next((snapshot for snapshot in snapshots if compare_date and snapshot.effective_date <= compare_date), None)
    if comparison is None and len(eligible) > 1:
        comparison = eligible[1]

    required_types = [choice for choice, _label in BusinessModelComponentType.choices]
    present_types = {component.component_type for component in current.components.all()} if current else set()
    missing_types = [component_type for component_type in required_types if component_type not in present_types]
    labels = dict(BusinessModelComponentType.choices)
    gaps = [
        {
            "key": f"business_model_{component_type.lower()}",
            "label": f"{labels[component_type]} unavailable",
            "reason": f"No reviewed, source-backed {labels[component_type].lower()} component is available for {company.name}.",
            "source": "business-model-map",
            "next_action": "Review filings, investor materials, and permitted official company pages for this component.",
        }
        for component_type in missing_types
    ]
    has_relationships = bool(current and current.relationships.exists())
    if current and not has_relationships:
        gaps.append(
            {
                "key": "business_model_relationships",
                "label": "Business-model relationships unavailable",
                "reason": "Components exist, but no reviewed relationships connect them.",
                "source": "business-model-map",
                "next_action": "Review payer, user, offering, channel, revenue, partner, cost, and asset relationships.",
            }
        )
    persist_business_model_gaps(company, gaps, present_types, has_relationships)
    completeness = round(((len(required_types) - len(missing_types)) / len(required_types)) * 100)
    status = "available" if current and completeness == 100 and has_relationships else "partial" if current else "unavailable"

    return JsonResponse(
        {
            "status": status,
            "company": serialize_company_detail(company),
            "snapshot": serialize_business_model_snapshot(current),
            "snapshot_history": [serialize_business_model_history(row, current) for row in snapshots],
            "comparison_snapshot": serialize_business_model_snapshot(comparison),
            "changes": business_model_changes(current, comparison),
            "peer_models": peer_business_model_rows(company, current),
            "related_surfaces": [
                {"key": "customer_groups", "label": "Customer groups", "status": "available", "destination": "company_profile"},
                {"key": "products", "label": "Products and services", "status": "available", "destination": "company_profile"},
                {"key": "revenue_sources", "label": "Revenue sources", "status": "available", "destination": "company_profile"},
                {"key": "pricing_history", "label": "Product and pricing history", "status": "unavailable", "destination": "phase2_requirement_9"},
                {"key": "supplier_dependency", "label": "Supplier dependencies", "status": "unavailable", "destination": "phase2_requirement_11"},
            ],
            "coverage": {
                "completeness_percent": completeness,
                "component_count": current.components.count() if current else 0,
                "relationship_count": current.relationships.count() if current else 0,
                "required_component_types": len(required_types),
                "available_component_types": len(present_types),
                "last_updated": current.updated_at.isoformat() if current else company.updated_at.isoformat(),
            },
            "evidence": [serialize_profile_source(row.source_document) for row in snapshots if row.source_document_id],
            "source_gaps": gaps,
        }
    )


@require_GET
def company_operating_kpis(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    definitions = list(KpiDefinition.objects.filter(company=company, is_active=True).prefetch_related(
        "definition_versions__source_document", "observations__source_document", "targets"
    ).order_by("name"))
    metric_slug = (request.GET.get("metric") or "").strip()
    selected = next((row for row in definitions if row.slug == metric_slug), definitions[0] if definitions else None)
    segment = (request.GET.get("segment") or "").strip()
    geography = (request.GET.get("geography") or "").strip()
    start_date = parse_iso_date(request.GET.get("start"))
    end_date = parse_iso_date(request.GET.get("end"))
    comparable_only = (request.GET.get("comparable_only") or "").lower() in {"1", "true", "yes"}
    observations = list(selected.observations.all()) if selected else []
    if segment:
        observations = [row for row in observations if row.segment == segment]
    if geography:
        observations = [row for row in observations if row.geography == geography]
    if start_date:
        observations = [row for row in observations if row.period_end >= start_date]
    if end_date:
        observations = [row for row in observations if row.period_end <= end_date]
    if comparable_only:
        observations = [row for row in observations if not row.is_non_comparable and not row.definition_changed]
    observations.sort(key=lambda row: (row.period_end, row.segment, row.geography))
    gaps = []
    if not definitions:
        gaps.append({"key": "operating_kpis", "label": "Operating KPIs unavailable", "reason": f"No reviewed operating KPI dictionary is available for {company.name}.", "source": "operating-kpi-tracker", "next_action": "Review filings, earnings materials, and official supplemental tables for company-specific KPIs."})
    if selected and not observations:
        gaps.append({"key": f"operating_kpi_{selected.slug}_series", "label": f"{selected.name} series unavailable", "reason": "No observations match the selected segment, geography, and comparability controls.", "source": "operating-kpi-tracker", "next_action": "Broaden the filters or collect and review the missing period data."})
    persist_operating_kpi_gaps(company, gaps, bool(definitions), bool(observations))
    events = list(BusinessEvent.objects.filter(company=company).exclude(actual_change="").order_by("event_date")[:100])
    sources, seen_sources = [], set()
    for definition in ([selected] if selected else []):
        for observation in definition.observations.all():
            if observation.source_document_id and observation.source_document_id not in seen_sources:
                sources.append(serialize_profile_source(observation.source_document))
                seen_sources.add(observation.source_document_id)
    return JsonResponse({
        "status": "available" if definitions and observations else "partial" if definitions else "unavailable",
        "company": serialize_company_detail(company), "dictionary": [serialize_kpi_definition(row) for row in definitions],
        "selected_metric": serialize_kpi_definition(selected), "series": [serialize_kpi_observation(row) for row in observations],
        "missing_periods": missing_kpi_periods(selected, observations),
        "filters": {"segments": sorted({row.segment for definition in definitions for row in definition.observations.all() if row.segment}), "geographies": sorted({row.geography for definition in definitions for row in definition.observations.all() if row.geography}), "selected_segment": segment, "selected_geography": geography, "selected_start": start_date.isoformat() if start_date else "", "selected_end": end_date.isoformat() if end_date else "", "comparable_only": comparable_only},
        "alerts": kpi_alerts(selected, observations), "event_overlays": [serialize_business_event(row) for row in events],
        "peer_comparisons": peer_kpi_rows(company, selected), "export_rows": [serialize_kpi_export_row(row) for row in observations],
        "related_surfaces": [
            {"key": "events", "label": "Strategic events", "status": "available"},
            {"key": "earnings", "label": "Earnings intelligence", "status": "unavailable", "requirement": 5},
            {"key": "promises", "label": "Management promises", "status": "unavailable", "requirement": 4},
            {"key": "milestones", "label": "Strategy milestones", "status": "unavailable", "requirement": 6},
        ],
        "coverage": {"metric_count": len(definitions), "observation_count": len(observations), "reported_count": sum(1 for row in definitions if row.value_type == "REPORTED"), "calculated_count": sum(1 for row in definitions if row.value_type == "CALCULATED"), "last_period": observations[-1].period_end.isoformat() if observations else None},
        "evidence": sources, "source_gaps": gaps,
    })


@require_GET
def company_management_promises(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    as_of = parse_iso_date(request.GET.get("as_of"))
    status_filter = (request.GET.get("status") or "").strip().upper()
    type_filter = (request.GET.get("type") or "").strip().upper()
    due_filter = (request.GET.get("due") or "").strip().lower()
    selected_slug = (request.GET.get("promise") or "").strip()
    today = date.today()
    due_soon = today + timedelta(days=90)

    queryset = (
        ManagementPromise.objects.filter(company=company, is_published=True, review_status="REVIEWED")
        .select_related("source_document", "linked_kpi", "linked_strategic_turn")
        .prefetch_related("updates__source_document")
    )
    if as_of:
        queryset = queryset.filter(statement_date__lte=as_of)
    if status_filter:
        queryset = queryset.filter(current_status=status_filter)
    if type_filter:
        queryset = queryset.filter(promise_type=type_filter)
    if due_filter == "overdue":
        queryset = queryset.filter(target_end_date__lt=today).exclude(
            current_status__in=["ACHIEVED", "PARTIALLY_ACHIEVED", "MISSED", "WITHDRAWN"]
        )
    elif due_filter == "due_soon":
        queryset = queryset.filter(target_end_date__gte=today, target_end_date__lte=due_soon).exclude(
            current_status__in=["ACHIEVED", "PARTIALLY_ACHIEVED", "MISSED", "WITHDRAWN"]
        )
    promises = list(queryset.order_by("target_end_date", "-statement_date", "title"))
    selected = next((row for row in promises if row.slug == selected_slug), promises[0] if promises else None)

    gaps = []
    if not promises:
        gaps.append({
            "key": "management_promises",
            "label": "Reviewed management promises unavailable",
            "reason": f"No reviewed management commitments match the selected filters for {company.name}.",
            "source": "management-promise-tracker",
            "next_action": "Review earnings calls, guidance, filings, presentations, and KPI targets for measurable commitments.",
        })
    persist_management_promise_gaps(company, gaps)
    source_rows = []
    seen_sources = set()
    for promise in promises:
        for source in [promise.source_document, *[update.source_document for update in promise.updates.all()]]:
            if source and source.id not in seen_sources:
                source_rows.append(serialize_profile_source(source))
                seen_sources.add(source.id)

    return JsonResponse({
        "status": "available" if promises else "unavailable",
        "company": serialize_company_detail(company),
        "promises": [serialize_management_promise(row, include_updates=False) for row in promises],
        "selected_promise": serialize_management_promise(selected, include_updates=True),
        "filters": {
            "statuses": sorted({row.current_status for row in promises}),
            "types": sorted({row.promise_type for row in promises}),
            "selected_status": status_filter,
            "selected_type": type_filter,
            "selected_due": due_filter,
            "selected_as_of": as_of.isoformat() if as_of else "",
        },
        "coverage": {
            "promise_count": len(promises),
            "due_soon_count": sum(1 for row in promises if row.target_end_date and today <= row.target_end_date <= due_soon),
            "overdue_count": sum(
                1 for row in promises
                if row.target_end_date and row.target_end_date < today
                and row.current_status not in {"ACHIEVED", "PARTIALLY_ACHIEVED", "MISSED", "WITHDRAWN"}
            ),
            "source_count": len(source_rows),
            "last_updated": max((row.updated_at for row in promises), default=company.updated_at).isoformat(),
        },
        "evidence": source_rows,
        "source_gaps": gaps,
    })


@require_GET
def company_strategy_milestones(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    status_filter = (request.GET.get("status") or "").strip().upper()
    type_filter = (request.GET.get("type") or "").strip().upper()
    origin_filter = (request.GET.get("origin") or "").strip().upper()
    view = (request.GET.get("view") or "all").strip().lower()
    selected_slug = (request.GET.get("milestone") or "").strip()
    today = date.today()
    upcoming_end = today + timedelta(days=180)
    recent_start = today - timedelta(days=180)
    terminal = [MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED, MilestoneStatus.FAILED]

    queryset = (
        StrategyMilestone.objects.filter(company=company, is_published=True, review_status="REVIEWED")
        .select_related("source_document", "linked_promise", "linked_kpi", "linked_strategic_turn")
        .prefetch_related("status_updates__source_document", "dependencies__depends_on")
    )
    if status_filter:
        queryset = queryset.filter(current_status=status_filter)
    if type_filter:
        queryset = queryset.filter(milestone_type=type_filter)
    if origin_filter:
        queryset = queryset.filter(origin=origin_filter)
    if view == "upcoming":
        queryset = queryset.filter(expected_end_date__gte=today, expected_end_date__lte=upcoming_end).exclude(current_status__in=terminal)
    elif view == "overdue":
        queryset = queryset.filter(expected_end_date__lt=today).exclude(current_status__in=terminal)
    elif view == "completed":
        queryset = queryset.filter(current_status=MilestoneStatus.COMPLETED, status_updates__status_date__gte=recent_start).distinct()
    milestones = list(queryset.order_by("expected_end_date", "title"))
    selected = next((row for row in milestones if row.slug == selected_slug), milestones[0] if milestones else None)

    gaps = []
    if not milestones:
        gaps.append({
            "key": "strategy_milestones",
            "label": "Reviewed strategy milestones unavailable",
            "reason": f"No reviewed milestones match the selected filters for {company.name}.",
            "source": "strategy-milestone-tracker",
            "next_action": "Review management commitments, regulatory deadlines, contracts, and execution evidence.",
        })
    persist_strategy_milestone_gaps(company, gaps)
    sources = []
    seen_sources = set()
    for milestone in milestones:
        for source in [milestone.source_document, *[update.source_document for update in milestone.status_updates.all()]]:
            if source.id not in seen_sources:
                sources.append(serialize_profile_source(source))
                seen_sources.add(source.id)
    all_reviewed = list(
        StrategyMilestone.objects.filter(company=company, is_published=True, review_status="REVIEWED")
        .prefetch_related("status_updates")
    )
    return JsonResponse({
        "status": "available" if milestones else "unavailable",
        "company": serialize_company_detail(company),
        "milestones": [serialize_strategy_milestone(row, include_history=False) for row in milestones],
        "selected_milestone": serialize_strategy_milestone(selected, include_history=True),
        "filters": {
            "statuses": sorted({row.current_status for row in all_reviewed}),
            "types": sorted({row.milestone_type for row in all_reviewed}),
            "origins": sorted({row.origin for row in all_reviewed}),
            "selected_status": status_filter,
            "selected_type": type_filter,
            "selected_origin": origin_filter,
            "selected_view": view,
        },
        "coverage": {
            "milestone_count": len(all_reviewed),
            "upcoming_count": sum(1 for row in all_reviewed if row.expected_end_date and today <= row.expected_end_date <= upcoming_end and row.current_status not in terminal),
            "overdue_count": sum(1 for row in all_reviewed if row.expected_end_date and row.expected_end_date < today and row.current_status not in terminal),
            "completed_count": sum(1 for row in all_reviewed if row.current_status == MilestoneStatus.COMPLETED),
            "unknown_date_count": sum(1 for row in all_reviewed if row.expected_end_date is None),
            "source_count": len(sources),
        },
        "evidence": sources,
        "source_gaps": gaps,
    })


@require_GET
def company_earnings(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    periods = list(
        EarningsPeriod.objects.filter(company=company, is_published=True, review_status="REVIEWED")
        .select_related("source_document")
        .order_by("-period_end", "-filed_date")
    )
    selected_key = (request.GET.get("period") or "").strip()
    selected = next(
        (row for row in periods if row.accession_number == selected_key or earnings_period_key(row) == selected_key),
        periods[0] if periods else None,
    )
    previous = next((row for row in periods if selected and row.period_end < selected.period_end), None)
    if selected is None:
        return JsonResponse({
            "status": "unavailable",
            "company": serialize_company_detail(company),
            "periods": [],
            "selected_period": None,
            "source_gaps": [{
                "key": "earnings_periods",
                "label": "Earnings Intelligence unavailable",
                "reason": f"No reviewed quarterly earnings periods are available for {company.name}.",
                "source": "sec-companyfacts",
                "next_action": "Ingest SEC 10-Q filings and Company Facts, then build earnings periods.",
            }],
        })

    metrics = earnings_metric_rows(company, selected, previous)
    kpis = earnings_kpi_rows(company, selected, previous)
    period_start = selected.period_start or (previous.period_end if previous else selected.period_end)
    events = list(
        BusinessEvent.objects.filter(company=company, event_date__gt=period_start, event_date__lte=selected.period_end)
        .exclude(actual_change="")
        .select_related("source_document")
        .order_by("-event_date")[:12]
    )
    turns = list(
        StrategicTurn.objects.filter(company=company, start_date__gt=period_start, start_date__lte=selected.period_end)
        .order_by("-start_date")[:12]
    )
    promises = list(
        ManagementPromise.objects.filter(
            company=company,
            is_published=True,
            review_status="REVIEWED",
        )
        .filter(
            Q(statement_date__gt=period_start, statement_date__lte=selected.filed_date)
            | Q(target_end_date__gt=period_start, target_end_date__lte=selected.period_end)
        )
        .select_related("source_document")[:12]
    )
    risk_events = [row for row in events if row.event_type in RISK_EVENT_TYPES]
    guidance = [row for row in promises if row.promise_type == "GUIDANCE"]
    guidance_comparisons = list(
        selected.guidance_comparisons.filter(review_status="REVIEWED")
        .select_related("forecast_source", "actual_source")
    )
    reviewed_documents = list(
        selected.documents.filter(review_status="REVIEWED").select_related("source_document")
    )
    reviewed_explanations = [row.evidence_text for row in reviewed_documents if row.evidence_text]
    management_explanation = selected.management_explanation or " ".join(reviewed_explanations)
    unanswered_questions = list(selected.unanswered_questions or [])
    if not management_explanation:
        unanswered_questions.append("Which operating and market factors did management identify as the main drivers of this period?")
    if not guidance and not guidance_comparisons:
        unanswered_questions.append("Did management introduce, maintain, raise, reduce, or withdraw comparable guidance?")
    gaps = earnings_source_gaps(bool(management_explanation), bool(guidance or guidance_comparisons))
    return JsonResponse({
        "status": "available",
        "company": serialize_company_detail(company),
        "periods": [serialize_earnings_period(row) for row in periods],
        "selected_period": {
            **serialize_earnings_period(selected),
            "previous_period": serialize_earnings_period(previous) if previous else None,
            "measured_results": metrics,
            "operating_kpis": kpis,
            "management_explanation": management_explanation or None,
            "infodj_interpretation": selected.infodj_interpretation or None,
            "unanswered_questions": unanswered_questions,
            "disclosure_changes": earnings_disclosure_changes(company, selected, previous),
            "guidance_comparison": {
                "status": "available" if guidance_comparisons else "unavailable",
                "items": [serialize_guidance_comparison(row) for row in guidance_comparisons],
                "linked_promises": [serialize_management_promise(row, include_updates=True) for row in guidance],
                "reason": "No reviewed comparable numeric guidance was linked to this reporting period." if not guidance_comparisons else "",
            },
            "promises": [serialize_management_promise(row, include_updates=False) for row in promises],
            "strategic_turns": [
                serialize_strategic_turn(row, source_count=row.turn_sources.count()) for row in turns
            ],
            "risk_signals": [serialize_risk_signal(row) for row in risk_events],
            "document_set": [
                {"document_type": "SEC_10_Q", "source": serialize_profile_source(selected.source_document)},
                *[
                    {
                        "document_type": row.document_type,
                        "source": serialize_profile_source(row.source_document),
                    }
                    for row in reviewed_documents
                ],
            ],
            "export_rows": metrics,
        },
        "source_gaps": gaps,
    })


@require_GET
def company_capital_allocation(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    periods = list(
        CapitalAllocationPeriod.objects.filter(company=company, is_published=True, review_status="REVIEWED")
        .prefetch_related("items__source_document", "items__source_fact")
        .order_by("-period_end", "-filed_date")
    )
    selected_key = (request.GET.get("period") or "").strip()
    selected = next((row for row in periods if capital_allocation_period_key(row) == selected_key), periods[0] if periods else None)
    if selected is None:
        gaps = [{
            "key": "capital_allocation_periods",
            "label": "Capital Allocation unavailable",
            "reason": f"No reviewed SEC-backed capital allocation periods are available for {company.name}.",
            "source": "sec-companyfacts",
            "next_action": "Ingest SEC Company Facts for operating cash flow, capex, R&D, buybacks, dividends, debt, acquisitions, and cash context.",
        }]
        persist_capital_allocation_gaps(company, gaps)
        return JsonResponse({
            "status": "unavailable",
            "company": serialize_company_detail(company),
            "periods": [],
            "selected_period": None,
            "source_gaps": gaps,
        })

    items = list(selected.items.filter(review_status="REVIEWED").order_by("is_context", "category", "label"))
    deployment_items = [row for row in items if row.category in DEPLOYMENT_CATEGORIES and not row.is_context]
    context_items = [row for row in items if row.is_context or row.category not in DEPLOYMENT_CATEGORIES]
    missing_categories = [
        category
        for category, _label in CapitalAllocationCategory.choices
        if category not in {row.category for row in items}
        and category not in {CapitalAllocationCategory.FREE_CASH_FLOW, CapitalAllocationCategory.INTERNAL_PROGRAM}
    ]
    gaps = capital_allocation_source_gaps(company, missing_categories, selected, deployment_items)
    persist_capital_allocation_gaps(company, gaps)
    category_totals = capital_allocation_category_totals(deployment_items, selected)
    related_turns = list(
        StrategicTurn.objects.filter(company=company, start_date__lte=selected.period_end)
        .order_by("-start_date", "-created_at")[:6]
    )
    related_promises = list(
        ManagementPromise.objects.filter(company=company, is_published=True, review_status="REVIEWED", statement_date__lte=selected.period_end)
        .select_related("source_document")
        .order_by("-statement_date")[:6]
    )
    return JsonResponse({
        "status": "available" if deployment_items else "partial",
        "company": serialize_company_detail(company),
        "periods": [serialize_capital_allocation_period(row, include_items=False) for row in periods],
        "selected_period": {
            **serialize_capital_allocation_period(selected, include_items=False),
            "deployment_items": [serialize_capital_allocation_item(row, selected) for row in deployment_items],
            "context_items": [serialize_capital_allocation_item(row, selected) for row in context_items],
            "category_totals": category_totals,
            "allocation_mix": [
                {
                    "category": row["category"],
                    "category_label": row["category_label"],
                    "value": row["value"],
                    "share_of_total_deployment": row["share_of_total_deployment"],
                }
                for row in category_totals
            ],
            "cash_flow_context": {
                "operating_cash_flow": decimal_to_float_or_none(selected.operating_cash_flow),
                "cash_balance": decimal_to_float_or_none(selected.cash_balance),
                "free_cash_flow": decimal_to_float_or_none(selected.free_cash_flow),
                "total_deployment": decimal_to_float_or_none(selected.total_deployment),
                "deployment_to_operating_cash_flow_pct": pct_ratio(selected.total_deployment, selected.operating_cash_flow),
                "deployment_to_cash_balance_pct": pct_ratio(selected.total_deployment, selected.cash_balance),
            },
            "related_strategy": {
                "strategic_turns": [serialize_strategic_turn(row, source_count=row.turn_sources.count()) for row in related_turns],
                "management_promises": [serialize_management_promise(row, include_updates=False) for row in related_promises],
            },
        },
        "filters": {
            "selected_period": capital_allocation_period_key(selected),
            "categories": [category for category, _label in CapitalAllocationCategory.choices],
        },
        "coverage": {
            "period_count": len(periods),
            "deployment_item_count": len(deployment_items),
            "context_item_count": len(context_items),
            "missing_category_count": len(missing_categories),
            "last_updated": selected.updated_at.isoformat(),
        },
        "evidence": capital_allocation_evidence(items),
        "source_gaps": gaps,
    })


@require_GET
def company_competitive_position(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    snapshots = list(
        CompetitivePositionSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .select_related("source_document")
        .prefetch_related("peers__peer_company", "peers__dimensions__source_document", "dimensions__source_document")
        .order_by("-effective_date", "-updated_at")
    )
    as_of = parse_iso_date(request.GET.get("as_of"))
    eligible = [row for row in snapshots if as_of is None or row.effective_date <= as_of]
    current = eligible[0] if eligible else None
    if current is None:
        gaps = [{
            "key": "competitive_position_snapshot",
            "label": "Competitive Position unavailable",
            "reason": f"No reviewed competitive-position snapshot is available for {company.name}.",
            "source": "company-profile",
            "next_action": "Refresh reviewed Company 360 profiles and run build_competitive_positions.",
        }]
        persist_competitive_position_gaps(company, gaps)
        return JsonResponse({
            "status": "unavailable",
            "company": serialize_company_detail(company),
            "snapshot": None,
            "snapshot_history": [],
            "source_gaps": gaps,
        })

    peers = list(current.peers.all())
    relationship_filter = (request.GET.get("relationship") or "").strip().upper()
    if relationship_filter:
        peers = [row for row in peers if row.relationship_type == relationship_filter]
    dimension_groups = competitive_dimension_groups(current, peers)
    action_events = list(
        BusinessEvent.objects.filter(company=company, event_type__in=["COMPETITIVE_RESPONSE", "PRICING_CHANGE", "PRODUCT_EXPANSION"])
        .exclude(actual_change="")
        .select_related("source_document")
        .order_by("-event_date", "-created_at")[:12]
    )
    gaps = competitive_position_source_gaps(company, current, peers, dimension_groups)
    persist_competitive_position_gaps(company, gaps)
    evidence = competitive_position_evidence(current, peers)
    return JsonResponse({
        "status": "available" if peers else "partial",
        "company": serialize_company_detail(company),
        "snapshot": serialize_competitive_position_snapshot(current),
        "snapshot_history": [serialize_competitive_position_history(row, current) for row in snapshots],
        "peer_map": [serialize_competitive_peer(row) for row in peers],
        "comparison": dimension_groups,
        "competitive_actions": [serialize_business_event(row) for row in action_events],
        "market_share": {
            "status": "unavailable",
            "series": [],
            "reason": "No reviewed market-share series with source and methodology labels is available yet.",
        },
        "moat_evidence": dimension_groups.get(CompetitiveDimensionType.MOAT_EVIDENCE, []),
        "opposing_evidence": dimension_groups.get(CompetitiveDimensionType.OPPOSING_EVIDENCE, []),
        "filters": {
            "relationships": sorted({row.relationship_type for row in current.peers.all()}),
            "selected_relationship": relationship_filter,
            "as_of": as_of.isoformat() if as_of else "",
        },
        "coverage": {
            "peer_count": len(peers),
            "in_universe_peer_count": sum(1 for row in peers if row.is_in_universe),
            "dimension_count": sum(len(rows) for rows in dimension_groups.values()),
            "competitive_action_count": len(action_events),
            "source_count": len(evidence),
            "last_updated": current.updated_at.isoformat(),
        },
        "evidence": evidence,
        "source_gaps": gaps,
    })


@require_GET
def company_product_pricing(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    snapshots = list(
        ProductCatalogSnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .select_related("source_document")
        .prefetch_related("offerings__price_observations__source_document", "changes__source_document", "changes__linked_event")
        .order_by("-effective_date", "-updated_at")
    )
    as_of = parse_iso_date(request.GET.get("as_of"))
    eligible = [row for row in snapshots if as_of is None or row.effective_date <= as_of]
    current = eligible[0] if eligible else None
    if current is None:
        gaps = [{
            "key": "product_catalog_snapshot",
            "label": "Product and Pricing History unavailable",
            "reason": f"No reviewed product catalog snapshot is available for {company.name}.",
            "source": "company-profile",
            "next_action": "Refresh reviewed Company 360 profiles and run build_product_pricing_history.",
        }]
        persist_product_pricing_gaps(company, gaps)
        return JsonResponse({"status": "unavailable", "company": serialize_company_detail(company), "snapshot": None, "snapshot_history": [], "source_gaps": gaps})
    offering_type = (request.GET.get("type") or "").strip().upper()
    offerings = list(current.offerings.all())
    if offering_type:
        offerings = [row for row in offerings if row.offering_type == offering_type]
    changes = list(current.changes.all())
    prices = [price for offering in offerings for price in offering.price_observations.all()]
    gaps = product_pricing_source_gaps(company, current, offerings, changes, prices)
    persist_product_pricing_gaps(company, gaps)
    evidence = product_pricing_evidence(current, offerings, changes, prices)
    return JsonResponse({
        "status": "available" if offerings else "partial",
        "company": serialize_company_detail(company),
        "snapshot": serialize_product_catalog_snapshot(current),
        "snapshot_history": [serialize_product_catalog_history(row, current) for row in snapshots],
        "offerings": [serialize_product_offering(row) for row in offerings],
        "changes": [serialize_product_change(row) for row in changes],
        "price_observations": [serialize_price_observation(row) for row in prices],
        "price_context": {
            "status": "available" if prices else "unavailable",
            "reason": "" if prices else "No reviewed list-price observations with currency, geography, billing period, tax, promotion, and customer-segment context are available yet.",
            "promotion_policy": "Promotional prices are stored separately and are not treated as standard list prices.",
        },
        "comparison": product_before_after_rows(changes),
        "filters": {
            "types": sorted({row.offering_type for row in current.offerings.all()}),
            "selected_type": offering_type,
            "as_of": as_of.isoformat() if as_of else "",
        },
        "coverage": {
            "offering_count": len(offerings),
            "change_count": len(changes),
            "price_observation_count": len(prices),
            "source_count": len(evidence),
            "last_updated": current.updated_at.isoformat(),
        },
        "evidence": evidence,
        "source_gaps": gaps,
    })


@require_GET
def company_acquisition_lifecycle(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    deals_qs = (
        AcquisitionLifecycleDeal.objects.filter(company=company, is_published=True, review_status="REVIEWED")
        .select_related("source_document", "target_company", "linked_event", "linked_strategic_turn")
        .prefetch_related("stage_events__source_document", "stage_events__linked_milestone", "stage_events__linked_product_change")
        .order_by("-announcement_date", "target_name")
    )
    stage_filter = (request.GET.get("stage") or "").strip().upper()
    transaction_filter = (request.GET.get("transaction_type") or "").strip().upper()
    outcome_filter = (request.GET.get("outcome") or "").strip().upper()
    if stage_filter:
        deals_qs = deals_qs.filter(current_stage=stage_filter)
    if transaction_filter:
        deals_qs = deals_qs.filter(transaction_type=transaction_filter)
    if outcome_filter:
        deals_qs = deals_qs.filter(outcome_category=outcome_filter)
    deals = list(deals_qs)
    selected_slug = (request.GET.get("deal") or "").strip()
    selected = next((row for row in deals if row.slug == selected_slug), deals[0] if deals else None)
    if selected is None:
        gaps = acquisition_lifecycle_source_gaps(company, [], None)
        persist_acquisition_lifecycle_gaps(company, gaps)
        return JsonResponse({
            "status": "partial",
            "company": serialize_company_detail(company),
            "deals": [],
            "selected_deal": None,
            "filters": acquisition_lifecycle_filters(company, stage_filter, transaction_filter, outcome_filter, selected_slug),
            "coverage": {"deal_count": 0, "stage_event_count": 0, "source_count": 0, "last_updated": None},
            "evidence": [],
            "source_gaps": gaps,
        })
    stage_events = list(selected.stage_events.all())
    gaps = acquisition_lifecycle_source_gaps(company, deals, selected)
    persist_acquisition_lifecycle_gaps(company, gaps)
    evidence = acquisition_lifecycle_evidence(deals, stage_events)
    return JsonResponse({
        "status": "available" if deals else "partial",
        "company": serialize_company_detail(company),
        "deals": [serialize_acquisition_deal(row, include_events=False) for row in deals],
        "selected_deal": serialize_acquisition_deal(selected, include_events=True),
        "portfolio": acquisition_portfolio_summary(deals),
        "filters": acquisition_lifecycle_filters(company, stage_filter, transaction_filter, outcome_filter, selected.slug),
        "coverage": {
            "deal_count": len(deals),
            "stage_event_count": sum(row.stage_events.count() for row in deals),
            "deal_term_count": sum(1 for row in deals if row.purchase_price is not None or row.payment_form),
            "source_count": len(evidence),
            "last_updated": max(row.updated_at for row in deals).isoformat(),
        },
        "evidence": evidence,
        "source_gaps": gaps,
    })


@require_GET
def company_customer_supplier_dependency(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    snapshots = list(
        CustomerSupplierDependencySnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
        .select_related("source_document")
        .prefetch_related("dependencies__source_document", "dependencies__counterparty_company", "dependencies__contract_terms__source_document")
        .order_by("-effective_date", "-updated_at")
    )
    as_of = parse_iso_date(request.GET.get("as_of"))
    eligible = [row for row in snapshots if as_of is None or row.effective_date <= as_of]
    current = eligible[0] if eligible else None
    dependency_type = (request.GET.get("type") or "").strip().upper()
    confidence = (request.GET.get("confidence") or "").strip().upper()
    if current is None:
        gaps = [{
            "key": "dependency_snapshot",
            "label": "Dependency map unavailable",
            "reason": f"No reviewed customer and supplier dependency snapshot is available for {company.name}.",
            "source": "customer-supplier-dependency",
            "next_action": "Refresh reviewed Company 360 profiles, business-model maps, and run build_customer_supplier_dependencies.",
        }]
        persist_customer_supplier_dependency_gaps(company, gaps)
        return JsonResponse({"status": "unavailable", "company": serialize_company_detail(company), "snapshot": None, "snapshot_history": [], "dependencies": [], "source_gaps": gaps})
    dependencies = list(current.dependencies.all())
    if dependency_type:
        dependencies = [row for row in dependencies if row.dependency_type == dependency_type]
    if confidence:
        dependencies = [row for row in dependencies if row.disclosure_confidence == confidence]
    gaps = customer_supplier_dependency_source_gaps(company, current, dependencies)
    persist_customer_supplier_dependency_gaps(company, gaps)
    evidence = customer_supplier_dependency_evidence(current, dependencies)
    return JsonResponse({
        "status": "available" if dependencies else "partial",
        "company": serialize_company_detail(company),
        "snapshot": serialize_dependency_snapshot(current),
        "snapshot_history": [serialize_dependency_snapshot_history(row, current) for row in snapshots],
        "dependencies": [serialize_dependency(row) for row in dependencies],
        "map": dependency_map(dependencies),
        "contract_terms": [serialize_dependency_contract_term(term) for row in dependencies for term in row.contract_terms.all()],
        "filters": {
            "types": sorted({row.dependency_type for row in current.dependencies.all()}),
            "confidence_levels": sorted({row.disclosure_confidence for row in current.dependencies.all()}),
            "selected_type": dependency_type,
            "selected_confidence": confidence,
            "as_of": as_of.isoformat() if as_of else "",
        },
        "coverage": {
            "dependency_count": len(dependencies),
            "named_counterparty_count": sum(1 for row in dependencies if row.is_named_counterparty),
            "category_only_count": sum(1 for row in dependencies if row.disclosure_confidence == DependencyDisclosureConfidence.CATEGORY_ONLY),
            "contract_term_count": sum(row.contract_terms.count() for row in dependencies),
            "source_count": len(evidence),
            "last_updated": current.updated_at.isoformat(),
        },
        "evidence": evidence,
        "source_gaps": gaps,
    })


def earnings_period_key(period: EarningsPeriod) -> str:
    return f"FY{period.fiscal_year}-{period.fiscal_period}"


def serialize_earnings_period(period: EarningsPeriod | None) -> dict[str, object] | None:
    if period is None:
        return None
    return {
        "id": period.id,
        "key": earnings_period_key(period),
        "accession_number": period.accession_number,
        "fiscal_year": period.fiscal_year,
        "fiscal_period": period.fiscal_period,
        "period_start": period.period_start.isoformat() if period.period_start else None,
        "period_end": period.period_end.isoformat(),
        "filed_date": period.filed_date.isoformat(),
        "headline": period.headline,
        "confidence_score": decimal_to_float(period.confidence_score),
        "source": serialize_profile_source(period.source_document),
    }


def earnings_metric_rows(company: Company, period: EarningsPeriod, previous: EarningsPeriod | None) -> list[dict[str, object]]:
    from apps.ingestion.services.earnings_intelligence import KEY_CONCEPTS

    filing_facts = list(FinancialFact.objects.filter(company=company, accession_number=period.accession_number))
    rows = []
    seen_labels = set()
    for concept in KEY_CONCEPTS:
        candidates = [
            fact for fact in filing_facts
            if fact.concept == concept and str((fact.raw or {}).get("end") or "") == period.period_end.isoformat()
        ]
        if not candidates:
            continue
        current = max(candidates, key=lambda fact: (bool(fact.frame), fact.id))
        label = current.label or current.concept
        normalized_label = label.lower()
        if normalized_label in seen_labels:
            continue
        seen_labels.add(normalized_label)
        prior = None
        if previous:
            prior_candidates = [
                fact for fact in FinancialFact.objects.filter(
                    company=company,
                    accession_number=previous.accession_number,
                    concept=current.concept,
                    unit=current.unit,
                )
                if str((fact.raw or {}).get("end") or "") == previous.period_end.isoformat()
            ]
            prior = max(prior_candidates, key=lambda fact: (bool(fact.frame), fact.id), default=None)
        prior_value = decimal_to_float(prior.value) if prior else None
        current_value = decimal_to_float(current.value)
        change_pct = pct_change(prior.value, current.value) if prior and prior.value else None
        rows.append({
            "concept": current.concept,
            "label": label,
            "unit": current.unit,
            "value": current_value,
            "previous_value": prior_value,
            "change_pct": change_pct,
            "comparison_status": "available" if prior else "unavailable",
            "source": "SEC Company Facts",
        })
    return rows[:8]


def earnings_kpi_rows(company: Company, period: EarningsPeriod, previous: EarningsPeriod | None) -> list[dict[str, object]]:
    rows = []
    definitions = KpiDefinition.objects.filter(company=company, is_active=True).prefetch_related("observations")
    for definition in definitions:
        observations = [row for row in definition.observations.all() if row.period_end <= period.period_end]
        if not observations:
            continue
        current = max(observations, key=lambda row: row.period_end)
        if current.period_end < period.period_end.replace(day=1):
            continue
        prior = None
        if previous:
            prior = max((row for row in observations if row.period_end <= previous.period_end), key=lambda row: row.period_end, default=None)
        rows.append({
            "slug": definition.slug,
            "name": definition.name,
            "unit": definition.unit,
            "period_end": current.period_end.isoformat(),
            "value": decimal_to_float(current.value),
            "previous_value": decimal_to_float(prior.value) if prior else None,
            "change_pct": pct_change(prior.value, current.value) if prior and prior.value else None,
            "quality_flags": [
                flag for flag, enabled in (
                    ("estimated", current.is_estimated),
                    ("restated", current.is_restatement),
                    ("non-comparable", current.is_non_comparable),
                    ("definition changed", current.definition_changed),
                ) if enabled
            ],
        })
    return rows[:8]


def earnings_disclosure_changes(
    company: Company, period: EarningsPeriod, previous: EarningsPeriod | None
) -> dict[str, list[dict[str, str]]]:
    current = {
        (row.concept, row.unit): row.label or row.concept
        for row in FinancialFact.objects.filter(company=company, accession_number=period.accession_number)
    }
    prior = {
        (row.concept, row.unit): row.label or row.concept
        for row in FinancialFact.objects.filter(company=company, accession_number=previous.accession_number)
    } if previous else {}
    added = [
        {"concept": concept, "unit": unit, "label": current[(concept, unit)]}
        for concept, unit in sorted(current.keys() - prior.keys())
    ]
    removed = [
        {"concept": concept, "unit": unit, "label": prior[(concept, unit)]}
        for concept, unit in sorted(prior.keys() - current.keys())
    ]
    return {"added": added[:20], "removed": removed[:20]}


def earnings_source_gaps(has_management_explanation: bool, has_guidance: bool) -> list[dict[str, str]]:
    gaps = []
    if not has_management_explanation:
        gaps.append({
            "key": "management_explanation",
            "label": "Management explanation unavailable",
            "reason": "No reviewed earnings release, shareholder letter, presentation, or call excerpt is linked to this period.",
            "source": "earnings-documents",
            "next_action": "Collect and review company-issued earnings materials while preserving each document identity.",
        })
    if not has_guidance:
        gaps.append({
            "key": "guidance_comparison",
            "label": "Actual-versus-guidance unavailable",
            "reason": "No reviewed numeric guidance is linked to this reporting period.",
            "source": "management-promises",
            "next_action": "Review guidance statements and map comparable metrics, scope, units, and target periods.",
        })
    return gaps


def capital_allocation_period_key(period: CapitalAllocationPeriod) -> str:
    return f"FY{period.fiscal_year}-{period.fiscal_period}-{period.period_end.isoformat()}"


def serialize_capital_allocation_period(period: CapitalAllocationPeriod, *, include_items: bool) -> dict[str, object]:
    payload = {
        "id": period.id,
        "key": capital_allocation_period_key(period),
        "fiscal_year": period.fiscal_year,
        "fiscal_period": period.fiscal_period,
        "period_start": period.period_start.isoformat() if period.period_start else None,
        "period_end": period.period_end.isoformat(),
        "filed_date": period.filed_date.isoformat() if period.filed_date else None,
        "accession_number": period.accession_number,
        "cadence": period.cadence,
        "headline": period.headline,
        "total_deployment": decimal_to_float_or_none(period.total_deployment),
        "operating_cash_flow": decimal_to_float_or_none(period.operating_cash_flow),
        "cash_balance": decimal_to_float_or_none(period.cash_balance),
        "free_cash_flow": decimal_to_float_or_none(period.free_cash_flow),
        "calculation_note": period.calculation_note,
        "review_status": period.review_status,
    }
    if include_items:
        payload["items"] = [serialize_capital_allocation_item(row, period) for row in period.items.all()]
    return payload


def serialize_capital_allocation_item(item: CapitalAllocationItem, period: CapitalAllocationPeriod) -> dict[str, object]:
    return {
        "id": item.id,
        "category": item.category,
        "category_label": dict(CapitalAllocationCategory.choices).get(item.category, item.category),
        "label": item.label,
        "value": decimal_to_float_or_none(item.value),
        "unit": item.unit,
        "concept": item.concept,
        "evidence_text": item.evidence_text,
        "is_context": item.is_context,
        "is_calculated": item.is_calculated,
        "calculation_method": item.calculation_method,
        "confidence_score": decimal_to_float(item.confidence_score),
        "share_of_total_deployment": pct_ratio(item.value, period.total_deployment) if not item.is_context else None,
        "share_of_operating_cash_flow": pct_ratio(item.value, period.operating_cash_flow),
        "source": serialize_profile_source(item.source_document) if item.source_document_id else None,
        "source_fact": {
            "id": item.source_fact_id,
            "concept": item.source_fact.concept,
            "label": item.source_fact.label,
            "accession_number": item.source_fact.accession_number,
        } if item.source_fact_id else None,
    }


def capital_allocation_category_totals(items: list[CapitalAllocationItem], period: CapitalAllocationPeriod) -> list[dict[str, object]]:
    totals = defaultdict(lambda: {"value": 0.0, "item_count": 0})
    labels = dict(CapitalAllocationCategory.choices)
    for item in items:
        totals[item.category]["value"] += decimal_to_float(item.value) or 0
        totals[item.category]["item_count"] += 1
    return [
        {
            "category": category,
            "category_label": labels.get(category, category),
            "value": round(row["value"], 6),
            "item_count": row["item_count"],
            "share_of_total_deployment": pct_ratio(row["value"], period.total_deployment),
        }
        for category, row in sorted(totals.items(), key=lambda item: item[0])
    ]


def capital_allocation_evidence(items: list[CapitalAllocationItem]) -> list[dict[str, object]]:
    sources = []
    seen = set()
    for item in items:
        if item.source_document_id and item.source_document_id not in seen:
            sources.append(serialize_profile_source(item.source_document))
            seen.add(item.source_document_id)
    return sources


def capital_allocation_source_gaps(
    company: Company,
    missing_categories: list[str],
    period: CapitalAllocationPeriod,
    deployment_items: list[CapitalAllocationItem],
) -> list[dict[str, str]]:
    labels = dict(CapitalAllocationCategory.choices)
    gaps = []
    if not deployment_items:
        gaps.append({
            "key": "capital_deployment_items",
            "label": "Deployment items unavailable",
            "reason": f"{company.name} has operating cash-flow context for the selected period, but no reviewed deployment categories were present in stored SEC facts.",
            "source": "sec-companyfacts",
            "next_action": "Expand SEC concepts or review the filing cash-flow statement for capex, buybacks, dividends, acquisitions, debt, restructuring, content, or inventory investment.",
        })
    if period.operating_cash_flow is None:
        gaps.append({
            "key": "operating_cash_flow_context",
            "label": "Operating cash flow unavailable",
            "reason": "No reviewed operating cash-flow fact is available for this period.",
            "source": "sec-companyfacts",
            "next_action": "Collect NetCashProvidedByUsedInOperatingActivities for the selected period.",
        })
    for category in missing_categories:
        gaps.append({
            "key": f"capital_allocation_{category.lower()}",
            "label": f"{labels.get(category, category)} unavailable",
            "reason": f"No reviewed, source-backed {labels.get(category, category).lower()} figure is available for {company.name} in the selected period.",
            "source": "sec-companyfacts",
            "next_action": "Review official filings and company materials before treating this category as present or absent.",
        })
    return gaps


def pct_ratio(value, denominator) -> float | None:
    if value in {None, ""} or denominator in {None, "", 0}:
        return None
    try:
        return round((float(value) / abs(float(denominator))) * 100, 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def serialize_competitive_position_snapshot(snapshot: CompetitivePositionSnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "summary": snapshot.summary,
        "methodology": snapshot.methodology,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "source": serialize_profile_source(snapshot.source_document) if snapshot.source_document_id else None,
    }


def serialize_competitive_position_history(
    snapshot: CompetitivePositionSnapshot,
    current: CompetitivePositionSnapshot,
) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "peer_count": snapshot.peers.count(),
        "selected": snapshot.id == current.id,
    }


def serialize_competitive_peer(peer: CompetitivePeer) -> dict[str, object]:
    return {
        "id": peer.id,
        "peer_name": peer.peer_name,
        "peer_company": serialize_company(peer.peer_company) if peer.peer_company_id else None,
        "relationship_type": peer.relationship_type,
        "relationship_label": peer.get_relationship_type_display(),
        "scope": peer.scope,
        "geography": peer.geography,
        "product_overlap": peer.product_overlap if isinstance(peer.product_overlap, list) else [],
        "customer_overlap": peer.customer_overlap if isinstance(peer.customer_overlap, list) else [],
        "evidence_text": peer.evidence_text,
        "is_in_universe": peer.is_in_universe,
        "confidence_score": decimal_to_float(peer.confidence_score),
    }


def competitive_dimension_groups(
    snapshot: CompetitivePositionSnapshot,
    peers: list[CompetitivePeer],
) -> dict[str, list[dict[str, object]]]:
    peer_ids = {row.id for row in peers}
    rows = []
    for dimension in snapshot.dimensions.all():
        if dimension.peer_id and dimension.peer_id not in peer_ids:
            continue
        rows.append({
            "id": dimension.id,
            "dimension_type": dimension.dimension_type,
            "dimension_label": dimension.get_dimension_type_display(),
            "label": dimension.label,
            "description": dimension.description,
            "evidence_text": dimension.evidence_text,
            "peer_id": dimension.peer_id,
            "peer_name": dimension.peer.peer_name if dimension.peer_id else "",
            "confidence_score": decimal_to_float(dimension.confidence_score),
            "source": serialize_profile_source(dimension.source_document) if dimension.source_document_id else None,
        })
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["dimension_type"])].append(row)
    return dict(grouped)


def competitive_position_evidence(
    snapshot: CompetitivePositionSnapshot,
    peers: list[CompetitivePeer],
) -> list[dict[str, object]]:
    sources = []
    seen = set()
    if snapshot.source_document_id:
        sources.append(serialize_profile_source(snapshot.source_document))
        seen.add(snapshot.source_document_id)
    for peer in peers:
        for dimension in peer.dimensions.all():
            if dimension.source_document_id and dimension.source_document_id not in seen:
                sources.append(serialize_profile_source(dimension.source_document))
                seen.add(dimension.source_document_id)
    return sources


def competitive_position_source_gaps(
    company: Company,
    snapshot: CompetitivePositionSnapshot,
    peers: list[CompetitivePeer],
    dimension_groups: dict[str, list[dict[str, object]]],
) -> list[dict[str, str]]:
    gaps = []
    if not peers:
        gaps.append({
            "key": "competitive_peers",
            "label": "Competitive peers unavailable",
            "reason": f"No reviewed competitor or benchmark peer records are available for {company.name}.",
            "source": "competitive-position",
            "next_action": "Review Company 360 competitor disclosures and same-sector peer mappings.",
        })
    for dimension_type, label in (
        (CompetitiveDimensionType.PRODUCT_OVERLAP, "Product overlap"),
        (CompetitiveDimensionType.GEOGRAPHIC_OVERLAP, "Geographic overlap"),
        (CompetitiveDimensionType.CUSTOMER_OVERLAP, "Customer overlap"),
        (CompetitiveDimensionType.SCALE_COMPARISON, "Scale comparison"),
        (CompetitiveDimensionType.MOAT_EVIDENCE, "Moat evidence"),
        (CompetitiveDimensionType.OPPOSING_EVIDENCE, "Opposing evidence"),
    ):
        if not dimension_groups.get(dimension_type):
            gaps.append({
                "key": f"competitive_{dimension_type.lower()}",
                "label": f"{label} unavailable",
                "reason": f"No reviewed {label.lower()} dimension is available for the selected competitive snapshot.",
                "source": "competitive-position",
                "next_action": "Collect and review company filings, investor materials, and permitted industry sources for this dimension.",
            })
    gaps.append({
        "key": "competitive_market_share",
        "label": "Market-share series unavailable",
        "reason": "No reviewed market-share series with source and methodology labels is available yet.",
        "source": "competitive-position",
        "next_action": "Add a licensed or official market-share source and record methodology, geography, period, and denominator.",
    })
    if not snapshot.source_document_id:
        gaps.append({
            "key": "competitive_source_document",
            "label": "Source document unavailable",
            "reason": "The selected competitive snapshot is not linked to a source document.",
            "source": "competitive-position",
            "next_action": "Rebuild from reviewed Company 360 profiles with source documents.",
        })
    return gaps


def serialize_product_catalog_snapshot(snapshot: ProductCatalogSnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "summary": snapshot.summary,
        "chronology_note": snapshot.chronology_note,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "source": serialize_profile_source(snapshot.source_document) if snapshot.source_document_id else None,
    }


def serialize_product_catalog_history(snapshot: ProductCatalogSnapshot, current: ProductCatalogSnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "offering_count": snapshot.offerings.count(),
        "change_count": snapshot.changes.count(),
        "selected": snapshot.id == current.id,
    }


def serialize_product_offering(offering: ProductOffering) -> dict[str, object]:
    return {
        "id": offering.id,
        "parent_id": offering.parent_id,
        "offering_type": offering.offering_type,
        "offering_type_label": offering.get_offering_type_display(),
        "name": offering.name,
        "description": offering.description,
        "availability": offering.availability,
        "geography": offering.geography,
        "customer_segment": offering.customer_segment,
        "evidence_text": offering.evidence_text,
        "confidence_score": decimal_to_float(offering.confidence_score),
        "price_count": offering.price_observations.count(),
    }


def serialize_product_change(change: ProductChange) -> dict[str, object]:
    return {
        "id": change.id,
        "offering_id": change.offering_id,
        "offering_name": change.offering.name if change.offering_id else "",
        "change_type": change.change_type,
        "change_type_label": change.get_change_type_display(),
        "title": change.title,
        "announcement_date": change.announcement_date.isoformat() if change.announcement_date else None,
        "effective_date": change.effective_date.isoformat() if change.effective_date else None,
        "before_state": change.before_state,
        "after_state": change.after_state,
        "evidence_text": change.evidence_text,
        "confidence_score": decimal_to_float(change.confidence_score),
        "source": serialize_profile_source(change.source_document) if change.source_document_id else None,
        "linked_event": serialize_business_event(change.linked_event) if change.linked_event_id else None,
    }


def serialize_price_observation(price: PriceObservation) -> dict[str, object]:
    return {
        "id": price.id,
        "offering_id": price.offering_id,
        "offering_name": price.offering.name,
        "observed_date": price.observed_date.isoformat(),
        "effective_date": price.effective_date.isoformat() if price.effective_date else None,
        "amount": decimal_to_float(price.amount),
        "currency": price.currency,
        "billing_period": price.billing_period,
        "geography": price.geography,
        "customer_segment": price.customer_segment,
        "tax_treatment": price.tax_treatment,
        "is_promotional": price.is_promotional,
        "evidence_text": price.evidence_text,
        "confidence_score": decimal_to_float(price.confidence_score),
        "source": serialize_profile_source(price.source_document) if price.source_document_id else None,
    }


def product_before_after_rows(changes: list[ProductChange]) -> list[dict[str, object]]:
    return [
        {
            "change_id": change.id,
            "title": change.title,
            "change_type": change.change_type,
            "announcement_date": change.announcement_date.isoformat() if change.announcement_date else None,
            "effective_date": change.effective_date.isoformat() if change.effective_date else None,
            "before": change.before_state,
            "after": change.after_state,
        }
        for change in changes
        if change.before_state or change.after_state
    ]


def product_pricing_evidence(
    snapshot: ProductCatalogSnapshot,
    offerings: list[ProductOffering],
    changes: list[ProductChange],
    prices: list[PriceObservation],
) -> list[dict[str, object]]:
    sources = []
    seen = set()
    if snapshot.source_document_id:
        sources.append(serialize_profile_source(snapshot.source_document))
        seen.add(snapshot.source_document_id)
    for row in [*changes, *prices]:
        if row.source_document_id and row.source_document_id not in seen:
            sources.append(serialize_profile_source(row.source_document))
            seen.add(row.source_document_id)
    return sources


def product_pricing_source_gaps(
    company: Company,
    snapshot: ProductCatalogSnapshot,
    offerings: list[ProductOffering],
    changes: list[ProductChange],
    prices: list[PriceObservation],
) -> list[dict[str, str]]:
    gaps = []
    if not offerings:
        gaps.append({"key": "product_offerings", "label": "Product catalog unavailable", "reason": f"No reviewed product offerings are available for {company.name}.", "source": "product-pricing-history", "next_action": "Review Company 360 products and official product pages."})
    if not changes:
        gaps.append({"key": "product_change_timeline", "label": "Product timeline unavailable", "reason": "No reviewed launch, update, rename, bundle, discontinuation, migration, or packaging events are available.", "source": "product-pricing-history", "next_action": "Review product/pricing events and official announcements."})
    if not prices:
        gaps.append({"key": "product_list_prices", "label": "List prices unavailable", "reason": "No reviewed list-price observations with full context are available. Missing prices are not estimated or treated as zero.", "source": "product-pricing-history", "next_action": "Collect official pricing pages or filings with currency, geography, billing period, tax, promotion, and customer-segment context."})
    if not snapshot.source_document_id:
        gaps.append({"key": "product_catalog_source", "label": "Catalog source unavailable", "reason": "The selected product catalog snapshot is not linked to a source document.", "source": "product-pricing-history", "next_action": "Rebuild from reviewed Company 360 profiles with source documents."})
    return gaps


def serialize_acquisition_deal(deal: AcquisitionLifecycleDeal, *, include_events: bool) -> dict[str, object]:
    payload = {
        "id": deal.id,
        "slug": deal.slug,
        "target_name": deal.target_name,
        "target_company": serialize_company(deal.target_company) if deal.target_company_id else None,
        "transaction_type": deal.transaction_type,
        "transaction_type_label": deal.get_transaction_type_display(),
        "current_stage": deal.current_stage,
        "current_stage_label": deal.get_current_stage_display(),
        "outcome_category": deal.outcome_category,
        "outcome_category_label": deal.get_outcome_category_display(),
        "announcement_date": deal.announcement_date.isoformat() if deal.announcement_date else None,
        "expected_close_date": deal.expected_close_date.isoformat() if deal.expected_close_date else None,
        "close_date": deal.close_date.isoformat() if deal.close_date else None,
        "purchase_price": decimal_to_float_or_none(deal.purchase_price),
        "currency": deal.currency,
        "payment_form": deal.payment_form,
        "approvals": deal.approvals if isinstance(deal.approvals, list) else [],
        "conditions": deal.conditions if isinstance(deal.conditions, list) else [],
        "management_rationale": deal.management_rationale,
        "promised_synergies": deal.promised_synergies,
        "integration_summary": deal.integration_summary,
        "outcome_review": deal.outcome_review,
        "confidence_score": decimal_to_float(deal.confidence_score),
        "review_status": deal.review_status,
        "source": serialize_profile_source(deal.source_document) if deal.source_document_id else None,
        "linked_event": serialize_business_event(deal.linked_event) if deal.linked_event_id else None,
        "linked_strategic_turn": {
            "id": deal.linked_strategic_turn_id,
            "title": deal.linked_strategic_turn.title,
            "turn_type": deal.linked_strategic_turn.turn_type,
        } if deal.linked_strategic_turn_id else None,
        "updated_at": deal.updated_at.isoformat(),
        "stage_event_count": deal.stage_events.count(),
    }
    if include_events:
        payload["stage_events"] = [serialize_acquisition_event(row) for row in deal.stage_events.all()]
    return payload


def serialize_acquisition_event(event: AcquisitionLifecycleEvent) -> dict[str, object]:
    return {
        "id": event.id,
        "stage": event.stage,
        "stage_label": event.get_stage_display(),
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "title": event.title,
        "description": event.description,
        "price_revision": decimal_to_float_or_none(event.price_revision),
        "currency": event.currency,
        "evidence_text": event.evidence_text,
        "confidence_score": decimal_to_float(event.confidence_score),
        "review_status": event.review_status,
        "source": serialize_profile_source(event.source_document) if event.source_document_id else None,
        "linked_milestone": {
            "id": event.linked_milestone_id,
            "slug": event.linked_milestone.slug,
            "title": event.linked_milestone.title,
            "current_status": event.linked_milestone.current_status,
        } if event.linked_milestone_id else None,
        "linked_product_change": {
            "id": event.linked_product_change_id,
            "title": event.linked_product_change.title,
            "change_type": event.linked_product_change.change_type,
        } if event.linked_product_change_id else None,
    }


def acquisition_portfolio_summary(deals: list[AcquisitionLifecycleDeal]) -> dict[str, object]:
    by_stage = defaultdict(int)
    by_outcome = defaultdict(int)
    by_type = defaultdict(int)
    for deal in deals:
        by_stage[deal.current_stage] += 1
        by_outcome[deal.outcome_category] += 1
        by_type[deal.transaction_type] += 1
    return {
        "by_stage": [{"key": key, "label": dict(AcquisitionStage.choices).get(key, key), "count": value} for key, value in sorted(by_stage.items())],
        "by_outcome": [{"key": key, "label": dict(AcquisitionOutcomeCategory.choices).get(key, key), "count": value} for key, value in sorted(by_outcome.items())],
        "by_transaction_type": [{"key": key, "label": dict(AcquisitionTransactionType.choices).get(key, key), "count": value} for key, value in sorted(by_type.items())],
    }


def acquisition_lifecycle_filters(
    company: Company,
    selected_stage: str,
    selected_transaction_type: str,
    selected_outcome: str,
    selected_deal: str,
) -> dict[str, object]:
    all_deals = AcquisitionLifecycleDeal.objects.filter(company=company, is_published=True, review_status="REVIEWED")
    return {
        "stages": sorted({row.current_stage for row in all_deals}),
        "transaction_types": sorted({row.transaction_type for row in all_deals}),
        "outcomes": sorted({row.outcome_category for row in all_deals}),
        "selected_stage": selected_stage,
        "selected_transaction_type": selected_transaction_type,
        "selected_outcome": selected_outcome,
        "selected_deal": selected_deal,
    }


def acquisition_lifecycle_evidence(
    deals: list[AcquisitionLifecycleDeal],
    stage_events: list[AcquisitionLifecycleEvent],
) -> list[dict[str, object]]:
    sources = []
    seen = set()
    for row in [*deals, *stage_events]:
        if row.source_document_id and row.source_document_id not in seen:
            sources.append(serialize_profile_source(row.source_document))
            seen.add(row.source_document_id)
    return sources


def acquisition_lifecycle_source_gaps(
    company: Company,
    deals: list[AcquisitionLifecycleDeal],
    selected: AcquisitionLifecycleDeal | None,
) -> list[dict[str, str]]:
    gaps = []
    if not deals:
        gaps.append({"key": "acquisition_deals", "label": "Acquisition deals unavailable", "reason": f"No reviewed acquisition lifecycle deal is available for {company.name}.", "source": "acquisition-lifecycle", "next_action": "Review acquisition events, annual filings, investor materials, and current portfolio disclosures before creating lifecycle records."})
        return gaps
    if selected and selected.purchase_price is None and not selected.payment_form:
        gaps.append({"key": "acquisition_deal_terms", "label": "Deal consideration unavailable", "reason": "No reviewed purchase price or payment-form evidence is linked to the selected deal.", "source": "acquisition-lifecycle", "next_action": "Review announcement releases, merger agreements, and annual filing acquisition footnotes."})
    if selected and not selected.approvals:
        gaps.append({"key": "acquisition_approvals", "label": "Approvals unavailable", "reason": "No reviewed regulatory, shareholder, board, or court approval timeline is linked to the selected deal.", "source": "acquisition-lifecycle", "next_action": "Add approval milestones only after source-backed review."})
    if selected and not selected.promised_synergies:
        gaps.append({"key": "acquisition_promised_synergies", "label": "Promised synergies unavailable", "reason": "No reviewed management synergy target is linked to the selected deal.", "source": "acquisition-lifecycle", "next_action": "Capture management promises from deal announcements or investor presentations without treating them as achieved outcomes."})
    if selected and not selected.stage_events.exists():
        gaps.append({"key": "acquisition_stage_events", "label": "Lifecycle timeline unavailable", "reason": "No reviewed stage events are linked to the selected deal.", "source": "acquisition-lifecycle", "next_action": "Add announcement, approval, close, integration, impairment, divestiture, or review events."})
    if selected and not selected.outcome_review:
        gaps.append({"key": "acquisition_outcome_review", "label": "Outcome review unavailable", "reason": "No reviewed post-close outcome assessment is available for the selected deal.", "source": "acquisition-lifecycle", "next_action": "Review later filings and operating evidence before classifying the outcome."})
    return gaps


def serialize_dependency_snapshot(snapshot: CustomerSupplierDependencySnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "summary": snapshot.summary,
        "methodology": snapshot.methodology,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "source": serialize_profile_source(snapshot.source_document) if snapshot.source_document_id else None,
    }


def serialize_dependency_snapshot_history(
    snapshot: CustomerSupplierDependencySnapshot,
    current: CustomerSupplierDependencySnapshot,
) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "dependency_count": snapshot.dependencies.count(),
        "selected": snapshot.id == current.id,
    }


def serialize_dependency(row: CustomerSupplierDependency) -> dict[str, object]:
    return {
        "id": row.id,
        "dependency_type": row.dependency_type,
        "dependency_type_label": row.get_dependency_type_display(),
        "counterparty_name": row.counterparty_name,
        "counterparty_company": serialize_company(row.counterparty_company) if row.counterparty_company_id else None,
        "is_named_counterparty": row.is_named_counterparty,
        "materiality_band": row.materiality_band,
        "materiality_band_label": row.get_materiality_band_display(),
        "disclosure_confidence": row.disclosure_confidence,
        "disclosure_confidence_label": row.get_disclosure_confidence_display(),
        "concentration_percent": decimal_to_float_or_none(row.concentration_percent),
        "geography": row.geography,
        "product_scope": row.product_scope,
        "relationship_summary": row.relationship_summary,
        "risk_summary": row.risk_summary,
        "evidence_text": row.evidence_text,
        "confidence_score": decimal_to_float(row.confidence_score),
        "source": serialize_profile_source(row.source_document) if row.source_document_id else None,
        "contract_term_count": row.contract_terms.count(),
    }


def serialize_dependency_contract_term(term: DependencyContractTerm) -> dict[str, object]:
    return {
        "id": term.id,
        "dependency_id": term.dependency_id,
        "counterparty_name": term.dependency.counterparty_name,
        "term_type": term.term_type,
        "term_type_label": term.get_term_type_display(),
        "effective_date": term.effective_date.isoformat() if term.effective_date else None,
        "expiration_date": term.expiration_date.isoformat() if term.expiration_date else None,
        "description": term.description,
        "evidence_text": term.evidence_text,
        "confidence_score": decimal_to_float(term.confidence_score),
        "review_status": term.review_status,
        "source": serialize_profile_source(term.source_document) if term.source_document_id else None,
    }


def dependency_map(dependencies: list[CustomerSupplierDependency]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in dependencies:
        grouped[row.dependency_type].append(serialize_dependency(row))
    return dict(grouped)


def customer_supplier_dependency_evidence(
    snapshot: CustomerSupplierDependencySnapshot,
    dependencies: list[CustomerSupplierDependency],
) -> list[dict[str, object]]:
    sources = []
    seen = set()
    if snapshot.source_document_id:
        sources.append(serialize_profile_source(snapshot.source_document))
        seen.add(snapshot.source_document_id)
    for dependency in dependencies:
        if dependency.source_document_id and dependency.source_document_id not in seen:
            sources.append(serialize_profile_source(dependency.source_document))
            seen.add(dependency.source_document_id)
        for term in dependency.contract_terms.all():
            if term.source_document_id and term.source_document_id not in seen:
                sources.append(serialize_profile_source(term.source_document))
                seen.add(term.source_document_id)
    return sources


def customer_supplier_dependency_source_gaps(
    company: Company,
    snapshot: CustomerSupplierDependencySnapshot,
    dependencies: list[CustomerSupplierDependency],
) -> list[dict[str, str]]:
    gaps = []
    if not dependencies:
        gaps.append({"key": "dependency_relationships", "label": "Dependency relationships unavailable", "reason": f"No reviewed dependency relationships are available for {company.name} under the selected filters.", "source": "customer-supplier-dependency", "next_action": "Review Company 360 customers, business-model channels, partner components, and official concentration disclosures."})
        return gaps
    if not any(row.is_named_counterparty for row in dependencies):
        gaps.append({"key": "named_counterparties", "label": "Named counterparties unavailable", "reason": "The reviewed baseline contains category-only dependencies. It does not identify customers, suppliers, platforms, or distributors unless the source explicitly names them.", "source": "customer-supplier-dependency", "next_action": "Review official filings and contracts for named counterparties before publishing them."})
    if not any(row.concentration_percent is not None for row in dependencies):
        gaps.append({"key": "concentration_percentages", "label": "Concentration percentages unavailable", "reason": "No reviewed customer or supplier concentration percentage is linked to the selected dependency set.", "source": "customer-supplier-dependency", "next_action": "Review major-customer and major-supplier concentration notes in annual filings."})
    if not any(row.contract_terms.exists() for row in dependencies):
        gaps.append({"key": "dependency_contract_terms", "label": "Contract terms unavailable", "reason": "No reviewed renewal, expiration, exclusivity, minimum commitment, or termination-risk terms are linked to the selected dependencies.", "source": "customer-supplier-dependency", "next_action": "Add contract terms only when disclosed in filings, agreements, or reviewed source documents."})
    if not any(row.dependency_type in {DependencyType.SUPPLIER, DependencyType.MANUFACTURER, DependencyType.INFRASTRUCTURE} for row in dependencies):
        gaps.append({"key": "critical_supplier_detail", "label": "Critical supplier detail unavailable", "reason": "No reviewed critical supplier, manufacturer, or infrastructure-provider category is available under the selected filters.", "source": "customer-supplier-dependency", "next_action": "Review supply-chain and infrastructure risk disclosures without inferring undisclosed suppliers."})
    if not snapshot.source_document_id:
        gaps.append({"key": "dependency_source_document", "label": "Dependency source unavailable", "reason": "The selected dependency snapshot is not linked to a source document.", "source": "customer-supplier-dependency", "next_action": "Rebuild from reviewed Company 360 profiles or business-model maps with source documents."})
    return gaps


def serialize_guidance_comparison(row: EarningsGuidanceComparison) -> dict[str, object]:
    forecast = decimal_to_float(row.forecast_value)
    actual = decimal_to_float(row.actual_value)
    variance = None if not forecast else round(((actual - forecast) / abs(forecast)) * 100, 2)
    return {
        "metric_name": row.metric_name,
        "forecast_value": forecast,
        "actual_value": actual,
        "variance_pct": variance,
        "unit": row.unit,
        "comparison_status": row.comparison_status,
        "forecast_evidence": row.forecast_evidence,
        "actual_evidence": row.actual_evidence,
        "confidence_score": decimal_to_float(row.confidence_score),
        "forecast_source": serialize_profile_source(row.forecast_source),
        "actual_source": serialize_profile_source(row.actual_source),
    }


@require_GET
def dashboard_data(request: HttpRequest) -> JsonResponse:
    limit = bounded_limit(request, default=10, maximum=50)
    requested_section = (request.GET.get("section") or "").strip()
    requested_page = bounded_page(request)
    company_slug = (request.GET.get("company") or "").strip()
    scoped_company = get_company(company_slug) if company_slug else None

    def page_for(section: str) -> int:
        return requested_page if requested_section == section else 1

    event_candidates = BusinessEvent.objects.select_related("company", "source_document")
    turn_candidates = StrategicTurn.objects.select_related("company")
    if scoped_company:
        event_candidates = event_candidates.filter(company=scoped_company)
        turn_candidates = turn_candidates.filter(company=scoped_company)

    latest_event_candidates = list(
        event_candidates
        .exclude(actual_change="")
        .order_by("-event_date", "-created_at")[:500]
    )
    latest_events = eligible_events(latest_event_candidates, 500)
    impact_event_candidates = list(
        event_candidates
        .filter(company_id__in=MarketPrice.objects.exclude(company_id__isnull=True).values("company_id"))
        .exclude(actual_change="")
        .order_by("-event_date", "-created_at")[:500]
    )
    impact_events = eligible_events(impact_event_candidates, 500)
    latest_turn_candidates = list(turn_candidates.order_by("-start_date", "-created_at")[:500])
    turn_source_counts = dict(
        StrategicTurnSource.objects.filter(strategic_turn__in=latest_turn_candidates)
        .values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    latest_turns = eligible_turns(latest_turn_candidates, turn_source_counts, 500)
    pattern_rows = strategic_pattern_rows(500)
    risk_event_candidates = list(
        event_candidates
        .filter(event_type__in=RISK_EVENT_TYPES)
        .exclude(actual_change="")
        .order_by("-event_date", "-created_at")[:500]
    )
    risk_events = eligible_risk_events(risk_event_candidates, 500)
    company_queryset = (
        Company.objects.annotate(
            source_count=Count("source_documents", distinct=True),
            event_count=Count("business_events", distinct=True),
            turn_count=Count("strategic_turns", distinct=True),
        )
        .filter(event_count__gt=0)
    )
    if scoped_company:
        if scoped_company.industry:
            company_queryset = company_queryset.filter(industry=scoped_company.industry)
        elif scoped_company.country:
            company_queryset = company_queryset.filter(country=scoped_company.country)
        company_queryset = company_queryset.exclude(id=scoped_company.id)
    company_rows = list(company_queryset.order_by("-event_count", "name")[:500])
    compare_rows = compare_turn_rows(500)
    scorecard_rows = scorecard_candidate_rows(500)
    impact_rows = market_impact_rows(impact_events, 500)
    latest_events_page = paginate_rows(latest_events, page_for("latest_moves"), limit)
    latest_turns_page = paginate_rows(latest_turns, page_for("strategic_turns"), limit)
    pattern_rows_page = paginate_rows(pattern_rows, page_for("patterns"), limit)
    risk_events_page = paginate_rows(risk_events, page_for("risk_signals"), limit)
    impact_rows_page = paginate_rows(impact_rows, page_for("turn_impact"), limit)
    scorecard_rows_page = paginate_rows(scorecard_rows, page_for("scorecards"), limit)
    compare_rows_page = paginate_rows(compare_rows, page_for("compare"), limit)
    company_rows_page = paginate_rows(company_rows, page_for("company_situations"), limit)
    sections = {
        "latest_moves": section_payload(
            key="latest_moves",
            items=[serialize_business_event(event) for event in latest_events_page],
            raw_count=len(latest_event_candidates),
            eligible_count=len(latest_events),
            page=page_for("latest_moves"),
            page_size=limit,
            source_gaps=section_gaps("latest_moves", latest_events, "Need dated, source-backed events with specific company actions."),
            required_data=["event_date", "source_document", "actual_change", "source_claim", "confidence_score"],
            next_action="Ingest SEC 8-K, company press releases, and supporting news/Wikipedia references.",
        ),
        "strategic_turns": section_payload(
            key="strategic_turns",
            items=[serialize_strategic_turn(turn, source_count=turn_source_counts.get(turn.id, 0)) for turn in latest_turns_page],
            raw_count=len(latest_turn_candidates),
            eligible_count=len(latest_turns),
            page=page_for("strategic_turns"),
            page_size=limit,
            source_gaps=section_gaps("strategic_turns", latest_turns, "Current strategic turns are generic or missing eligible turn quality."),
            required_data=["start_date", "specific_title", "source_count", "confidence_score", "specific_action"],
            next_action="Rebuild turns from eligible event clusters only.",
        ),
        "patterns": section_payload(
            key="patterns",
            items=pattern_rows_page,
            raw_count=StrategicTurn.objects.count(),
            eligible_count=len(pattern_rows),
            page=page_for("patterns"),
            page_size=limit,
            source_gaps=section_gaps("patterns", pattern_rows, "No eligible strategic turns are available for pattern grouping."),
            required_data=["eligible_turn", "pattern_label", "sample_size", "confidence_status"],
            next_action="Create reviewed pattern taxonomy after turn rebuild.",
        ),
        "risk_signals": section_payload(
            key="risk_signals",
            items=[serialize_risk_signal(event) for event in risk_events_page],
            raw_count=len(risk_event_candidates),
            eligible_count=len(risk_events),
            page=page_for("risk_signals"),
            page_size=limit,
            source_gaps=section_gaps("risk_signals", risk_events, "Need source-backed risk events or calculated financial/market signals."),
            required_data=["event_date", "source_document", "risk_event_type", "method", "confidence_score"],
            next_action="Keep SEC risk candidates separate from strategic moves and add financial/market risk calculations.",
        ),
        "turn_impact": section_payload(
            key="turn_impact",
            items=impact_rows_page,
            raw_count=len(impact_event_candidates),
            eligible_count=len(impact_rows),
            page=page_for("turn_impact"),
            page_size=limit,
            source_gaps=section_gaps("turn_impact", impact_rows, "Need eligible events with ticker mapping, market prices, and SEC companyfacts."),
            required_data=["eligible_event", "ticker", "daily_prices", "event_window_returns", "financial_facts"],
            next_action="Run market price and SEC companyfacts ingestion for companies with eligible events.",
        ),
        "scorecards": section_payload(
            key="scorecards",
            items=scorecard_rows_page,
            raw_count=StrategicTurn.objects.count(),
            eligible_count=len(scorecard_rows),
            page=page_for("scorecards"),
            page_size=limit,
            source_gaps=section_gaps("scorecards", scorecard_rows, "No eligible strategic turns with impact dimensions are available."),
            required_data=["eligible_turn", "source_count", "market_reaction", "financial_impact", "confidence_reason"],
            next_action="Add market prices, SEC companyfacts, and evidence-backed score dimensions.",
        ),
        "compare": section_payload(
            key="compare",
            items=compare_rows_page,
            raw_count=StrategicTurn.objects.count(),
            eligible_count=len(compare_rows),
            page=page_for("compare"),
            page_size=limit,
            source_gaps=section_gaps("compare", compare_rows, "Need at least two eligible turns in the same comparable pattern/type."),
            required_data=["eligible_turns", "same_pattern_or_type", "dates", "source_confidence"],
            next_action="Rebuild eligible strategic turns and assign pattern labels.",
        ),
        "company_situations": section_payload(
            key="company_situations",
            items=[serialize_company_situation(company, scoped_company) for company in company_rows_page],
            raw_count=Company.objects.count(),
            eligible_count=len(company_rows),
            page=page_for("company_situations"),
            page_size=limit,
            source_gaps=section_gaps("company_situations", company_rows, "Need company situation dimensions beyond sector/country."),
            required_data=["sector", "country", "stage", "revenue_band", "business_model", "pressure_trigger"],
            next_action="Ingest companyfacts and classify company situation dimensions.",
        ),
    }
    gaps = dashboard_source_gaps(pattern_rows, risk_events, compare_rows, impact_rows)
    persist_source_gaps(gaps)

    return JsonResponse(
        {
            "scope": serialize_dashboard_scope(scoped_company),
            "latest_events": [serialize_business_event(event) for event in latest_events],
            "latest_turns": [serialize_strategic_turn(turn, source_count=turn_source_counts.get(turn.id, 0)) for turn in latest_turns],
            "patterns": pattern_rows,
            "risk_signals": [serialize_risk_signal(event) for event in risk_events],
            "turn_impact": impact_rows,
            "source_confidence": source_confidence_summary(),
            "scorecard_candidates": scorecard_rows,
            "company_situations": [serialize_company_situation(company, scoped_company) for company in company_rows],
            "compare_examples": compare_rows,
            "source_gaps": gaps,
            "sections": sections,
        }
    )


@require_GET
def search(request: HttpRequest) -> JsonResponse:
    query = normalized_query(request)
    if not query:
        return JsonResponse({"error": "q is required"}, status=400)

    limit = bounded_limit(request, default=10, maximum=50)
    company_page = bounded_positive_int(request, "company_page", default=1, maximum=1000)
    event_page = bounded_positive_int(request, "event_page", default=1, maximum=1000)
    turn_page = bounded_positive_int(request, "turn_page", default=1, maximum=1000)
    company_queryset = Company.objects.filter(
        Q(name__icontains=query)
        | Q(slug__icontains=query)
        | Q(industry__icontains=query)
        | Q(country__icontains=query)
    ).annotate(
        source_count=Count("source_documents", distinct=True),
        event_count=Count("business_events", distinct=True),
        turn_count=Count("strategic_turns", distinct=True),
    ).order_by("name")
    company_total = company_queryset.count()
    company_rows = company_queryset[pagination_offset(company_page, limit) : pagination_offset(company_page, limit) + limit]

    all_event_rows = eligible_events(search_business_events(query, 500), 500)
    event_rows = paginate_rows(all_event_rows, event_page, limit)
    all_turn_rows = search_strategic_turns(query, 500)
    turn_source_counts = dict(
        StrategicTurnSource.objects.filter(strategic_turn__in=all_turn_rows)
        .values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    all_turn_rows = eligible_turns(all_turn_rows, turn_source_counts, 500)
    turn_rows = paginate_rows(all_turn_rows, turn_page, limit)

    return JsonResponse(
        {
            "query": query,
            "language": request.GET.get("language") or "en",
            "results": {
                "companies": [serialize_company(company) for company in company_rows],
                "events": [serialize_business_event(event) for event in event_rows],
                "strategic_turns": [
                    serialize_strategic_turn(turn, source_count=turn_source_counts.get(turn.id, 0))
                    for turn in turn_rows
                ],
            },
            "pagination": {
                "companies": pagination_meta(company_total, company_page, limit),
                "events": pagination_meta(len(all_event_rows), event_page, limit),
                "strategic_turns": pagination_meta(len(all_turn_rows), turn_page, limit),
            },
        }
    )


@require_GET
def search_suggest(request: HttpRequest) -> JsonResponse:
    query = normalized_query(request)
    if not query:
        return JsonResponse({"error": "q is required"}, status=400)

    limit = bounded_limit(request, default=8, maximum=25)
    queryset = Company.objects.filter(
        Q(name__istartswith=query)
        | Q(slug__istartswith=query)
        | Q(name__icontains=query)
        | Q(industry__icontains=query)
    )
    if connection.vendor == "postgresql":
        queryset = (
            queryset.annotate(similarity=TrigramSimilarity("name", query))
            .filter(Q(similarity__gte=0.1) | Q(name__istartswith=query) | Q(slug__istartswith=query))
            .order_by("-similarity", "name")
        )
    else:
        queryset = queryset.order_by("name")

    return JsonResponse(
        {
            "query": query,
            "language": request.GET.get("language") or "en",
            "suggestions": [
                {
                    "type": "company",
                    "label": company.name,
                    "slug": company.slug,
                    "sector": company.industry,
                    "description": company.country,
                }
                for company in queryset[:limit]
            ],
        }
    )


@require_GET
def company_events(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    limit = bounded_limit(request, default=100, maximum=500)
    rows = [
        serialize_business_event(event)
        for event in BusinessEvent.objects.filter(company=company)
        .select_related("company", "source_document")
        .order_by("event_date", "id")[:limit]
    ]
    return JsonResponse({"company": serialize_company(company), "events": rows})


@require_GET
def company_strategic_turns(request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    limit = bounded_limit(request, default=100, maximum=500)
    source_counts = dict(
        StrategicTurnSource.objects.filter(strategic_turn__company=company)
        .values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    rows = [
        serialize_strategic_turn(turn, source_count=source_counts.get(turn.id, 0))
        for turn in StrategicTurn.objects.filter(company=company).order_by("start_date", "id")[:limit]
    ]
    return JsonResponse({"company": serialize_company(company), "strategic_turns": rows})


@require_GET
def jobs(request: HttpRequest) -> JsonResponse:
    limit = bounded_limit(request, default=100, maximum=500)
    rows = [
        serialize_job(job)
        for job in IngestionJob.objects.select_related("company").order_by("-created_at")[:limit]
    ]
    return JsonResponse({"jobs": rows})


@require_GET
def source_gaps(request: HttpRequest) -> JsonResponse:
    status = request.GET.get("status") or "OPEN"
    dashboard = request.GET.get("dashboard") or ""
    queryset = SourceGap.objects.select_related("company")
    if status:
        queryset = queryset.filter(status=status)
    if dashboard:
        queryset = queryset.filter(dashboard=dashboard)
    return JsonResponse({"source_gaps": [serialize_source_gap(gap) for gap in queryset.order_by("-updated_at")[:200]]})


@require_GET
def job_detail(_request: HttpRequest, job_id: int) -> JsonResponse:
    try:
        job = IngestionJob.objects.select_related("company").get(id=job_id)
    except IngestionJob.DoesNotExist as exc:
        raise Http404("Job not found") from exc
    return JsonResponse({"job": serialize_job(job)})


@require_POST
def run_daily_update(_request: HttpRequest) -> JsonResponse:
    call_command("daily_company_update", limit=20, skip_gdelt=True)
    return JsonResponse({"status": "queued_or_completed", "job_type": "daily_company_update"})


@require_POST
def refresh_company(_request: HttpRequest, slug: str) -> JsonResponse:
    company = get_company(slug)
    call_command(
        "extract_sector_events",
        company=company.name,
        limit=20,
        forms="10-K",
        filing_limit=8,
        reuse_extractions=True,
    )
    return JsonResponse({"status": "completed", "company": serialize_company(company)})


def get_company(slug: str) -> Company:
    try:
        return Company.objects.get(slug=slug)
    except Company.DoesNotExist as exc:
        raise Http404("Company not found") from exc


def bounded_limit(request: HttpRequest, *, default: int, maximum: int) -> int:
    return bounded_positive_int(request, "limit", default=default, maximum=maximum)


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def bounded_page(request: HttpRequest) -> int:
    return bounded_positive_int(request, "page", default=1, maximum=1000)


def bounded_positive_int(request: HttpRequest, name: str, *, default: int, maximum: int) -> int:
    raw = request.GET.get(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, min(value, maximum))


def pagination_offset(page: int, page_size: int) -> int:
    return max(page - 1, 0) * page_size


def paginate_rows(rows: list, page: int, page_size: int) -> list:
    offset = pagination_offset(page, page_size)
    return rows[offset : offset + page_size]


def pagination_meta(total: int, page: int, page_size: int) -> dict[str, object]:
    total_pages = max(1, ((total + page_size - 1) // page_size) if page_size else 1)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }


def normalized_query(request: HttpRequest) -> str:
    return " ".join((request.GET.get("q") or "").strip().split())


def search_business_events(query: str, limit: int) -> list[BusinessEvent]:
    fallback_queryset = (
        BusinessEvent.objects.select_related("company", "source_document")
        .exclude(actual_change="")
        .filter(
            Q(actual_change__icontains=query)
            | Q(source_claim__icontains=query)
            | Q(decision__icontains=query)
            | Q(outcome__icontains=query)
            | Q(event_type__icontains=query)
            | Q(decision_theme__icontains=query)
            | Q(company__name__icontains=query)
        )
    )
    if connection.vendor != "postgresql":
        return list(fallback_queryset.order_by("-event_date", "id")[:limit])

    vector = (
        SearchVector("actual_change", weight="A")
        + SearchVector("source_claim", weight="B")
        + SearchVector("decision", weight="B")
        + SearchVector("outcome", weight="C")
        + SearchVector("event_type", weight="C")
        + SearchVector("decision_theme", weight="C")
        + SearchVector("company__name", weight="A")
    )
    search_query = SearchQuery(query, search_type="websearch")
    return list(
        BusinessEvent.objects.select_related("company", "source_document")
        .exclude(actual_change="")
        .annotate(rank=SearchRank(vector, search_query))
        .filter(Q(rank__gt=0) | Q(actual_change__icontains=query) | Q(company__name__icontains=query))
        .order_by("-rank", "-event_date", "id")[:limit]
    )


def search_strategic_turns(query: str, limit: int) -> list[StrategicTurn]:
    fallback_queryset = StrategicTurn.objects.select_related("company").filter(
        Q(title__icontains=query)
        | Q(summary__icontains=query)
        | Q(decision__icontains=query)
        | Q(outcome__icontains=query)
        | Q(founder_lesson__icontains=query)
        | Q(turn_type__icontains=query)
        | Q(company__name__icontains=query)
    )
    if connection.vendor != "postgresql":
        return list(fallback_queryset.order_by("-start_date", "id")[:limit])

    vector = (
        SearchVector("title", weight="A")
        + SearchVector("summary", weight="A")
        + SearchVector("decision", weight="B")
        + SearchVector("outcome", weight="C")
        + SearchVector("founder_lesson", weight="B")
        + SearchVector("turn_type", weight="C")
        + SearchVector("company__name", weight="A")
    )
    search_query = SearchQuery(query, search_type="websearch")
    return list(
        StrategicTurn.objects.select_related("company")
        .annotate(rank=SearchRank(vector, search_query))
        .filter(Q(rank__gt=0) | Q(title__icontains=query) | Q(company__name__icontains=query))
        .order_by("-rank", "-start_date", "id")[:limit]
    )


def is_specific_strategic_turn(turn: StrategicTurn) -> bool:
    return turn_eligibility(turn, source_count=1).eligible


def eligible_events(candidates: list[BusinessEvent], limit: int) -> list[BusinessEvent]:
    rows = []
    for event in candidates:
        if event_eligibility(event).eligible:
            rows.append(event)
        if len(rows) >= limit:
            break
    return rows


def eligible_risk_events(candidates: list[BusinessEvent], limit: int) -> list[BusinessEvent]:
    rows = []
    for event in candidates:
        if risk_event_eligibility(event).eligible:
            rows.append(event)
        if len(rows) >= limit:
            break
    return rows


def eligible_turns(candidates: list[StrategicTurn], source_counts: dict[int, int], limit: int) -> list[StrategicTurn]:
    rows = []
    for turn in candidates:
        if turn_eligibility(turn, source_count=source_counts.get(turn.id, 0)).eligible:
            rows.append(turn)
        if len(rows) >= limit:
            break
    return rows


def section_gaps(section: str, items: list, reason: str) -> list[dict[str, str]]:
    if items:
        return []
    return [
        source_gap_dict(
            key=f"{section}_unavailable",
            dashboard=section,
            reason=reason,
            source=f"ingestion.{section}",
            next_action="Run the required ingestion and quality-scoring tasks before exposing this dashboard section.",
        )
    ]


def strategic_pattern_rows(limit: int) -> list[dict[str, object]]:
    source_counts = dict(
        StrategicTurnSource.objects.values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    eligible = [
        turn
        for turn in StrategicTurn.objects.select_related("company").order_by("turn_type", "-start_date", "title")
        if turn_eligibility(turn, source_count=source_counts.get(turn.id, 0)).eligible
    ]
    by_type: dict[str, list[StrategicTurn]] = {}
    for turn in eligible:
        by_type.setdefault(turn.turn_type, []).append(turn)
    rows = []
    for turn_type, turns in sorted(by_type.items(), key=lambda item: (-len(item[1]), item[0]))[:limit]:
        examples = [
            {
                "id": turn.id,
                "company": turn.company.name,
                "company_slug": turn.company.slug,
                "title": turn.title,
                "start_date": turn.start_date.isoformat() if turn.start_date else None,
                "source_count": source_counts.get(turn.id, 0),
                "review_status": turn.review_status,
            }
            for turn in turns[:3]
        ]
        avg_confidence = sum(decimal_to_float(turn.confidence_score) for turn in turns) / len(turns)
        rows.append(
            {
                "pattern": turn_type,
                "sample_size": len(turns),
                "avg_confidence": round(avg_confidence, 3),
                "examples": examples,
                "confidence_status": confidence_status(len(turns), avg_confidence),
            }
        )
    return rows


def source_confidence_summary() -> dict[str, object]:
    event_summary = BusinessEvent.objects.aggregate(
        total=Count("id"),
        with_date=Count("id", filter=Q(event_date__isnull=False)),
        with_source=Count("id", filter=Q(source_document__isnull=False)),
        avg_confidence=Avg("confidence_score"),
    )
    turn_summary = StrategicTurn.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(is_published=True)),
        avg_confidence=Avg("confidence_score"),
    )
    source_types = list(
        SourceDocument.objects.values("source_api")
        .annotate(count=Count("id"))
        .order_by("-count", "source_api")
    )
    source_statuses = list(
        SourceDocument.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("-count", "status")
    )
    event_reviews = list(
        BusinessEvent.objects.values("review_status")
        .annotate(count=Count("id"))
        .order_by("-count", "review_status")
    )
    return {
        "events": {
            "total": event_summary["total"],
            "with_date": event_summary["with_date"],
            "with_source": event_summary["with_source"],
            "avg_confidence": decimal_to_float(event_summary["avg_confidence"]),
        },
        "turns": {
            "total": turn_summary["total"],
            "published": turn_summary["published"],
            "avg_confidence": decimal_to_float(turn_summary["avg_confidence"]),
        },
        "source_types": source_types,
        "source_statuses": source_statuses,
        "event_reviews": event_reviews,
        "market_prices": {
            "total": MarketPrice.objects.count(),
            "companies": MarketPrice.objects.exclude(company_id__isnull=True).values("company_id").distinct().count(),
            "latest_price_date": max_date_iso(MarketPrice.objects.aggregate(latest=Max("price_date"))["latest"]),
        },
        "financial_facts": {
            "total": FinancialFact.objects.count(),
            "companies": FinancialFact.objects.values("company_id").distinct().count(),
            "latest_filed": max_date_iso(FinancialFact.objects.aggregate(latest=Max("filed"))["latest"]),
        },
    }


def market_impact_rows(events: list[BusinessEvent], limit: int) -> list[dict[str, object]]:
    rows = []
    for event in events:
        if not event.event_date:
            continue
        ticker = ticker_for_company(event.company)
        if not ticker:
            continue
        base_price = price_on_or_before(event.company, ticker, event.event_date)
        if base_price is None or not base_price.close_price:
            continue
        windows = []
        for days in (1, 7, 30, 90):
            after_price = price_on_or_after(event.company, ticker, event.event_date + timedelta(days=days))
            if after_price is None or not after_price.close_price:
                continue
            windows.append(
                {
                    "window": f"T+{days}",
                    "days": days,
                    "price_date": after_price.price_date.isoformat(),
                    "close_price": decimal_to_float(after_price.close_price),
                    "return_pct": pct_change(base_price.close_price, after_price.close_price),
                }
            )
        facts = financial_snapshot(event.company)
        if not windows and not facts:
            continue
        rows.append(
            {
                "event": serialize_business_event(event),
                "company": event.company.name,
                "company_slug": event.company.slug,
                "ticker": ticker,
                "event_date": event.event_date.isoformat(),
                "base_price": {
                    "price_date": base_price.price_date.isoformat(),
                    "close_price": decimal_to_float(base_price.close_price),
                    "provider": base_price.provider,
                },
                "windows": windows,
                "financial_facts": facts,
                "quality": {
                    "eligible": bool(windows or facts),
                    "status": "eligible" if windows or facts else "ineligible",
                    "reasons": impact_reasons(windows, facts),
                },
            }
        )
        if len(rows) >= limit:
            break
    return rows


def price_on_or_before(company: Company, ticker: str, price_date):
    return (
        MarketPrice.objects.filter(company=company, price_date__lte=price_date)
        .filter(ticker_query(ticker))
        .order_by("-price_date")
        .first()
    )


def price_on_or_after(company: Company, ticker: str, price_date):
    return (
        MarketPrice.objects.filter(company=company, price_date__gte=price_date)
        .filter(ticker_query(ticker))
        .order_by("price_date")
        .first()
    )


def ticker_query(ticker: str) -> Q:
    normalized = ticker.strip().lower()
    stooq = normalized if "." in normalized else f"{normalized}.us"
    return Q(ticker__iexact=ticker) | Q(ticker__iexact=stooq)


def financial_snapshot(company: Company) -> list[dict[str, object]]:
    wanted = (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "OperatingIncomeLoss",
        "NetIncomeLoss",
        "Assets",
        "Liabilities",
        "LongTermDebt",
        "LongTermDebtAndFinanceLeaseObligations",
        "NetCashProvidedByUsedInOperatingActivities",
        "PaymentsToAcquirePropertyPlantAndEquipment",
    )
    rows = []
    for concept in wanted:
        fact = (
            FinancialFact.objects.filter(company=company, concept=concept)
            .order_by("-fy", "-filed", "-id")
            .first()
        )
        if not fact:
            continue
        rows.append(serialize_financial_fact(fact))
    return rows


def serialize_financial_fact(fact: FinancialFact) -> dict[str, object]:
    return {
        "id": fact.id,
        "concept": fact.concept,
        "label": fact.label,
        "unit": fact.unit,
        "fy": fact.fy,
        "fp": fact.fp,
        "filed": fact.filed.isoformat() if fact.filed else None,
        "frame": fact.frame,
        "value": decimal_to_float(fact.value),
    }


def impact_reasons(windows: list[dict], facts: list[dict]) -> list[str]:
    reasons = []
    if windows:
        reasons.append("market_price_window_available")
    if facts:
        reasons.append("sec_companyfacts_available")
    return reasons


def pct_change(start, end) -> float | None:
    start_float = float(start or 0)
    if not start_float:
        return None
    return round(((float(end or 0) - start_float) / start_float) * 100, 3)


def ticker_for_company(company: Company) -> str:
    aliases = [str(alias).strip().upper() for alias in (company.aliases or []) if str(alias).strip()]
    for alias in aliases:
        if 1 <= len(alias) <= 8 and " " not in alias:
            return alias
    return ""


def max_date_iso(value) -> str | None:
    return value.isoformat() if value else None


def scorecard_candidate_rows(limit: int) -> list[dict[str, object]]:
    source_counts = dict(
        StrategicTurnSource.objects.values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    rows = []
    for turn in StrategicTurn.objects.select_related("company").order_by("-confidence_score", "-start_date")[:500]:
        source_count = source_counts.get(turn.id, 0)
        if not turn_eligibility(turn, source_count=source_count).eligible:
            continue
        linked_event = first_turn_event(turn)
        impact_rows = market_impact_rows([linked_event], 1) if linked_event else []
        impact = impact_rows[0] if impact_rows else None
        rows.append(
            {
                "id": turn.id,
                "company": turn.company.name,
                "company_slug": turn.company.slug,
                "title": turn.title,
                "turn_type": turn.turn_type,
                "start_date": turn.start_date.isoformat() if turn.start_date else None,
                "source_count": source_count,
                "confidence_score": decimal_to_float(turn.confidence_score),
                "review_status": turn.review_status,
                "score_status": "evidence-backed" if source_count > 0 else "source gap",
                "score_reason": scorecard_reason(impact),
                "market_reaction": impact.get("windows", []) if impact else [],
                "financial_facts": impact.get("financial_facts", []) if impact else [],
            }
        )
    first_by_company = {}
    additional_rows = []
    for row in rows:
        if row["company_slug"] not in first_by_company:
            first_by_company[row["company_slug"]] = row
        else:
            additional_rows.append(row)
    return [*first_by_company.values(), *additional_rows][:limit]


def first_turn_event(turn: StrategicTurn) -> BusinessEvent | None:
    link = (
        StrategicTurnSource.objects.select_related("business_event", "source_document")
        .filter(strategic_turn=turn, business_event__isnull=False)
        .order_by("id")
        .first()
    )
    return link.business_event if link else None


def scorecard_reason(impact: dict[str, object] | None) -> str:
    if not impact:
        return "Uses turn confidence and linked sources. Market/financial impact unavailable for this event window."
    windows = impact.get("windows") or []
    facts = impact.get("financial_facts") or []
    if windows and facts:
        return "Uses linked sources, event-window market returns, and SEC companyfacts."
    if windows:
        return "Uses linked sources and event-window market returns; SEC companyfacts are unavailable for this company."
    if facts:
        return "Uses linked sources and SEC companyfacts; market windows are unavailable for this event."
    return "Uses turn confidence and linked sources. Impact dimensions are incomplete."


def compare_turn_rows(limit: int) -> list[dict[str, object]]:
    source_counts = dict(
        StrategicTurnSource.objects.values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    grouped: dict[str, list[StrategicTurn]] = defaultdict(list)
    for turn in StrategicTurn.objects.select_related("company").order_by("-start_date", "company__name"):
        if turn_eligibility(turn, source_count=source_counts.get(turn.id, 0)).eligible:
            grouped[turn.turn_type].append(turn)

    rows = []
    for turn_type, eligible_turns in grouped.items():
        company_count = len({turn.company_id for turn in eligible_turns})
        if len(eligible_turns) < 2 or company_count < 2:
            continue
        rows.append(
            {
                "turn_type": turn_type,
                "sample_size": len(eligible_turns),
                "company_count": company_count,
                "turns": [
                    {
                        "id": turn.id,
                        "company": turn.company.name,
                        "company_slug": turn.company.slug,
                        "title": turn.title,
                        "turn_type": turn.turn_type,
                        "start_date": turn.start_date.isoformat() if turn.start_date else None,
                    }
                    for turn in eligible_turns[:12]
                ],
            }
        )
    return sorted(rows, key=lambda row: (-row["company_count"], -row["sample_size"], row["turn_type"]))[:limit]


def serialize_risk_signal(event: BusinessEvent) -> dict[str, object]:
    row = serialize_business_event(event)
    row["signal"] = event.event_type
    row["calculation_method"] = "Source-backed event type from curated business events."
    row["confidence_score"] = decimal_to_float(event.confidence_score)
    return row


def serialize_company_situation(company: Company, anchor: Company | None = None) -> dict[str, object]:
    match_dimensions = [value for value in [company.industry, company.country] if value]
    if anchor:
        match_dimensions = [
            value
            for value, matches in (
                (company.industry, company.industry and company.industry == anchor.industry),
                (company.country, company.country and company.country == anchor.country),
            )
            if matches
        ]
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "sector": company.industry,
        "country": company.country,
        "source_count": company.source_count,
        "event_count": company.event_count,
        "strategic_turn_count": company.turn_count,
        "match_dimensions": match_dimensions,
    }


def serialize_dashboard_scope(company: Company | None) -> dict[str, object] | None:
    if company is None:
        return None
    return {
        "company": company.name,
        "company_slug": company.slug,
        "sector": company.industry,
        "country": company.country,
    }


def dashboard_source_gaps(
    pattern_rows: list[dict],
    risk_events: list[BusinessEvent],
    compare_rows: list[dict],
    impact_rows: list[dict],
) -> list[dict[str, str]]:
    gaps = []
    if not pattern_rows:
        gaps.append(
            source_gap(
                "patterns",
                "No eligible strategic patterns can be built until specific source-backed turns exist.",
                dashboard="patterns",
                provider="turn_rebuild",
                next_action="Rebuild strategic turns from eligible event clusters and assign pattern labels.",
            )
        )
    if not risk_events:
        gaps.append(
            source_gap(
                "risk_signals",
                "No eligible source-backed risk event types were found.",
                dashboard="risk_signals",
                provider="event_extraction",
                next_action="Run risk event extraction and keep generic 10-K risk text as candidate-only.",
            )
        )
    if not compare_rows:
        gaps.append(
            source_gap(
                "compare_turns",
                "At least two eligible specific turns of the same comparable type are required.",
                dashboard="compare",
                provider="turn_rebuild",
                next_action="Rebuild eligible turns and assign comparable pattern/type labels.",
            )
        )
    if MarketPrice.objects.count() == 0:
        gaps.append(
            source_gap(
                "market_prices",
                "Market reaction dashboards need daily price and benchmark ingestion.",
                dashboard="turn_impact",
                provider="stooq",
                next_action="Run Stooq OHLCV ingestion for the company universe and benchmark ETFs.",
            )
        )
    if FinancialFact.objects.count() == 0:
        gaps.append(
            source_gap(
                "financial_facts",
                "Financial impact dashboards need SEC companyfacts ingestion.",
                dashboard="turn_impact",
                provider="sec_companyfacts",
                next_action="Run SEC companyfacts ingestion and build before/after financial windows.",
            )
        )
    if MarketPrice.objects.exists() and FinancialFact.objects.exists() and not impact_rows:
        gaps.append(
            source_gap(
                "impact_windows",
                "Prices and financial facts exist, but no eligible event has enough aligned window data yet.",
                dashboard="turn_impact",
                provider="impact_builder",
                next_action="Backfill price ranges around eligible event dates and verify company ticker aliases.",
            )
        )
    return gaps


def source_gap(key: str, reason: str, *, dashboard: str, provider: str, next_action: str) -> dict[str, str]:
    return {
        "key": key,
        "dashboard": dashboard,
        "reason": reason,
        "source": provider,
        "next_action": next_action,
    }


def persist_source_gaps(gaps: list[dict[str, str]]) -> None:
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=None,
            dashboard=gap.get("dashboard") or "dashboard",
            gap_type=gap["key"],
            provider=gap.get("source", ""),
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap.get("next_action", ""),
                "status": "OPEN",
                "metadata": {"source": "dashboard-data"},
            },
        )


def confidence_status(sample_size: int, avg_confidence) -> str:
    if sample_size < 5:
        return "low sample"
    if decimal_to_float(avg_confidence) < 0.5:
        return "needs review"
    return "reviewable"


def decimal_to_float(value) -> float:
    return round(float(value or 0), 3)


def decimal_to_float_or_none(value) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def serialize_company(company: Company) -> dict[str, object]:
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "sector": company.industry,
        "country": company.country,
        "wikidata_id": company.wikidata_id,
        "sec_cik": company.sec_cik,
        "source_count": getattr(company, "source_count", 0),
        "event_count": getattr(company, "event_count", 0),
        "strategic_turn_count": getattr(company, "turn_count", 0),
    }


def serialize_company_detail(company: Company) -> dict[str, object]:
    payload = serialize_company(company)
    payload.update(
        {
            "aliases": company.aliases if isinstance(company.aliases, list) else [],
            "website": company.website,
            "founded_date": company.founded_date.isoformat() if company.founded_date else None,
            "description": company.description,
            "is_active": company.is_active,
        }
    )
    return payload


def profile_section_values(
    company: Company,
    snapshot: CompanyProfileSnapshot | None,
    business_model_snapshot: BusinessModelSnapshot | None = None,
) -> dict[str, object]:
    return {
        "summary": snapshot.summary if snapshot and snapshot.summary else company.description,
        "business_model": business_model_snapshot.summary if business_model_snapshot else (snapshot.business_model if snapshot else ""),
        "subsidiaries": snapshot.subsidiaries if snapshot else [],
        "brands": snapshot.brands if snapshot else [],
        "segments": snapshot.segments if snapshot else [],
        "products": snapshot.products if snapshot else [],
        "customer_groups": snapshot.customer_groups if snapshot else [],
        "revenue_sources": snapshot.revenue_sources if snapshot else [],
        "geographies": snapshot.geographies if snapshot and snapshot.geographies else ([company.country] if company.country else []),
        "leadership": snapshot.leadership if snapshot else [],
        "competitors": snapshot.competitors if snapshot else [],
        "strategic_priorities": snapshot.strategic_priorities if snapshot else [],
    }


def profile_section_values_from_snapshots(
    company: Company,
    snapshots: list[CompanyProfileSnapshot],
    business_model_snapshot: BusinessModelSnapshot | None = None,
) -> dict[str, object]:
    values = profile_section_values(company, None, business_model_snapshot)
    for field in values:
        if field == "business_model" and business_model_snapshot:
            continue
        for snapshot in snapshots:
            value = getattr(snapshot, field)
            if value:
                values[field] = value
                break
    return values


def serialize_profile_snapshot(snapshot: CompanyProfileSnapshot | None, sections: dict[str, object]) -> dict[str, object] | None:
    if snapshot is None:
        return None
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "evidence_text": snapshot.evidence_text,
        "source_id": snapshot.source_document_id,
        "sections": sections,
    }


def profile_changes(current: CompanyProfileSnapshot | None, previous: CompanyProfileSnapshot | None) -> list[dict[str, object]]:
    if current is None or previous is None:
        return []
    fields = (
        "summary",
        "business_model",
        "subsidiaries",
        "brands",
        "segments",
        "products",
        "customer_groups",
        "revenue_sources",
        "geographies",
        "leadership",
        "competitors",
        "strategic_priorities",
    )
    return [
        {
            "section": field,
            "previous_effective_date": previous.effective_date.isoformat(),
            "current_effective_date": current.effective_date.isoformat(),
            "previous": getattr(previous, field),
            "current": getattr(current, field),
        }
        for field in fields
        if getattr(previous, field) != getattr(current, field)
    ]


def profile_value_changes(
    current: dict[str, object],
    previous: dict[str, object] | None,
    current_date: date | None,
    previous_date: date | None,
) -> list[dict[str, object]]:
    if previous is None or current_date is None or previous_date is None:
        return []
    return [
        {
            "section": field,
            "previous_effective_date": previous_date.isoformat(),
            "current_effective_date": current_date.isoformat(),
            "previous": previous.get(field),
            "current": value,
        }
        for field, value in current.items()
        if previous.get(field) != value
    ]


def profile_conflicts(current: CompanyProfileSnapshot | None, snapshots: list[CompanyProfileSnapshot]) -> list[dict[str, object]]:
    if current is None:
        return []
    peers = [row for row in snapshots if row.id != current.id and row.effective_date == current.effective_date]
    conflicts = []
    for peer in peers:
        differing = [
            field
            for field in ("summary", "business_model", "subsidiaries", "brands", "segments", "products", "customer_groups", "revenue_sources", "geographies", "leadership", "competitors", "strategic_priorities")
            if getattr(peer, field) and getattr(current, field) and getattr(peer, field) != getattr(current, field)
        ]
        if differing:
            conflicts.append(
                {
                    "snapshot_id": peer.id,
                    "effective_date": peer.effective_date.isoformat(),
                    "differing_sections": differing,
                    "source_id": peer.source_document_id,
                    "status": "needs_review",
                }
            )
    return conflicts


def serialize_profile_source(source: SourceDocument) -> dict[str, object]:
    return {
        "id": source.id,
        "source_api": source.source_api,
        "title": source.title,
        "publisher": source.publisher,
        "url": source.canonical_url or source.url,
        "published_date": source.published_date.isoformat() if source.published_date else None,
        "snippet": source.snippet,
        "status": source.status,
        "updated_at": source.updated_at.isoformat(),
    }


def persist_company_profile_gaps(company: Company, gaps: list[dict[str, str]], sections: dict[str, object]) -> None:
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="company_profile",
            gap_type=gap["key"],
            provider="company-profile",
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap["next_action"],
                "status": "OPEN",
                "metadata": {"section": gap["key"].removeprefix("company_profile_")},
            },
        )
    available_keys = {f"company_profile_{key}" for key, value in sections.items() if value}
    SourceGap.objects.filter(
        company=company,
        dashboard="company_profile",
        gap_type__in=available_keys,
        status__in=["OPEN", "IN_PROGRESS"],
    ).update(status="RESOLVED")


def serialize_kpi_definition(kpi: KpiDefinition | None) -> dict[str, object] | None:
    if kpi is None:
        return None
    versions = list(kpi.definition_versions.all())
    return {
        "id": kpi.id, "slug": kpi.slug, "name": kpi.name, "description": kpi.description,
        "unit": kpi.unit, "cadence": kpi.cadence, "value_type": kpi.value_type, "scope": kpi.scope,
        "aliases": kpi.aliases if isinstance(kpi.aliases, list) else [], "formula": kpi.formula,
        "peer_comparable": kpi.peer_comparable,
        "definition_history": [{
            "effective_date": row.effective_date.isoformat(), "definition": row.definition,
            "scope": row.scope, "change_note": row.change_note, "source_id": row.source_document_id,
        } for row in versions],
        "targets": [{"target_date": row.target_date.isoformat(), "target_value": decimal_to_float(row.target_value), "condition": row.condition, "status": row.status} for row in kpi.targets.all()],
    }


def serialize_management_promise(promise: ManagementPromise | None, *, include_updates: bool) -> dict[str, object] | None:
    if promise is None:
        return None
    payload = {
        "id": promise.id,
        "slug": promise.slug,
        "title": promise.title,
        "promise_type": promise.promise_type,
        "original_statement": promise.original_statement,
        "speaker": promise.speaker,
        "speaker_role": promise.speaker_role,
        "statement_date": promise.statement_date.isoformat(),
        "target_start_date": promise.target_start_date.isoformat() if promise.target_start_date else None,
        "target_end_date": promise.target_end_date.isoformat() if promise.target_end_date else None,
        "metric_name": promise.metric_name,
        "baseline_value": decimal_to_float(promise.baseline_value) if promise.baseline_value is not None else None,
        "target_value": decimal_to_float(promise.target_value) if promise.target_value is not None else None,
        "unit": promise.unit,
        "scope": promise.scope,
        "conditions": promise.conditions,
        "evaluation_rule": promise.evaluation_rule,
        "current_status": promise.current_status,
        "confidence_score": decimal_to_float(promise.confidence_score),
        "review_status": promise.review_status,
        "evidence_text": promise.evidence_text,
        "source": serialize_profile_source(promise.source_document) if promise.source_document else None,
        "linked_kpi": {"slug": promise.linked_kpi.slug, "name": promise.linked_kpi.name} if promise.linked_kpi else None,
        "linked_strategic_turn": {
            "id": promise.linked_strategic_turn.id,
            "title": promise.linked_strategic_turn.title,
        } if promise.linked_strategic_turn else None,
    }
    payload["updates"] = [
        {
            "id": row.id,
            "update_date": row.update_date.isoformat(),
            "status": row.status,
            "summary": row.summary,
            "previous_target_end_date": row.previous_target_end_date.isoformat() if row.previous_target_end_date else None,
            "revised_target_end_date": row.revised_target_end_date.isoformat() if row.revised_target_end_date else None,
            "evidence_text": row.evidence_text,
            "is_contradiction_candidate": row.is_contradiction_candidate,
            "contradiction_note": row.contradiction_note,
            "confidence_score": decimal_to_float(row.confidence_score),
            "review_status": row.review_status,
            "source": serialize_profile_source(row.source_document) if row.source_document else None,
        }
        for row in promise.updates.all()
        if row.review_status == "REVIEWED"
    ] if include_updates else []
    return payload


def serialize_strategy_milestone(milestone: StrategyMilestone | None, *, include_history: bool) -> dict[str, object] | None:
    if milestone is None:
        return None
    payload = {
        "id": milestone.id,
        "slug": milestone.slug,
        "title": milestone.title,
        "milestone_type": milestone.milestone_type,
        "origin": milestone.origin,
        "current_status": milestone.current_status,
        "expected_start_date": milestone.expected_start_date.isoformat() if milestone.expected_start_date else None,
        "expected_end_date": milestone.expected_end_date.isoformat() if milestone.expected_end_date else None,
        "date_precision": milestone.date_precision,
        "owner": milestone.owner,
        "success_condition": milestone.success_condition,
        "blocker": milestone.blocker,
        "outcome_review": milestone.outcome_review,
        "evidence_text": milestone.evidence_text,
        "confidence_score": decimal_to_float(milestone.confidence_score),
        "review_status": milestone.review_status,
        "source": serialize_profile_source(milestone.source_document),
        "linked_promise": {"slug": milestone.linked_promise.slug, "title": milestone.linked_promise.title} if milestone.linked_promise else None,
        "linked_kpi": {"slug": milestone.linked_kpi.slug, "name": milestone.linked_kpi.name} if milestone.linked_kpi else None,
        "linked_strategic_turn": {"id": milestone.linked_strategic_turn.id, "title": milestone.linked_strategic_turn.title} if milestone.linked_strategic_turn else None,
        "related_entities": milestone.related_entities if isinstance(milestone.related_entities, list) else [],
        "dependencies": [
            {"slug": row.depends_on.slug, "title": row.depends_on.title, "relationship": row.relationship, "description": row.description}
            for row in milestone.dependencies.all()
        ],
    }
    payload["status_history"] = [
        {
            "status_date": row.status_date.isoformat(),
            "status": row.status,
            "summary": row.summary,
            "blocker": row.blocker,
            "evidence_text": row.evidence_text,
            "confidence_score": decimal_to_float(row.confidence_score),
            "source": serialize_profile_source(row.source_document),
        }
        for row in milestone.status_updates.all()
        if row.review_status == "REVIEWED"
    ] if include_history else []
    return payload


def persist_management_promise_gaps(company: Company, gaps: list[dict[str, str]]) -> None:
    if gaps:
        gap = gaps[0]
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="management_promises",
            gap_type=gap["key"],
            provider="management-promise-tracker",
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap["next_action"],
                "status": "OPEN",
            },
        )
    else:
        SourceGap.objects.filter(
            company=company,
            dashboard="management_promises",
            gap_type="management_promises",
            status__in=["OPEN", "IN_PROGRESS"],
        ).update(status="RESOLVED")


def persist_strategy_milestone_gaps(company: Company, gaps: list[dict[str, str]]) -> None:
    if gaps:
        gap = gaps[0]
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="strategy_milestones",
            gap_type=gap["key"],
            provider="strategy-milestone-tracker",
            defaults={"reason": gap["reason"], "next_ingestion_task": gap["next_action"], "status": "OPEN"},
        )
    else:
        SourceGap.objects.filter(
            company=company,
            dashboard="strategy_milestones",
            gap_type="strategy_milestones",
            status__in=["OPEN", "IN_PROGRESS"],
        ).update(status="RESOLVED")


def persist_capital_allocation_gaps(company: Company, gaps: list[dict[str, str]]) -> None:
    active_keys = [gap["key"] for gap in gaps]
    if active_keys:
        SourceGap.objects.filter(company=company, dashboard="capital_allocation").exclude(
            gap_type__in=active_keys
        ).update(status="RESOLVED")
    else:
        SourceGap.objects.filter(
            company=company,
            dashboard="capital_allocation",
            status__in=["OPEN", "IN_PROGRESS"],
        ).update(status="RESOLVED")
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="capital_allocation",
            gap_type=gap["key"],
            provider=gap.get("source", "capital-allocation-dashboard"),
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap.get("next_action", ""),
                "status": "OPEN",
                "metadata": {"label": gap.get("label", "")},
            },
        )


def persist_competitive_position_gaps(company: Company, gaps: list[dict[str, str]]) -> None:
    active_keys = [gap["key"] for gap in gaps]
    if active_keys:
        SourceGap.objects.filter(company=company, dashboard="competitive_position").exclude(
            gap_type__in=active_keys
        ).update(status="RESOLVED")
    else:
        SourceGap.objects.filter(
            company=company,
            dashboard="competitive_position",
            status__in=["OPEN", "IN_PROGRESS"],
        ).update(status="RESOLVED")
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="competitive_position",
            gap_type=gap["key"],
            provider=gap.get("source", "competitive-position"),
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap.get("next_action", ""),
                "status": "OPEN",
                "metadata": {"label": gap.get("label", "")},
            },
        )


def persist_product_pricing_gaps(company: Company, gaps: list[dict[str, str]]) -> None:
    active_keys = [gap["key"] for gap in gaps]
    if active_keys:
        SourceGap.objects.filter(company=company, dashboard="product_pricing_history").exclude(
            gap_type__in=active_keys
        ).update(status="RESOLVED")
    else:
        SourceGap.objects.filter(
            company=company,
            dashboard="product_pricing_history",
            status__in=["OPEN", "IN_PROGRESS"],
        ).update(status="RESOLVED")
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="product_pricing_history",
            gap_type=gap["key"],
            provider=gap.get("source", "product-pricing-history"),
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap.get("next_action", ""),
                "status": "OPEN",
                "metadata": {"label": gap.get("label", "")},
            },
        )


def persist_acquisition_lifecycle_gaps(company: Company, gaps: list[dict[str, str]]) -> None:
    active_keys = [gap["key"] for gap in gaps]
    if active_keys:
        SourceGap.objects.filter(company=company, dashboard="acquisition_lifecycle").exclude(
            gap_type__in=active_keys
        ).update(status="RESOLVED")
    else:
        SourceGap.objects.filter(
            company=company,
            dashboard="acquisition_lifecycle",
            status__in=["OPEN", "IN_PROGRESS"],
        ).update(status="RESOLVED")
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="acquisition_lifecycle",
            gap_type=gap["key"],
            provider=gap.get("source", "acquisition-lifecycle"),
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap.get("next_action", ""),
                "status": "OPEN",
                "metadata": {"label": gap.get("label", "")},
            },
        )


def persist_customer_supplier_dependency_gaps(company: Company, gaps: list[dict[str, str]]) -> None:
    active_keys = [gap["key"] for gap in gaps]
    if active_keys:
        SourceGap.objects.filter(company=company, dashboard="customer_supplier_dependency").exclude(
            gap_type__in=active_keys
        ).update(status="RESOLVED")
    else:
        SourceGap.objects.filter(
            company=company,
            dashboard="customer_supplier_dependency",
            status__in=["OPEN", "IN_PROGRESS"],
        ).update(status="RESOLVED")
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="customer_supplier_dependency",
            gap_type=gap["key"],
            provider=gap.get("source", "customer-supplier-dependency"),
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap.get("next_action", ""),
                "status": "OPEN",
                "metadata": {"label": gap.get("label", "")},
            },
        )


def serialize_kpi_observation(row: KpiObservation) -> dict[str, object]:
    return {
        "id": row.id, "period_start": row.period_start.isoformat(), "period_end": row.period_end.isoformat(),
        "fiscal_year": row.fiscal_year, "fiscal_period": row.fiscal_period, "value": decimal_to_float(row.value),
        "segment": row.segment, "geography": row.geography, "evidence_text": row.evidence_text,
        "source_id": row.source_document_id, "is_estimated": row.is_estimated, "is_restatement": row.is_restatement,
        "is_non_comparable": row.is_non_comparable, "definition_changed": row.definition_changed,
        "confidence_score": decimal_to_float(row.confidence_score),
    }


def serialize_kpi_export_row(row: KpiObservation) -> dict[str, object]:
    payload = serialize_kpi_observation(row)
    payload.update({"metric": row.kpi.name, "metric_slug": row.kpi.slug, "unit": row.kpi.unit, "value_type": row.kpi.value_type})
    return payload


def missing_kpi_periods(kpi: KpiDefinition | None, observations: list[KpiObservation]) -> list[str]:
    if kpi is None or kpi.cadence != "QUARTERLY":
        return []
    global_rows = sorted({row.period_end for row in observations if not row.geography})
    if len(global_rows) < 2:
        return []
    observed = set(global_rows)
    cursor = global_rows[0]
    missing = []
    while cursor < global_rows[-1]:
        next_month = cursor.month + 3
        next_year = cursor.year + (1 if next_month > 12 else 0)
        next_month = next_month - 12 if next_month > 12 else next_month
        month_end = {3: 31, 6: 30, 9: 30, 12: 31}[next_month]
        cursor = date(next_year, next_month, month_end)
        if cursor not in observed:
            missing.append(cursor.isoformat())
    return missing


def kpi_alerts(kpi: KpiDefinition | None, observations: list[KpiObservation]) -> list[dict[str, object]]:
    if kpi is None:
        return []
    rows = [row for row in observations if not row.geography and not row.is_non_comparable]
    alerts = []
    for previous, current in zip(rows, rows[1:]):
        previous_value = float(previous.value)
        if previous_value == 0:
            continue
        change = ((float(current.value) / previous_value) - 1) * 100
        if abs(change) >= 1:
            alerts.append({
                "period_end": current.period_end.isoformat(), "type": "ACCELERATION" if change > 0 else "SLOWDOWN",
                "change_percent": round(change, 2),
                "message": f"{kpi.name} {'increased' if change > 0 else 'decreased'} {abs(change):.2f}% from the prior period.",
            })
    if not kpi.is_active:
        alerts.append({"period_end": None, "type": "DISCLOSURE_DISCONTINUED", "change_percent": None, "message": f"{kpi.name} is no longer disclosed."})
    latest = rows[-1] if rows else None
    for target in kpi.targets.all():
        if latest and latest.period_end <= target.target_date and latest.value >= target.target_value:
            alerts.append({
                "period_end": latest.period_end.isoformat(), "type": "TARGET_CROSSED", "change_percent": None,
                "message": f"{kpi.name} crossed the {decimal_to_float(target.target_value)} target due {target.target_date.isoformat()}.",
            })
    return alerts


def peer_kpi_rows(company: Company, kpi: KpiDefinition | None) -> list[dict[str, object]]:
    if kpi is None or not kpi.peer_comparable or not company.industry:
        return []
    peers = KpiDefinition.objects.filter(company__industry=company.industry, peer_comparable=True, slug=kpi.slug).exclude(company=company).select_related("company")
    return [{"company": row.company.name, "company_slug": row.company.slug, "metric": row.name, "unit": row.unit, "comparable": True} for row in peers]


def persist_operating_kpi_gaps(company: Company, gaps: list[dict[str, str]], has_definitions: bool, has_observations: bool) -> None:
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company, dashboard="operating_kpis", gap_type=gap["key"], provider="operating-kpi-tracker",
            defaults={"reason": gap["reason"], "next_ingestion_task": gap["next_action"], "status": "OPEN", "metadata": {}},
        )
    resolved = []
    if has_definitions:
        resolved.append("operating_kpis")
    if has_observations:
        resolved.extend(SourceGap.objects.filter(company=company, dashboard="operating_kpis", gap_type__endswith="_series").values_list("gap_type", flat=True))
    SourceGap.objects.filter(company=company, dashboard="operating_kpis", gap_type__in=resolved, status__in=["OPEN", "IN_PROGRESS"]).update(status="RESOLVED")


def serialize_business_model_snapshot(snapshot: BusinessModelSnapshot | None) -> dict[str, object] | None:
    if snapshot is None:
        return None
    components = list(snapshot.components.all())
    grouped = {
        component_type: [serialize_business_model_component(row) for row in components if row.component_type == component_type]
        for component_type, _label in BusinessModelComponentType.choices
    }
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "summary": snapshot.summary,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "source_id": snapshot.source_document_id,
        "components": [serialize_business_model_component(row) for row in components],
        "component_groups": grouped,
        "relationships": [
            {
                "id": row.id,
                "from_component_id": row.from_component_id,
                "from_name": row.from_component.name,
                "to_component_id": row.to_component_id,
                "to_name": row.to_component.name,
                "relationship_type": row.relationship_type,
                "description": row.description,
                "evidence_text": row.evidence_text,
                "is_inferred": row.is_inferred,
                "confidence_score": decimal_to_float(row.confidence_score),
            }
            for row in snapshot.relationships.all()
        ],
    }


def serialize_business_model_component(component) -> dict[str, object]:
    return {
        "id": component.id,
        "component_type": component.component_type,
        "component_type_label": component.get_component_type_display(),
        "name": component.name,
        "description": component.description,
        "scope": component.scope,
        "evidence_text": component.evidence_text,
        "is_inferred": component.is_inferred,
        "confidence_score": decimal_to_float(component.confidence_score),
    }


def serialize_business_model_history(snapshot: BusinessModelSnapshot, selected: BusinessModelSnapshot | None) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "effective_date": snapshot.effective_date.isoformat(),
        "status": snapshot.status,
        "summary": snapshot.summary,
        "confidence_score": decimal_to_float(snapshot.confidence_score),
        "component_count": snapshot.components.count(),
        "relationship_count": snapshot.relationships.count(),
        "selected": bool(selected and selected.id == snapshot.id),
    }


def business_model_changes(current: BusinessModelSnapshot | None, comparison: BusinessModelSnapshot | None) -> dict[str, object]:
    if current is None or comparison is None or current.id == comparison.id:
        return {"from_date": None, "to_date": current.effective_date.isoformat() if current else None, "components_added": [], "components_removed": [], "relationships_added": [], "relationships_removed": []}
    current_components = {(row.component_type, row.name) for row in current.components.all()}
    comparison_components = {(row.component_type, row.name) for row in comparison.components.all()}
    current_relationships = {(row.from_component.name, row.relationship_type, row.to_component.name) for row in current.relationships.all()}
    comparison_relationships = {(row.from_component.name, row.relationship_type, row.to_component.name) for row in comparison.relationships.all()}
    return {
        "from_date": comparison.effective_date.isoformat(),
        "to_date": current.effective_date.isoformat(),
        "components_added": [{"component_type": row[0], "name": row[1]} for row in sorted(current_components - comparison_components)],
        "components_removed": [{"component_type": row[0], "name": row[1]} for row in sorted(comparison_components - current_components)],
        "relationships_added": [{"from_name": row[0], "relationship_type": row[1], "to_name": row[2]} for row in sorted(current_relationships - comparison_relationships)],
        "relationships_removed": [{"from_name": row[0], "relationship_type": row[1], "to_name": row[2]} for row in sorted(comparison_relationships - current_relationships)],
    }


def persist_business_model_gaps(company: Company, gaps: list[dict[str, str]], present_types: set[str], has_relationships: bool) -> None:
    for gap in gaps:
        SourceGap.objects.update_or_create(
            company=company,
            dashboard="business_model",
            gap_type=gap["key"],
            provider="business-model-map",
            defaults={
                "reason": gap["reason"],
                "next_ingestion_task": gap["next_action"],
                "status": "OPEN",
                "metadata": {},
            },
        )
    resolved = {f"business_model_{component_type.lower()}" for component_type in present_types}
    if has_relationships:
        resolved.add("business_model_relationships")
    SourceGap.objects.filter(
        company=company,
        dashboard="business_model",
        gap_type__in=resolved,
        status__in=["OPEN", "IN_PROGRESS"],
    ).update(status="RESOLVED")


def peer_business_model_rows(company: Company, current: BusinessModelSnapshot | None) -> list[dict[str, object]]:
    if not company.industry:
        return []
    candidates = (
        BusinessModelSnapshot.objects.filter(
            company__industry=company.industry,
            status__in=["PUBLISHED", "REVIEWED"],
        )
        .exclude(company=company)
        .select_related("company")
        .prefetch_related("components")
        .order_by("company__name", "-effective_date")
    )
    latest_by_company = {}
    for snapshot in candidates:
        latest_by_company.setdefault(snapshot.company_id, snapshot)
    current_components = {(row.component_type, row.name.lower()) for row in current.components.all()} if current else set()
    rows = []
    for snapshot in latest_by_company.values():
        components = list(snapshot.components.all())
        peer_components = {(row.component_type, row.name.lower()) for row in components}
        shared = sorted(current_components & peer_components)
        rows.append(
            {
                "company": snapshot.company.name,
                "company_slug": snapshot.company.slug,
                "effective_date": snapshot.effective_date.isoformat(),
                "summary": snapshot.summary,
                "component_count": len(components),
                "shared_components": [{"component_type": item[0], "name": item[1]} for item in shared],
                "confidence_score": decimal_to_float(snapshot.confidence_score),
            }
        )
    return rows


def serialize_business_event(event: BusinessEvent) -> dict[str, object]:
    raw = event.raw_extraction_json or {}
    source_count = event_source_count(event)
    eligibility = event_eligibility(event)
    return {
        "id": event.id,
        "company": event.company.name,
        "company_slug": event.company.slug,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "event_type": event.event_type,
        "decision_theme": event.decision_theme,
        "actual_change": event.actual_change,
        "source_claim": event.source_claim,
        "first_filing": raw.get("first_observed_filing_date"),
        "latest_filing": raw.get("latest_observed_filing_date"),
        "source_count": source_count,
        "review_status": event.review_status,
        "confidence_score": decimal_to_float(event.confidence_score),
        "quality": {
            "eligible": eligibility.eligible,
            "status": eligibility.status,
            "score": eligibility.score,
            "reasons": list(eligibility.reasons),
        },
    }


def serialize_strategic_turn(turn: StrategicTurn, *, source_count: int) -> dict[str, object]:
    eligibility = turn_eligibility(turn, source_count=source_count)
    return {
        "id": turn.id,
        "title": turn.title,
        "turn_type": turn.turn_type,
        "start_date": turn.start_date.isoformat() if turn.start_date else None,
        "end_date": turn.end_date.isoformat() if turn.end_date else None,
        "summary": turn.summary,
        "decision": turn.decision,
        "outcome": turn.outcome,
        "review_status": turn.review_status,
        "is_published": turn.is_published,
        "source_count": source_count,
        "confidence_score": decimal_to_float(turn.confidence_score),
        "quality": {
            "eligible": eligibility.eligible,
            "status": eligibility.status,
            "score": eligibility.score,
            "reasons": list(eligibility.reasons),
        },
    }


def serialize_job(job: IngestionJob) -> dict[str, object]:
    return {
        "id": job.id,
        "company": job.company.name if job.company_id else None,
        "company_slug": job.company.slug if job.company_id else None,
        "job_type": job.job_type,
        "source": job.source,
        "status": job.status,
        "sources_found": job.sources_found,
        "sources_inserted": job.sources_inserted,
        "duplicates_skipped": job.duplicates_skipped,
        "articles_extracted": job.articles_extracted,
        "events_extracted": job.events_extracted,
        "turns_created": job.turns_created,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


def serialize_source_gap(gap: SourceGap) -> dict[str, object]:
    return {
        "id": gap.id,
        "company": gap.company.name if gap.company_id else None,
        "company_slug": gap.company.slug if gap.company_id else None,
        "dashboard": gap.dashboard,
        "gap_type": gap.gap_type,
        "provider": gap.provider,
        "reason": gap.reason,
        "next_ingestion_task": gap.next_ingestion_task,
        "status": gap.status,
        "metadata": gap.metadata,
        "created_at": gap.created_at.isoformat() if gap.created_at else None,
        "updated_at": gap.updated_at.isoformat() if gap.updated_at else None,
    }

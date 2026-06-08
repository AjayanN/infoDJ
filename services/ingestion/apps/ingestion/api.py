from __future__ import annotations

from datetime import date, timedelta

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.core.management import call_command
from django.db import connection
from django.db.models import Avg, Count, Max, Q
from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.companies.models import (
    BusinessModelComponentType,
    BusinessModelSnapshot,
    Company,
    CompanyProfileSnapshot,
    KpiDefinition,
    KpiObservation,
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


def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok", "service": "infodj-ingestion"})


@require_GET
def companies(_request: HttpRequest) -> JsonResponse:
    rows = []
    for company in Company.objects.annotate(
        source_count=Count("source_documents", distinct=True),
        event_count=Count("business_events", distinct=True),
        turn_count=Count("strategic_turns", distinct=True),
        kpi_count=Count("kpi_definitions", distinct=True),
    ).order_by("industry", "name"):
        rows.append(
            {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "sector": company.industry,
                "country": company.country,
                "wikidata_id": company.wikidata_id,
                "sec_cik": company.sec_cik,
                "source_count": company.source_count,
                "event_count": company.event_count,
                "strategic_turn_count": company.turn_count,
                "kpi_count": company.kpi_count,
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
    previous = eligible_snapshots[1] if len(eligible_snapshots) > 1 else None

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

    section_values = profile_section_values(company, current)
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
                key: {"status": "available" if value else "unavailable", "items": value if isinstance(value, list) else [], "text": value if isinstance(value, str) else ""}
                for key, value in section_values.items()
            },
            "highlights": {
                "latest_events": [serialize_business_event(event) for event in events],
                "latest_turns": [serialize_strategic_turn(turn, source_count=turn_source_counts.get(turn.id, 0)) for turn in turns],
                "financial_facts": [serialize_financial_fact(fact) for fact in facts],
            },
            "changes": profile_changes(current, previous),
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
def dashboard_data(request: HttpRequest) -> JsonResponse:
    limit = bounded_limit(request, default=10, maximum=50)
    requested_section = (request.GET.get("section") or "").strip()
    requested_page = bounded_page(request)

    def page_for(section: str) -> int:
        return requested_page if requested_section == section else 1

    latest_event_candidates = list(
        BusinessEvent.objects.select_related("company", "source_document")
        .exclude(actual_change="")
        .order_by("-event_date", "-created_at")[:500]
    )
    latest_events = eligible_events(latest_event_candidates, 500)
    impact_event_candidates = list(
        BusinessEvent.objects.select_related("company", "source_document")
        .filter(company_id__in=MarketPrice.objects.exclude(company_id__isnull=True).values("company_id"))
        .exclude(actual_change="")
        .order_by("-event_date", "-created_at")[:500]
    )
    impact_events = eligible_events(impact_event_candidates, 500)
    latest_turn_candidates = list(StrategicTurn.objects.select_related("company").order_by("-start_date", "-created_at")[:500])
    turn_source_counts = dict(
        StrategicTurnSource.objects.filter(strategic_turn__in=latest_turn_candidates)
        .values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )
    latest_turns = eligible_turns(latest_turn_candidates, turn_source_counts, 500)
    pattern_rows = strategic_pattern_rows(500)
    risk_event_candidates = list(
        BusinessEvent.objects.select_related("company", "source_document")
        .filter(event_type__in=RISK_EVENT_TYPES)
        .exclude(actual_change="")
        .order_by("-event_date", "-created_at")[:500]
    )
    risk_events = eligible_risk_events(risk_event_candidates, 500)
    company_rows = list(
        Company.objects.annotate(
            source_count=Count("source_documents", distinct=True),
            event_count=Count("business_events", distinct=True),
            turn_count=Count("strategic_turns", distinct=True),
        )
        .filter(event_count__gt=0)
        .order_by("-event_count", "name")[:500]
    )
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
            items=[serialize_company_situation(company) for company in company_rows_page],
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
            "latest_events": [serialize_business_event(event) for event in latest_events],
            "latest_turns": [serialize_strategic_turn(turn, source_count=turn_source_counts.get(turn.id, 0)) for turn in latest_turns],
            "patterns": pattern_rows,
            "risk_signals": [serialize_risk_signal(event) for event in risk_events],
            "turn_impact": impact_rows,
            "source_confidence": source_confidence_summary(),
            "scorecard_candidates": scorecard_rows,
            "company_situations": [serialize_company_situation(company) for company in company_rows],
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
        if len(rows) >= limit:
            break
    return rows


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
    rows = []
    for group in (
        StrategicTurn.objects.values("turn_type")
        .annotate(count=Count("id"))
        .filter(count__gte=2)
        .order_by("-count", "turn_type")[:limit]
    ):
        turns = []
        for turn in (
            StrategicTurn.objects.select_related("company")
            .filter(turn_type=group["turn_type"])
            .order_by("-start_date", "company__name")[:4]
        ):
            if turn_eligibility(turn, source_count=StrategicTurnSource.objects.filter(strategic_turn=turn).count()).eligible:
                turns.append(
                    {
                        "id": turn.id,
                        "company": turn.company.name,
                        "title": turn.title,
                        "start_date": turn.start_date.isoformat() if turn.start_date else None,
                    }
                )
        if len(turns) >= 2:
            rows.append({"turn_type": group["turn_type"], "sample_size": group["count"], "turns": turns})
    return rows


def serialize_risk_signal(event: BusinessEvent) -> dict[str, object]:
    row = serialize_business_event(event)
    row["signal"] = event.event_type
    row["calculation_method"] = "Source-backed event type from curated business events."
    row["confidence_score"] = decimal_to_float(event.confidence_score)
    return row


def serialize_company_situation(company: Company) -> dict[str, object]:
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "sector": company.industry,
        "country": company.country,
        "source_count": company.source_count,
        "event_count": company.event_count,
        "strategic_turn_count": company.turn_count,
        "match_dimensions": [value for value in [company.industry, company.country] if value],
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


def profile_section_values(company: Company, snapshot: CompanyProfileSnapshot | None) -> dict[str, object]:
    return {
        "summary": snapshot.summary if snapshot and snapshot.summary else company.description,
        "business_model": snapshot.business_model if snapshot else "",
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

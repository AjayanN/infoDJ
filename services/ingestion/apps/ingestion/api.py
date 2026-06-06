from __future__ import annotations

from datetime import timedelta

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.core.management import call_command
from django.db import connection
from django.db.models import Avg, Count, Max, Q
from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.companies.models import Company
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
            }
        )
    return JsonResponse({"companies": rows})


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

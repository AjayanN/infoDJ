from __future__ import annotations

from django.core.management import call_command
from django.db.models import Count
from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import IngestionJob, SourceDocument


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
    raw = request.GET.get("limit")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, min(value, maximum))


def serialize_company(company: Company) -> dict[str, object]:
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "sector": company.industry,
        "country": company.country,
        "wikidata_id": company.wikidata_id,
        "sec_cik": company.sec_cik,
    }


def serialize_business_event(event: BusinessEvent) -> dict[str, object]:
    raw = event.raw_extraction_json or {}
    source_count = len(raw.get("additional_source_ids") or []) + (1 if event.source_document_id else 0)
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
    }


def serialize_strategic_turn(turn: StrategicTurn, *, source_count: int) -> dict[str, object]:
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


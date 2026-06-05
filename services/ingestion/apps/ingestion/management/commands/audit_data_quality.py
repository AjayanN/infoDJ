from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Q

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import ArticleExtraction, FinancialFact, IngestionJob, MarketPrice, SourceDocument
from apps.ingestion.services.dashboard_quality import event_eligibility, risk_event_eligibility, turn_eligibility


GENERIC_EVENT_PHRASES = (
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


class Command(BaseCommand):
    help = "Audit InfoDJ ingestion data quality for dashboard readiness."

    def add_arguments(self, parser):
        parser.add_argument("--sample-size", type=int, default=8)

    def handle(self, *args, **options):
        sample_size = options["sample_size"]
        event_source_counts = event_source_count_distribution()
        turn_source_counts = turn_source_count_distribution()
        generic_turn_ids = generic_turn_id_set()

        self.section("Inventory")
        self.kv("companies", Company.objects.count())
        self.kv("source_documents", SourceDocument.objects.count())
        self.kv("article_extractions", ArticleExtraction.objects.count())
        self.kv("business_events", BusinessEvent.objects.count())
        self.kv("strategic_turns", StrategicTurn.objects.count())
        self.kv("strategic_turn_sources", StrategicTurnSource.objects.count())
        self.kv("market_prices", MarketPrice.objects.count())
        self.kv("financial_facts", FinancialFact.objects.count())
        self.kv("ingestion_jobs", IngestionJob.objects.count())

        self.section("Company Coverage")
        for row in company_coverage_rows(sample_size):
            self.row(row)

        self.section("Source Health")
        self.rows("source_api_counts", values_count(SourceDocument, "source_api"))
        self.rows("source_status_counts", values_count(SourceDocument, "status"))
        self.kv("source_documents_missing_published_date", SourceDocument.objects.filter(published_date__isnull=True).count())
        self.kv("source_documents_missing_language", SourceDocument.objects.filter(language="").count())
        self.kv("source_documents_marked_duplicate", SourceDocument.objects.filter(duplicate_of__isnull=False).count())
        self.rows("repeated_title_hashes", repeated_values(SourceDocument, "title_hash", sample_size, exclude_blank=True))

        self.section("Extraction Health")
        self.rows("article_extraction_status_counts", values_count(ArticleExtraction, "extraction_status"))
        self.kv("article_extractions_zero_words", ArticleExtraction.objects.filter(word_count=0).count())
        self.kv("article_extractions_with_error", ArticleExtraction.objects.exclude(extraction_error="").count())

        self.section("Business Event Validity")
        self.rows("event_type_counts", values_count(BusinessEvent, "event_type"))
        self.rows("event_review_status_counts", values_count(BusinessEvent, "review_status"))
        self.kv("events_missing_date", BusinessEvent.objects.filter(event_date__isnull=True).count())
        self.kv("events_missing_source_document", BusinessEvent.objects.filter(source_document__isnull=True).count())
        self.kv("events_zero_sources", event_source_counts.get(0, 0))
        self.kv("events_blank_actual_change", BusinessEvent.objects.filter(actual_change="").count())
        self.kv("events_blank_source_claim", BusinessEvent.objects.filter(source_claim="").count())
        self.kv("events_blank_evidence_text", BusinessEvent.objects.filter(evidence_text="").count())
        self.kv("events_zero_confidence", BusinessEvent.objects.filter(confidence_score=0).count())
        self.kv("events_low_confidence_lt_0_5", BusinessEvent.objects.filter(confidence_score__lt=0.5).count())
        self.kv("events_generic_rule_text", generic_event_queryset().count())
        self.rows("event_source_count_distribution", sorted_counter(event_source_counts))
        self.rows("duplicate_event_groups", duplicate_events(sample_size))
        self.rows("generic_event_samples", event_samples(generic_event_queryset(), sample_size))

        self.section("Strategic Turn Validity")
        self.rows("turn_type_counts", values_count(StrategicTurn, "turn_type"))
        self.rows("turn_review_status_counts", values_count(StrategicTurn, "review_status"))
        self.kv("turns_missing_start_date", StrategicTurn.objects.filter(start_date__isnull=True).count())
        self.kv("turns_zero_sources", turn_source_counts.get(0, 0))
        self.kv("turns_zero_confidence", StrategicTurn.objects.filter(confidence_score=0).count())
        self.kv("turns_low_confidence_lt_0_5", StrategicTurn.objects.filter(confidence_score__lt=0.5).count())
        self.kv("turns_generic_or_not_specific", len(generic_turn_ids))
        self.rows("turn_source_count_distribution", sorted_counter(turn_source_counts))
        self.rows("duplicate_turn_groups", duplicate_turns(sample_size))
        self.rows("generic_turn_samples", turn_samples(StrategicTurn.objects.filter(id__in=generic_turn_ids), sample_size))

        self.section("Ingestion Job Health")
        self.rows("job_status_counts", values_count(IngestionJob, "status"))
        self.rows("job_type_status_counts", job_type_status_counts())
        self.rows("failed_or_partial_jobs", failed_job_samples(sample_size))

        self.section("Dashboard Readiness")
        for row in dashboard_readiness_rows(event_source_counts, turn_source_counts, generic_turn_ids):
            self.row(row)

    def section(self, label: str):
        self.stdout.write(f"\n## {label}")

    def kv(self, key: str, value):
        self.stdout.write(f"{key}: {value}")

    def row(self, row: dict):
        self.stdout.write(" | ".join(f"{key}={value}" for key, value in row.items()))

    def rows(self, label: str, rows: list[dict]):
        self.stdout.write(f"{label}:")
        if not rows:
            self.stdout.write("  none")
            return
        for row in rows:
            self.stdout.write("  " + " | ".join(f"{key}={value}" for key, value in row.items()))


def values_count(model, field: str) -> list[dict]:
    return list(model.objects.values(field).annotate(count=Count("id")).order_by("-count", field))


def repeated_values(model, field: str, limit: int, *, exclude_blank: bool = False) -> list[dict]:
    qs = model.objects.values(field).annotate(count=Count("id")).filter(count__gt=1)
    if exclude_blank:
        qs = qs.exclude(**{field: ""})
    return list(qs.order_by("-count", field)[:limit])


def company_coverage_rows(limit: int) -> list[dict]:
    return list(
        Company.objects.annotate(
            sources=Count("source_documents", distinct=True),
            events=Count("business_events", distinct=True),
            turns=Count("strategic_turns", distinct=True),
        )
        .values("name", "industry", "sources", "events", "turns")
        .order_by("-events", "name")[:limit]
    )


def event_source_count_distribution() -> Counter:
    counts: Counter[int] = Counter()
    for event in BusinessEvent.objects.only("source_document_id", "raw_extraction_json"):
        raw = event.raw_extraction_json or {}
        count = len(raw.get("additional_source_ids") or []) + (1 if event.source_document_id else 0)
        counts[count] += 1
    return counts


def turn_source_count_distribution() -> Counter:
    linked = Counter(turn_source_counts_by_id())
    counts: Counter[int] = Counter()
    for turn_id in StrategicTurn.objects.values_list("id", flat=True):
        counts[linked.get(turn_id, 0)] += 1
    return counts


def turn_source_counts_by_id() -> dict[int, int]:
    return dict(
        StrategicTurnSource.objects.values("strategic_turn_id")
        .annotate(count=Count("id"))
        .values_list("strategic_turn_id", "count")
    )


def sorted_counter(counter: Counter) -> list[dict]:
    return [{"value": key, "count": counter[key]} for key in sorted(counter)]


def generic_event_queryset():
    query = Q()
    for phrase in GENERIC_EVENT_PHRASES:
        query |= Q(actual_change__icontains=phrase)
        query |= Q(outcome__icontains=phrase)
    return BusinessEvent.objects.filter(query)


def generic_turn_id_set() -> set[int]:
    ids: set[int] = set()
    source_counts = turn_source_counts_by_id()
    for turn in StrategicTurn.objects.all():
        if not turn_eligibility(turn, source_count=source_counts.get(turn.id, 0)).eligible:
            ids.add(turn.id)
    return ids


def duplicate_events(limit: int) -> list[dict]:
    return list(
        BusinessEvent.objects.values("company__name", "event_type", "event_date", "actual_change")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .order_by("-count", "company__name")[:limit]
    )


def duplicate_turns(limit: int) -> list[dict]:
    return list(
        StrategicTurn.objects.values("company__name", "turn_type", "start_date", "title")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .order_by("-count", "company__name")[:limit]
    )


def event_samples(queryset, limit: int) -> list[dict]:
    return list(
        queryset.select_related("company")
        .values("id", "company__name", "event_type", "event_date", "actual_change")[:limit]
    )


def turn_samples(queryset, limit: int) -> list[dict]:
    return list(
        queryset.select_related("company")
        .values("id", "company__name", "turn_type", "start_date", "title")[:limit]
    )


def job_type_status_counts() -> list[dict]:
    return list(
        IngestionJob.objects.values("job_type", "status")
        .annotate(count=Count("id"))
        .order_by("job_type", "status")
    )


def failed_job_samples(limit: int) -> list[dict]:
    return list(
        IngestionJob.objects.filter(Q(status="FAILED") | Q(status="PARTIAL") | ~Q(error_message=""))
        .select_related("company")
        .values("id", "company__name", "job_type", "source", "status", "error_message")
        .order_by("-created_at")[:limit]
    )


def dashboard_readiness_rows(event_source_counts: Counter, turn_source_counts: Counter, generic_turn_ids: set[int]) -> list[dict]:
    event_total = BusinessEvent.objects.count()
    turn_total = StrategicTurn.objects.count()
    source_total = SourceDocument.objects.count()
    dated_events = BusinessEvent.objects.filter(event_date__isnull=False).count()
    specific_turns = max(turn_total - len(generic_turn_ids), 0)
    source_backed_events = event_total - event_source_counts.get(0, 0)
    source_backed_turns = turn_total - turn_source_counts.get(0, 0)
    market_price_count = MarketPrice.objects.count()
    financial_fact_count = FinancialFact.objects.count()
    eligible_events = sum(
        1
        for event in BusinessEvent.objects.select_related("source_document")
        if event_eligibility(event).eligible
    )
    eligible_risk_events = sum(
        1
        for event in BusinessEvent.objects.select_related("source_document")
        if risk_event_eligibility(event).eligible
    )
    eligible_turn_type_counts = Counter(
        StrategicTurn.objects.exclude(id__in=generic_turn_ids).values_list("turn_type", flat=True)
    )
    comparable_eligible_turn_types = sum(1 for count in eligible_turn_type_counts.values() if count >= 2)
    return [
        readiness("Company Strategic Intelligence", event_total > 0 and source_total > 0, f"{event_total} events, {source_total} sources, {dated_events} dated events"),
        readiness(
            "Strategic Turn Impact",
            market_price_count > 0 and financial_fact_count > 0,
            f"{market_price_count} market prices, {financial_fact_count} SEC companyfacts",
        ),
        readiness("Strategic Pattern", specific_turns > 0, f"{specific_turns} eligible turns, {source_backed_turns} source-backed turns"),
        readiness("Companies Like Mine", Company.objects.count() > 0 and event_total > 0, "basic company/sector/country dimensions exist; stage/revenue dimensions missing"),
        readiness("Risk Signals", eligible_risk_events > 0, f"{eligible_risk_events} eligible risk events after source/date/generic-text gating"),
        readiness("Source Confidence", source_total > 0, f"{source_total} source documents, {source_backed_events} source-backed events"),
        readiness("Latest Strategic Moves", eligible_events > 0, f"{eligible_events} eligible dated events after source/date/generic-text gating"),
        readiness("Founder / Business Questions", eligible_events > 0, "can cite eligible events, but answer templates are not curated"),
        readiness("Strategy Scorecard", specific_turns > 0, f"{specific_turns} eligible turns; impact dimensions still missing"),
        readiness("Compare Strategic Turns", comparable_eligible_turn_types > 0, f"{comparable_eligible_turn_types} eligible repeated turn types"),
    ]


def readiness(name: str, ready: bool, reason: str) -> dict:
    return {"dashboard": name, "status": "usable_with_caveats" if ready else "not_ready", "reason": reason}

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from apps.alerts.models import (
    AlertCategory,
    AlertDeliveryPreference,
    Briefing,
    BriefingCadence,
    BriefingDeliveryLog,
    BriefingFeedback,
    BriefingItem,
    BriefingSection,
    BriefingStatus,
    Notification,
    WatchItem,
    Watchlist,
)
from apps.alerts.services import refresh_alerts_for_user


SECTION_BY_CATEGORY = {
    AlertCategory.STRATEGIC_MOVE: BriefingSection.STRATEGIC_MOVES,
    AlertCategory.EARNINGS_GUIDANCE: BriefingSection.EARNINGS_GUIDANCE,
    AlertCategory.KPI_CHANGE: BriefingSection.EARNINGS_GUIDANCE,
    AlertCategory.PROMISE_UPDATE: BriefingSection.PROMISE_MILESTONE,
    AlertCategory.MILESTONE_UPDATE: BriefingSection.PROMISE_MILESTONE,
    AlertCategory.LEADERSHIP_OWNERSHIP: BriefingSection.STRATEGIC_MOVES,
    AlertCategory.PRODUCT_PRICING: BriefingSection.COMPETITIVE_THEME,
    AlertCategory.ACQUISITION_UPDATE: BriefingSection.STRATEGIC_MOVES,
    AlertCategory.REGULATORY_LITIGATION: BriefingSection.RISK_REGULATORY,
    AlertCategory.RISK_ESCALATION: BriefingSection.RISK_REGULATORY,
    AlertCategory.SOURCE_CORRECTION: BriefingSection.CORRECTIONS,
}

SEVERITY_SCORE = {"HIGH": 100, "MEDIUM": 60, "LOW": 30}


def generate_briefing_for_user(user, cadence: str = BriefingCadence.DAILY, refresh_alerts: bool = True) -> Briefing:
    cadence = cadence if cadence in BriefingCadence.values else BriefingCadence.DAILY
    if refresh_alerts:
        refresh_alerts_for_user(user, limit=12)
    period_start, period_end = briefing_period(cadence)
    notifications = list(
        Notification.objects.filter(owner=user, generated_at__date__gte=period_start, generated_at__date__lte=period_end)
        .select_related("watchlist", "watch_item")
        .order_by("-generated_at", "-id")
    )
    selected = select_material_notifications(notifications)
    gaps = coverage_gap_items(user, period_start, period_end)
    briefing, _created = Briefing.objects.update_or_create(
        owner=user,
        cadence=cadence,
        period_start=period_start,
        period_end=period_end,
        defaults={
            "status": BriefingStatus.READY,
            "title": briefing_title(cadence, period_start, period_end),
            "summary": briefing_summary(selected, gaps),
            "ranking_note": "Ranked by severity, source-backed duplicate grouping, recency, and followed-entity scope. Repeated items are suppressed unless the source-backed notification changed.",
            "scope_summary": scope_summary(user),
            "source_gap_count": len(gaps),
            "notification_count": len(selected),
        },
    )
    briefing.items.all().delete()
    for rank, notification in enumerate(selected, start=1):
        BriefingItem.objects.create(
            briefing=briefing,
            notification=notification,
            section=section_for(notification),
            rank=rank,
            title=notification.title,
            what_changed=notification.what_changed,
            why_it_matters=notification.why_it_matters,
            what_next=what_next(notification),
            evidence_label=notification.source_label,
            evidence_url=notification.source_url,
            source_date=notification.source_date,
            dedupe_key=f"notification:{notification.dedupe_key}",
            metadata={"category": notification.category, "severity": notification.severity, "duplicate_count": notification.duplicate_count},
        )
    gap_rank = len(selected) + 1
    for gap in gaps:
        BriefingItem.objects.create(
            briefing=briefing,
            section=BriefingSection.COVERAGE_GAPS,
            rank=gap_rank,
            title=gap["title"],
            what_changed=gap["what_changed"],
            why_it_matters=gap["why_it_matters"],
            what_next=gap["what_next"],
            evidence_label="InfoDJ watchlist coverage",
            dedupe_key=gap["dedupe_key"],
            metadata=gap,
        )
        gap_rank += 1
    maybe_log_email_delivery(briefing)
    return briefing


def generate_briefings_for_all_users(cadence: str = BriefingCadence.DAILY, refresh_alerts: bool = True) -> dict[str, int]:
    stats = {"users": 0, "briefings_generated": 0, "items_created": 0}
    users = get_user_model().objects.filter(watchlists__is_active=True).distinct()
    for user in users:
        briefing = generate_briefing_for_user(user, cadence=cadence, refresh_alerts=refresh_alerts)
        stats["users"] += 1
        stats["briefings_generated"] += 1
        stats["items_created"] += briefing.items.count()
    return stats


def select_material_notifications(notifications: list[Notification], limit: int = 12) -> list[Notification]:
    deduped = {}
    for notification in notifications:
        key = notification.dedupe_key
        current = deduped.get(key)
        if current is None or ranking_score(notification) > ranking_score(current):
            deduped[key] = notification
    return sorted(deduped.values(), key=ranking_score, reverse=True)[:limit]


def coverage_gap_items(user, period_start, period_end) -> list[dict]:
    watched_items = WatchItem.objects.filter(watchlist__owner=user, watchlist__is_active=True, is_active=True)
    notification_item_ids = set(
        Notification.objects.filter(owner=user, generated_at__date__gte=period_start, generated_at__date__lte=period_end)
        .exclude(watch_item_id=None)
        .values_list("watch_item_id", flat=True)
    )
    gaps = []
    for item in watched_items:
        if item.id in notification_item_ids:
            continue
        gaps.append(
            {
                "title": f"No current alert coverage for {item.label}",
                "what_changed": "No source-backed alert was generated for this followed entity in the briefing period.",
                "why_it_matters": "Coverage gaps prevent the briefing from silently implying that nothing changed.",
                "what_next": "Refresh ingestion sources and alert generation, or review whether this followed entity needs a narrower source rule.",
                "dedupe_key": f"coverage-gap:{item.id}:{period_start}:{period_end}",
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
            }
        )
    return gaps[:20]


def maybe_log_email_delivery(briefing: Briefing) -> None:
    preference = AlertDeliveryPreference.objects.filter(owner=briefing.owner).first()
    if not preference or not preference.email_enabled or preference.email_frequency == "DISABLED":
        return
    if preference.email_frequency != briefing.cadence and preference.email_frequency != "IMMEDIATE":
        return
    BriefingDeliveryLog.objects.create(
        briefing=briefing,
        channel="EMAIL",
        status="QUEUED",
        detail="Email delivery is recorded for the configured cadence; console/email backend handles actual sending.",
    )
    briefing.email_rendered_at = timezone.now()
    briefing.status = BriefingStatus.SENT
    briefing.save(update_fields=["email_rendered_at", "status", "updated_at"])


def briefing_period(cadence: str):
    today = timezone.localdate()
    if cadence == BriefingCadence.WEEKLY:
        return today - timedelta(days=6), today
    return today, today


def ranking_score(notification: Notification) -> int:
    return SEVERITY_SCORE.get(notification.severity, 0) + min(notification.duplicate_count, 10) * 3


def section_for(notification: Notification) -> str:
    if notification.severity == "HIGH":
        return BriefingSection.MOST_IMPORTANT
    return SECTION_BY_CATEGORY.get(notification.category, BriefingSection.ATTENTION)


def what_next(notification: Notification) -> str:
    if notification.category in {AlertCategory.RISK_ESCALATION, AlertCategory.REGULATORY_LITIGATION}:
        return "Review the linked evidence, update affected thesis assumptions, and check deadline or exposure dashboards."
    if notification.category in {AlertCategory.PROMISE_UPDATE, AlertCategory.MILESTONE_UPDATE}:
        return "Review the promise or milestone tracker and update expected next steps."
    if notification.category in {AlertCategory.EARNINGS_GUIDANCE, AlertCategory.KPI_CHANGE}:
        return "Check the earnings and KPI dashboards for metric definitions, guidance changes, and source gaps."
    return "Open the linked dashboard/source and decide whether the company thesis, watchlist rule, or follow-up milestone needs updating."


def briefing_title(cadence: str, period_start, period_end) -> str:
    label = "Weekly" if cadence == BriefingCadence.WEEKLY else "Daily"
    if period_start == period_end:
        return f"{label} briefing for {period_end.isoformat()}"
    return f"{label} briefing for {period_start.isoformat()} to {period_end.isoformat()}"


def briefing_summary(notifications: list[Notification], gaps: list[dict]) -> str:
    if not notifications and not gaps:
        return "No material source-backed changes or coverage gaps were found for the selected watchlists."
    by_category = defaultdict(int)
    for notification in notifications:
        by_category[notification.get_category_display()] += 1
    category_text = ", ".join(f"{count} {category}" for category, count in sorted(by_category.items())) or "no alert categories"
    gap_text = f"{len(gaps)} coverage gaps" if gaps else "no coverage gaps"
    return f"{len(notifications)} material alerts selected across {category_text}; {gap_text} included."


def scope_summary(user) -> str:
    watchlists = Watchlist.objects.filter(owner=user, is_active=True).count()
    items = WatchItem.objects.filter(watchlist__owner=user, watchlist__is_active=True, is_active=True).count()
    return f"{watchlists} active watchlists and {items} followed entities."


def serialize_briefing(briefing: Briefing, include_items: bool = True) -> dict:
    payload = {
        "id": briefing.id,
        "cadence": briefing.cadence,
        "cadence_label": briefing.get_cadence_display(),
        "status": briefing.status,
        "period_start": briefing.period_start.isoformat(),
        "period_end": briefing.period_end.isoformat(),
        "title": briefing.title,
        "summary": briefing.summary,
        "ranking_note": briefing.ranking_note,
        "scope_summary": briefing.scope_summary,
        "source_gap_count": briefing.source_gap_count,
        "notification_count": briefing.notification_count,
        "email_rendered_at": briefing.email_rendered_at.isoformat() if briefing.email_rendered_at else None,
        "generated_at": briefing.generated_at.isoformat(),
    }
    if include_items:
        payload["items"] = [serialize_briefing_item(row) for row in briefing.items.all()]
        payload["delivery_logs"] = [
            {"id": row.id, "channel": row.channel, "status": row.status, "detail": row.detail, "created_at": row.created_at.isoformat()}
            for row in briefing.delivery_logs.all()
        ]
    return payload


def serialize_briefing_item(item: BriefingItem) -> dict:
    return {
        "id": item.id,
        "notification_id": item.notification_id,
        "section": item.section,
        "section_label": item.get_section_display(),
        "rank": item.rank,
        "title": item.title,
        "what_changed": item.what_changed,
        "why_it_matters": item.why_it_matters,
        "what_next": item.what_next,
        "evidence_label": item.evidence_label,
        "evidence_url": item.evidence_url,
        "source_date": item.source_date.isoformat() if item.source_date else None,
        "metadata": item.metadata,
    }


def briefing_feedback(briefing: Briefing, user, rating: str, comment: str = "") -> BriefingFeedback:
    return BriefingFeedback.objects.create(briefing=briefing, user=user, rating=rating, comment=comment)

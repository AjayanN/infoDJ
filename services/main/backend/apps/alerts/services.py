from __future__ import annotations

from datetime import date
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.alerts.models import (
    AlertCategory,
    AlertDeliveryPreference,
    AlertRule,
    AlertSeverity,
    FollowableEntityType,
    Notification,
    WatchItem,
    Watchlist,
)


INGESTION_TIMEOUT_SECONDS = 10

EVENT_CATEGORY_MAP = {
    "PRICE_CHANGE": AlertCategory.PRODUCT_PRICING,
    "PRODUCT_LAUNCH": AlertCategory.PRODUCT_PRICING,
    "PRODUCT_DISCONTINUATION": AlertCategory.PRODUCT_PRICING,
    "ACQUISITION": AlertCategory.ACQUISITION_UPDATE,
    "M&A": AlertCategory.ACQUISITION_UPDATE,
    "LEADERSHIP_CHANGE": AlertCategory.LEADERSHIP_OWNERSHIP,
    "OWNERSHIP_CHANGE": AlertCategory.LEADERSHIP_OWNERSHIP,
    "REGULATORY": AlertCategory.REGULATORY_LITIGATION,
    "LITIGATION": AlertCategory.REGULATORY_LITIGATION,
    "RISK": AlertCategory.RISK_ESCALATION,
    "GUIDANCE": AlertCategory.EARNINGS_GUIDANCE,
    "EARNINGS": AlertCategory.EARNINGS_GUIDANCE,
}


def refresh_alerts_for_user(user, limit: int = 12) -> dict[str, int]:
    stats = {"watchlists": 0, "items": 0, "notifications_created": 0, "notifications_updated": 0, "source_errors": 0}
    watchlists = Watchlist.objects.filter(owner=user, is_active=True).prefetch_related("items", "rules")
    for watchlist in watchlists:
        stats["watchlists"] += 1
        enabled_categories = enabled_categories_for(watchlist)
        for item in watchlist.items.filter(is_active=True):
            stats["items"] += 1
            for candidate in alert_candidates_for_item(item, limit=limit):
                if candidate["category"] not in enabled_categories:
                    continue
                notification, created = Notification.objects.update_or_create(
                    owner=user,
                    dedupe_key=candidate["dedupe_key"],
                    defaults={
                        "watchlist": watchlist,
                        "watch_item": item,
                        "category": candidate["category"],
                        "severity": candidate["severity"],
                        "title": candidate["title"],
                        "what_changed": candidate["what_changed"],
                        "why_it_matters": candidate["why_it_matters"],
                        "previous_state": candidate["previous_state"],
                        "source_label": candidate["source_label"],
                        "source_url": candidate["source_url"],
                        "source_date": candidate["source_date"],
                        "evidence_payload": candidate["evidence_payload"],
                        "duplicate_count": candidate["duplicate_count"],
                    },
                )
                stats["notifications_created" if created else "notifications_updated"] += 1
    return stats


def refresh_alerts_for_all_users(limit: int = 12) -> dict[str, int]:
    stats = {"users": 0, "watchlists": 0, "items": 0, "notifications_created": 0, "notifications_updated": 0, "source_errors": 0}
    for user in get_user_model().objects.filter(watchlists__is_active=True).distinct():
        user_stats = refresh_alerts_for_user(user, limit=limit)
        stats["users"] += 1
        for key, value in user_stats.items():
            stats[key] += value
    return stats


def alert_candidates_for_item(item: WatchItem, limit: int = 12) -> list[dict]:
    if item.entity_type == FollowableEntityType.COMPANY:
        return company_alert_candidates(item, limit=limit)
    return topic_alert_candidates(item, limit=limit)


def company_alert_candidates(item: WatchItem, limit: int = 12) -> list[dict]:
    payload, error = ingestion_get("dashboard-data", {"company": item.company_slug or item.entity_id, "limit": limit})
    if error:
        return []
    rows = []
    dashboard = payload or {}
    for event in dashboard_items(dashboard, "latest_moves") + dashboard.get("latest_events", []):
        rows.append(candidate_from_event(item, event))
    for turn in dashboard_items(dashboard, "strategic_turns") + dashboard.get("latest_turns", []):
        rows.append(candidate_from_turn(item, turn))
    for risk in dashboard_items(dashboard, "risk_signals") + dashboard.get("risk_signals", []):
        rows.append(candidate_from_risk(item, risk))
    return dedupe_candidates([row for row in rows if row])


def topic_alert_candidates(item: WatchItem, limit: int = 12) -> list[dict]:
    payload, error = ingestion_get("search", {"q": item.entity_id or item.label, "language": "en", "limit": limit})
    if error:
        return []
    groups = (payload or {}).get("results", {})
    rows = [candidate_from_event(item, row) for row in group_items(groups, "events")]
    rows.extend(candidate_from_turn(item, row) for row in group_items(groups, "strategic_turns"))
    return dedupe_candidates([row for row in rows if row])


def candidate_from_event(item: WatchItem, event: dict) -> dict:
    event_type = str(event.get("event_type") or "STRATEGIC_MOVE")
    category = event_category(event_type)
    event_id = event.get("id") or f"{event_type}:{event.get('event_date') or ''}:{event.get('actual_change') or ''}"
    return {
        "category": category,
        "severity": severity_for_event(event, category),
        "title": f"{item.label}: {event_type.replace('_', ' ').title()}",
        "what_changed": event.get("actual_change") or event.get("summary") or event.get("source_claim") or "A source-backed company change was detected.",
        "why_it_matters": why_it_matters(category),
        "previous_state": event.get("previous_state") or event.get("decision_theme") or "",
        "source_label": event.get("source_title") or event.get("publisher") or event.get("source_api") or "InfoDJ reviewed event",
        "source_url": event.get("url") or "",
        "source_date": parse_date(event.get("event_date") or event.get("published_date") or event.get("latest_filing")),
        "evidence_payload": event,
        "dedupe_key": f"{item.entity_type}:{item.entity_id}:event:{event_id}:{category}",
        "duplicate_count": max(1, int(event.get("source_count") or 1)),
    }


def candidate_from_turn(item: WatchItem, turn: dict) -> dict:
    turn_type = str(turn.get("turn_type") or "STRATEGIC_MOVE")
    turn_id = turn.get("id") or f"{turn_type}:{turn.get('start_date') or ''}:{turn.get('title') or ''}"
    return {
        "category": AlertCategory.STRATEGIC_MOVE,
        "severity": AlertSeverity.MEDIUM,
        "title": f"{item.label}: {turn.get('title') or turn_type.replace('_', ' ').title()}",
        "what_changed": turn.get("summary") or turn.get("decision") or "A strategic turn was detected.",
        "why_it_matters": "Strategic turns can change the operating thesis, milestone expectations, and dashboard priorities for a followed company.",
        "previous_state": turn.get("previous_state") or "",
        "source_label": "InfoDJ strategic turn",
        "source_url": turn.get("url") or "",
        "source_date": parse_date(turn.get("start_date")),
        "evidence_payload": turn,
        "dedupe_key": f"{item.entity_type}:{item.entity_id}:turn:{turn_id}",
        "duplicate_count": max(1, int(turn.get("source_count") or 1)),
    }


def candidate_from_risk(item: WatchItem, risk: dict) -> dict:
    risk_id = risk.get("id") or f"{risk.get('event_type') or 'risk'}:{risk.get('event_date') or ''}:{risk.get('actual_change') or risk.get('summary') or ''}"
    return {
        "category": AlertCategory.RISK_ESCALATION,
        "severity": AlertSeverity.HIGH,
        "title": f"{item.label}: Risk escalation",
        "what_changed": risk.get("actual_change") or risk.get("summary") or "A risk signal was detected.",
        "why_it_matters": "Risk escalation alerts require attention because they can invalidate assumptions, change milestones, or require source review.",
        "previous_state": risk.get("previous_state") or "",
        "source_label": risk.get("source_title") or "InfoDJ risk signal",
        "source_url": risk.get("url") or "",
        "source_date": parse_date(risk.get("event_date") or risk.get("published_date")),
        "evidence_payload": risk,
        "dedupe_key": f"{item.entity_type}:{item.entity_id}:risk:{risk_id}",
        "duplicate_count": max(1, int(risk.get("source_count") or 1)),
    }


def ensure_default_watchlist(user, company_slug: str, company_name: str) -> Watchlist:
    watchlist, _created = Watchlist.objects.get_or_create(
        owner=user,
        name="Default watchlist",
        defaults={"description": "Primary followed companies and topics."},
    )
    WatchItem.objects.get_or_create(
        watchlist=watchlist,
        entity_type=FollowableEntityType.COMPANY,
        entity_id=company_slug,
        defaults={"label": company_name or company_slug, "company_slug": company_slug},
    )
    ensure_default_rules(watchlist)
    AlertDeliveryPreference.objects.get_or_create(owner=user)
    return watchlist


def ensure_default_rules(watchlist: Watchlist) -> None:
    for category in AlertCategory.values:
        AlertRule.objects.get_or_create(watchlist=watchlist, category=category)


def enabled_categories_for(watchlist: Watchlist) -> set[str]:
    ensure_default_rules(watchlist)
    return set(watchlist.rules.filter(is_enabled=True).values_list("category", flat=True))


def dedupe_candidates(rows: list[dict]) -> list[dict]:
    grouped = {}
    for row in rows:
        key = row["dedupe_key"]
        if key in grouped:
            grouped[key]["duplicate_count"] += row.get("duplicate_count", 1)
        else:
            grouped[key] = row
    return list(grouped.values())


def event_category(event_type: str) -> str:
    normalized = event_type.upper()
    for key, category in EVENT_CATEGORY_MAP.items():
        if key in normalized:
            return category
    return AlertCategory.STRATEGIC_MOVE


def severity_for_event(event: dict, category: str) -> str:
    if category in {AlertCategory.RISK_ESCALATION, AlertCategory.REGULATORY_LITIGATION, AlertCategory.SOURCE_CORRECTION}:
        return AlertSeverity.HIGH
    score = event.get("confidence_score")
    try:
        return AlertSeverity.MEDIUM if float(score or 0) >= 0.65 else AlertSeverity.LOW
    except (TypeError, ValueError):
        return AlertSeverity.MEDIUM


def why_it_matters(category: str) -> str:
    return {
        AlertCategory.STRATEGIC_MOVE: "Strategic move alerts may affect the company thesis, peer comparison, and follow-up milestones.",
        AlertCategory.EARNINGS_GUIDANCE: "Earnings or guidance changes can alter operating expectations and management-promise tracking.",
        AlertCategory.KPI_CHANGE: "KPI changes may indicate acceleration, slowdown, target crossing, or disclosure changes.",
        AlertCategory.PROMISE_UPDATE: "Promise updates affect whether management commitments remain on track.",
        AlertCategory.MILESTONE_UPDATE: "Milestone updates show whether strategic execution is progressing, delayed, or blocked.",
        AlertCategory.LEADERSHIP_OWNERSHIP: "Leadership and ownership changes can shift priorities, incentives, and decision accountability.",
        AlertCategory.PRODUCT_PRICING: "Product or pricing changes can affect customer behavior, competitive positioning, and revenue model assumptions.",
        AlertCategory.ACQUISITION_UPDATE: "Acquisition updates can change integration risk, capital allocation, and promised synergy tracking.",
        AlertCategory.REGULATORY_LITIGATION: "Regulatory and litigation updates can change business exposure and deadlines.",
        AlertCategory.RISK_ESCALATION: "Risk escalation requires review because it can change assumptions and invalidate a thesis.",
        AlertCategory.SOURCE_CORRECTION: "Source corrections or confidence changes affect whether prior conclusions remain reliable.",
    }.get(category, "This alert may require review because it changed a followed entity.")


def dashboard_items(payload: dict, section: str) -> list[dict]:
    return ((payload.get("sections") or {}).get(section) or {}).get("items") or []


def group_items(groups: dict, key: str) -> list[dict]:
    rows = groups.get(key, [])
    if isinstance(rows, dict):
        rows = rows.get("items", [])
    return rows if isinstance(rows, list) else []


def parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


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

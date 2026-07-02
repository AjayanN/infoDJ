from __future__ import annotations

from django.db.models import Count, Q
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.alerts.models import (
    AlertCategory,
    AlertDeliveryPreference,
    AlertFeedback,
    AlertRule,
    AlertStatus,
    Briefing,
    BriefingCadence,
    BriefingStatus,
    DeliveryFrequency,
    FollowableEntityType,
    Notification,
    WatchItem,
    Watchlist,
)
from apps.alerts.briefings import briefing_feedback, generate_briefing_for_user, serialize_briefing
from apps.alerts.services import ensure_default_rules, ensure_default_watchlist, refresh_alerts_for_user


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def watchlists(request):
    if request.method == "POST":
        watchlist = Watchlist.objects.create(
            owner=request.user,
            name=clean_string(request.data.get("name")) or "Untitled watchlist",
            description=clean_string(request.data.get("description")),
        )
        ensure_default_rules(watchlist)
        return Response({"watchlist": serialize_watchlist(watchlist)}, status=201)
    rows = Watchlist.objects.filter(owner=request.user).prefetch_related("items", "rules", "notifications")
    return Response(
        {
            "watchlists": [serialize_watchlist(row, compact=True) for row in rows],
            "summary": watchlist_summary(request.user),
            "entity_types": [{"value": value, "label": label} for value, label in FollowableEntityType.choices],
            "alert_categories": [{"value": value, "label": label} for value, label in AlertCategory.choices],
            "delivery_preference": serialize_preference(get_preference(request.user)),
        }
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def watchlist_detail(request, watchlist_id: int):
    watchlist = get_owned_watchlist(request.user, watchlist_id)
    if request.method == "DELETE":
        watchlist.delete()
        return Response({"status": "deleted"})
    if request.method == "PATCH":
        if "name" in request.data:
            watchlist.name = clean_string(request.data.get("name"))
        if "description" in request.data:
            watchlist.description = clean_string(request.data.get("description"))
        if "is_active" in request.data:
            watchlist.is_active = bool(request.data.get("is_active"))
        watchlist.save()
    return Response({"watchlist": serialize_watchlist(get_owned_watchlist(request.user, watchlist_id))})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def watchlist_items(request, watchlist_id: int):
    watchlist = get_owned_watchlist(request.user, watchlist_id)
    item, _created = WatchItem.objects.update_or_create(
        watchlist=watchlist,
        entity_type=choice_value(request.data.get("entity_type"), FollowableEntityType.values, FollowableEntityType.COMPANY),
        entity_id=clean_string(request.data.get("entity_id")) or clean_string(request.data.get("company_slug")),
        defaults={
            "label": clean_string(request.data.get("label")) or clean_string(request.data.get("entity_id")),
            "company_slug": clean_string(request.data.get("company_slug")),
            "metadata": dict_payload(request.data.get("metadata")),
            "is_active": True,
        },
    )
    watchlist.save(update_fields=["updated_at"])
    return Response({"item": serialize_item(item)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def follow_company(request):
    company_slug = clean_string(request.data.get("company_slug"))
    if not company_slug:
        return Response({"error": "company_slug is required"}, status=400)
    watchlist = ensure_default_watchlist(request.user, company_slug, clean_string(request.data.get("company_name")) or company_slug)
    return Response({"watchlist": serialize_watchlist(watchlist), "status": "followed"}, status=201)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def watchlist_rule(request, watchlist_id: int, category: str):
    watchlist = get_owned_watchlist(request.user, watchlist_id)
    rule, _created = AlertRule.objects.get_or_create(watchlist=watchlist, category=choice_value(category, AlertCategory.values, AlertCategory.STRATEGIC_MOVE))
    if "is_enabled" in request.data:
        rule.is_enabled = bool(request.data.get("is_enabled"))
    if "minimum_severity" in request.data:
        rule.minimum_severity = clean_string(request.data.get("minimum_severity")) or rule.minimum_severity
    rule.save()
    return Response({"rule": serialize_rule(rule)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications(request):
    rows = Notification.objects.filter(owner=request.user).select_related("watchlist", "watch_item")
    if request.GET.get("status"):
        rows = rows.filter(status=request.GET["status"])
    if request.GET.get("category"):
        rows = rows.filter(category=request.GET["category"])
    if request.GET.get("q"):
        query = request.GET["q"].strip()
        rows = rows.filter(Q(title__icontains=query) | Q(what_changed__icontains=query) | Q(why_it_matters__icontains=query))
    limit = safe_int(request.GET.get("limit"), 50)
    return Response(
        {
            "notifications": [serialize_notification(row) for row in rows[:limit]],
            "summary": notification_summary(request.user),
            "quality": alert_quality(request.user),
            "statuses": [{"value": value, "label": label} for value, label in AlertStatus.choices],
            "categories": [{"value": value, "label": label} for value, label in AlertCategory.choices],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_notifications(request):
    stats = refresh_alerts_for_user(request.user, limit=safe_int(request.data.get("limit"), 12))
    return Response({"status": "refreshed", "stats": stats, "summary": notification_summary(request.user)})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def notification_detail(request, notification_id: int):
    notification = get_owned_notification(request.user, notification_id)
    notification.status = choice_value(request.data.get("status"), AlertStatus.values, notification.status)
    notification.save(update_fields=["status", "updated_at"])
    return Response({"notification": serialize_notification(notification)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_feedback(request, notification_id: int):
    notification = get_owned_notification(request.user, notification_id)
    feedback = AlertFeedback.objects.create(
        notification=notification,
        user=request.user,
        rating=clean_string(request.data.get("rating")) or "useful",
        comment=clean_string(request.data.get("comment")),
    )
    return Response({"feedback": {"id": feedback.id, "rating": feedback.rating, "comment": feedback.comment}}, status=201)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def delivery_preference(request):
    preference = get_preference(request.user)
    if request.method == "PATCH":
        for field in ("in_product_enabled", "email_enabled"):
            if field in request.data:
                setattr(preference, field, bool(request.data.get(field)))
        if "email_frequency" in request.data:
            preference.email_frequency = choice_value(request.data.get("email_frequency"), DeliveryFrequency.values, preference.email_frequency)
        if "timezone" in request.data:
            preference.timezone = clean_string(request.data.get("timezone")) or "UTC"
        preference.save()
    return Response({"delivery_preference": serialize_preference(preference)})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def briefings(request):
    if request.method == "POST":
        cadence = choice_value(request.data.get("cadence"), BriefingCadence.values, BriefingCadence.DAILY)
        briefing = generate_briefing_for_user(request.user, cadence=cadence, refresh_alerts=bool(request.data.get("refresh_alerts", True)))
        return Response({"briefing": serialize_briefing(briefing)}, status=201)
    rows = Briefing.objects.filter(owner=request.user).prefetch_related("items", "delivery_logs")
    if request.GET.get("cadence"):
        rows = rows.filter(cadence=request.GET["cadence"])
    if request.GET.get("status"):
        rows = rows.filter(status=request.GET["status"])
    limit = safe_int(request.GET.get("limit"), 20)
    return Response(
        {
            "briefings": [serialize_briefing(row, include_items=False) for row in rows[:limit]],
            "summary": briefing_summary(request.user),
            "cadences": [{"value": value, "label": label} for value, label in BriefingCadence.choices],
            "statuses": [{"value": value, "label": label} for value, label in BriefingStatus.choices],
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def briefing_detail(request, briefing_id: int):
    briefing = get_owned_briefing(request.user, briefing_id)
    if request.method == "PATCH":
        briefing.status = choice_value(request.data.get("status"), BriefingStatus.values, briefing.status)
        briefing.save(update_fields=["status", "updated_at"])
    return Response({"briefing": serialize_briefing(briefing)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def briefing_feedback_view(request, briefing_id: int):
    briefing = get_owned_briefing(request.user, briefing_id)
    feedback = briefing_feedback(
        briefing,
        request.user,
        clean_string(request.data.get("rating")) or "useful",
        clean_string(request.data.get("comment")),
    )
    return Response({"feedback": {"id": feedback.id, "rating": feedback.rating, "comment": feedback.comment}}, status=201)


def get_preference(user) -> AlertDeliveryPreference:
    preference, _created = AlertDeliveryPreference.objects.get_or_create(owner=user)
    return preference


def get_owned_watchlist(user, watchlist_id: int) -> Watchlist:
    try:
        return Watchlist.objects.filter(owner=user).prefetch_related("items", "rules", "notifications").get(id=watchlist_id)
    except Watchlist.DoesNotExist as exc:
        raise Http404("Watchlist not found") from exc


def get_owned_notification(user, notification_id: int) -> Notification:
    try:
        return Notification.objects.filter(owner=user).get(id=notification_id)
    except Notification.DoesNotExist as exc:
        raise Http404("Notification not found") from exc


def get_owned_briefing(user, briefing_id: int) -> Briefing:
    try:
        return Briefing.objects.filter(owner=user).prefetch_related("items", "delivery_logs").get(id=briefing_id)
    except Briefing.DoesNotExist as exc:
        raise Http404("Briefing not found") from exc


def serialize_watchlist(watchlist: Watchlist, compact: bool = False) -> dict:
    payload = {
        "id": watchlist.id,
        "name": watchlist.name,
        "description": watchlist.description,
        "is_active": watchlist.is_active,
        "item_count": watchlist.items.count(),
        "notification_count": watchlist.notifications.count(),
        "unread_count": watchlist.notifications.filter(status=AlertStatus.UNREAD).count(),
        "updated_at": watchlist.updated_at.isoformat(),
    }
    if not compact:
        payload["items"] = [serialize_item(row) for row in watchlist.items.all()]
        payload["rules"] = [serialize_rule(row) for row in watchlist.rules.all()]
    return payload


def serialize_item(item: WatchItem) -> dict:
    return {
        "id": item.id,
        "entity_type": item.entity_type,
        "entity_type_label": item.get_entity_type_display(),
        "entity_id": item.entity_id,
        "label": item.label,
        "company_slug": item.company_slug,
        "metadata": item.metadata,
        "is_active": item.is_active,
    }


def serialize_rule(rule: AlertRule) -> dict:
    return {"id": rule.id, "category": rule.category, "category_label": rule.get_category_display(), "is_enabled": rule.is_enabled, "minimum_severity": rule.minimum_severity}


def serialize_notification(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "watchlist_id": notification.watchlist_id,
        "watchlist_name": notification.watchlist.name if notification.watchlist else "",
        "watch_item_label": notification.watch_item.label if notification.watch_item else "",
        "category": notification.category,
        "category_label": notification.get_category_display(),
        "severity": notification.severity,
        "severity_label": notification.get_severity_display(),
        "status": notification.status,
        "title": notification.title,
        "what_changed": notification.what_changed,
        "why_it_matters": notification.why_it_matters,
        "previous_state": notification.previous_state,
        "source_label": notification.source_label,
        "source_url": notification.source_url,
        "source_date": notification.source_date.isoformat() if notification.source_date else None,
        "duplicate_count": notification.duplicate_count,
        "generated_at": notification.generated_at.isoformat(),
    }


def serialize_preference(preference: AlertDeliveryPreference) -> dict:
    return {
        "in_product_enabled": preference.in_product_enabled,
        "email_enabled": preference.email_enabled,
        "email_frequency": preference.email_frequency,
        "timezone": preference.timezone,
        "quiet_hours_start": preference.quiet_hours_start.isoformat() if preference.quiet_hours_start else None,
        "quiet_hours_end": preference.quiet_hours_end.isoformat() if preference.quiet_hours_end else None,
    }


def watchlist_summary(user) -> dict:
    rows = Watchlist.objects.filter(owner=user)
    return {"total": rows.count(), "active": rows.filter(is_active=True).count(), "followed_items": WatchItem.objects.filter(watchlist__owner=user, is_active=True).count()}


def notification_summary(user) -> dict:
    rows = Notification.objects.filter(owner=user)
    by_status = dict(rows.values("status").annotate(count=Count("id")).values_list("status", "count"))
    return {"total": rows.count(), "unread": by_status.get(AlertStatus.UNREAD, 0), "read": by_status.get(AlertStatus.READ, 0), "archived": by_status.get(AlertStatus.ARCHIVED, 0)}


def alert_quality(user) -> dict:
    rows = Notification.objects.filter(owner=user)
    total = rows.count()
    duplicate_groups = rows.filter(duplicate_count__gt=1).count()
    feedback_count = AlertFeedback.objects.filter(user=user).count()
    return {
        "total_alerts": total,
        "duplicate_group_count": duplicate_groups,
        "duplicate_group_ratio": round((duplicate_groups / total) * 100, 1) if total else 0,
        "feedback_count": feedback_count,
        "noise_monitoring_note": "Use feedback and duplicate grouping to monitor noisy, duplicated, or missed alerts.",
    }


def briefing_summary(user) -> dict:
    rows = Briefing.objects.filter(owner=user)
    by_cadence = dict(rows.values("cadence").annotate(count=Count("id")).values_list("cadence", "count"))
    return {"total": rows.count(), "daily": by_cadence.get(BriefingCadence.DAILY, 0), "weekly": by_cadence.get(BriefingCadence.WEEKLY, 0)}


def clean_string(value) -> str:
    return str(value or "").strip()


def choice_value(value, choices, default):
    value = clean_string(value).upper()
    return value if value in choices else default


def dict_payload(value) -> dict:
    return value if isinstance(value, dict) else {}


def safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

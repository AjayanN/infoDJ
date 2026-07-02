from django.contrib import admin

from apps.alerts.models import (
    AlertDeliveryLog,
    AlertDeliveryPreference,
    AlertFeedback,
    AlertRule,
    Briefing,
    BriefingDeliveryLog,
    BriefingFeedback,
    BriefingItem,
    Notification,
    WatchItem,
    Watchlist,
)


class WatchItemInline(admin.TabularInline):
    model = WatchItem
    extra = 0


class AlertRuleInline(admin.TabularInline):
    model = AlertRule
    extra = 0


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "owner__username", "owner__email")
    inlines = (WatchItemInline, AlertRuleInline)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "severity", "status", "duplicate_count", "generated_at")
    list_filter = ("category", "severity", "status")
    search_fields = ("title", "what_changed", "why_it_matters", "owner__username")


admin.site.register(AlertDeliveryPreference)
admin.site.register(AlertDeliveryLog)
admin.site.register(AlertFeedback)


class BriefingItemInline(admin.TabularInline):
    model = BriefingItem
    extra = 0


@admin.register(Briefing)
class BriefingAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "cadence", "status", "period_start", "period_end", "notification_count")
    list_filter = ("cadence", "status")
    search_fields = ("title", "summary", "owner__username")
    inlines = (BriefingItemInline,)


admin.site.register(BriefingDeliveryLog)
admin.site.register(BriefingFeedback)

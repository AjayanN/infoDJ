from __future__ import annotations

from django.conf import settings
from django.db import models


class FollowableEntityType(models.TextChoices):
    COMPANY = "COMPANY", "Company"
    THEME = "THEME", "Theme"
    PRODUCT = "PRODUCT", "Product"
    LEADER = "LEADER", "Leader"
    PROMISE = "PROMISE", "Management promise"
    MILESTONE = "MILESTONE", "Strategy milestone"
    RISK = "RISK", "Risk"
    REGULATORY_MATTER = "REGULATORY_MATTER", "Regulatory matter"


class AlertCategory(models.TextChoices):
    STRATEGIC_MOVE = "STRATEGIC_MOVE", "Strategic move"
    EARNINGS_GUIDANCE = "EARNINGS_GUIDANCE", "Earnings or guidance change"
    KPI_CHANGE = "KPI_CHANGE", "KPI change"
    PROMISE_UPDATE = "PROMISE_UPDATE", "Promise update"
    MILESTONE_UPDATE = "MILESTONE_UPDATE", "Milestone deadline or status change"
    LEADERSHIP_OWNERSHIP = "LEADERSHIP_OWNERSHIP", "Leadership or ownership change"
    PRODUCT_PRICING = "PRODUCT_PRICING", "Product or pricing change"
    ACQUISITION_UPDATE = "ACQUISITION_UPDATE", "Acquisition update"
    REGULATORY_LITIGATION = "REGULATORY_LITIGATION", "Regulatory or litigation update"
    RISK_ESCALATION = "RISK_ESCALATION", "Risk escalation"
    SOURCE_CORRECTION = "SOURCE_CORRECTION", "Source correction or confidence downgrade"


class AlertSeverity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class AlertStatus(models.TextChoices):
    UNREAD = "UNREAD", "Unread"
    READ = "READ", "Read"
    ARCHIVED = "ARCHIVED", "Archived"


class DeliveryFrequency(models.TextChoices):
    IMMEDIATE = "IMMEDIATE", "Immediate"
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"
    DISABLED = "DISABLED", "Disabled"


class Watchlist(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlists")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["owner", "is_active"], name="watchlist_owner_active_idx")]

    def __str__(self) -> str:
        return self.name


class WatchItem(models.Model):
    watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE, related_name="items")
    entity_type = models.CharField(max_length=32, choices=FollowableEntityType.choices, db_index=True)
    entity_id = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    company_slug = models.SlugField(max_length=255, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["entity_type", "label"]
        constraints = [
            models.UniqueConstraint(fields=["watchlist", "entity_type", "entity_id"], name="unique_watch_item")
        ]

    def __str__(self) -> str:
        return self.label


class AlertRule(models.Model):
    watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE, related_name="rules")
    category = models.CharField(max_length=32, choices=AlertCategory.choices, db_index=True)
    is_enabled = models.BooleanField(default=True, db_index=True)
    minimum_severity = models.CharField(max_length=16, choices=AlertSeverity.choices, default=AlertSeverity.LOW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category"]
        constraints = [models.UniqueConstraint(fields=["watchlist", "category"], name="unique_watchlist_alert_rule")]


class AlertDeliveryPreference(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alert_delivery_preference")
    in_product_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    email_frequency = models.CharField(max_length=16, choices=DeliveryFrequency.choices, default=DeliveryFrequency.DAILY)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.owner} alert delivery"


class Notification(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    watchlist = models.ForeignKey(Watchlist, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    watch_item = models.ForeignKey(WatchItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    category = models.CharField(max_length=32, choices=AlertCategory.choices, db_index=True)
    severity = models.CharField(max_length=16, choices=AlertSeverity.choices, default=AlertSeverity.LOW, db_index=True)
    status = models.CharField(max_length=16, choices=AlertStatus.choices, default=AlertStatus.UNREAD, db_index=True)
    title = models.CharField(max_length=255)
    what_changed = models.TextField()
    why_it_matters = models.TextField()
    previous_state = models.TextField(blank=True)
    source_label = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    source_date = models.DateField(null=True, blank=True)
    evidence_payload = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=255, db_index=True)
    duplicate_count = models.PositiveIntegerField(default=1)
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["owner", "dedupe_key"], name="unique_owner_notification_dedupe")]
        indexes = [
            models.Index(fields=["owner", "status"], name="notification_owner_status_idx"),
            models.Index(fields=["owner", "category"], name="notif_owner_category_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class AlertDeliveryLog(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="delivery_logs")
    channel = models.CharField(max_length=32)
    status = models.CharField(max_length=32)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AlertFeedback(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alert_feedback")
    rating = models.CharField(max_length=32)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

from __future__ import annotations

from django.conf import settings
from django.db import models


class SubscriptionTier(models.TextChoices):
    FREE = "FREE", "Free"
    PRO = "PRO", "Pro"
    ANALYST = "ANALYST", "Analyst"
    ADMIN = "ADMIN", "Admin"


class SubscriptionStatus(models.TextChoices):
    FREE = "FREE", "Free"
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
    ACTIVE = "ACTIVE", "Active"
    PAST_DUE = "PAST_DUE", "Past due"
    CANCELLED = "CANCELLED", "Cancelled"
    DOWNGRADED = "DOWNGRADED", "Downgraded"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=255, blank=True)
    founder_sector = models.CharField(max_length=128, blank=True)
    founder_business_type = models.CharField(max_length=255, blank=True)
    founder_stage = models.CharField(max_length=32, blank=True)
    founder_objective = models.CharField(max_length=64, blank=True)
    founder_geography = models.CharField(max_length=128, blank=True)
    founder_target_customer = models.CharField(max_length=255, blank=True)
    founder_revenue_model = models.CharField(max_length=128, blank=True)
    founder_constraints = models.TextField(blank=True)
    avatar = models.FileField(upload_to="avatars/%Y/%m/", blank=True)
    subscription_tier = models.CharField(
        max_length=32,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
        db_index=True,
    )
    subscription_status = models.CharField(
        max_length=32,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.FREE,
        db_index=True,
    )
    pending_subscription_tier = models.CharField(
        max_length=32,
        choices=SubscriptionTier.choices,
        blank=True,
        db_index=True,
    )
    razorpay_order_id = models.CharField(max_length=128, blank=True)
    razorpay_payment_id = models.CharField(max_length=128, blank=True)
    razorpay_subscription_id = models.CharField(max_length=128, blank=True)
    email_updates_enabled = models.BooleanField(default=True)
    product_updates_enabled = models.BooleanField(default=True)
    research_digest_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user} profile"


class SubscriptionChangeLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription_changes",
    )
    old_tier = models.CharField(max_length=32, choices=SubscriptionTier.choices)
    new_tier = models.CharField(max_length=32, choices=SubscriptionTier.choices)
    old_status = models.CharField(max_length=32, choices=SubscriptionStatus.choices)
    new_status = models.CharField(max_length=32, choices=SubscriptionStatus.choices)
    reason = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=64, default="INTERNAL")
    provider_order_id = models.CharField(max_length=128, blank=True)
    provider_payment_id = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.user}: {self.old_tier} -> {self.new_tier}"


class HistoryDocumentUpload(models.Model):
    """Tenant-owned audit record for a private or public history-document intake."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="history_document_uploads")
    company_slug = models.SlugField(max_length=255)
    rights_scope = models.CharField(max_length=64)
    access_scope = models.CharField(max_length=32, default="private")
    filename = models.CharField(max_length=512)
    content_sha256 = models.CharField(max_length=64, db_index=True)
    ingestion_job_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, default="PENDING", db_index=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["owner", "status", "created_at"])]

from __future__ import annotations

from django.conf import settings
from django.db import models


class ConflictType(models.TextChoices):
    CONTRADICTION = "CONTRADICTION", "Contradiction"
    CLARIFICATION = "CLARIFICATION", "Clarification"
    REVISION = "REVISION", "Revision"
    NORMAL_EVOLUTION = "NORMAL_EVOLUTION", "Normal evolution"


class ContradictionCategory(models.TextChoices):
    STATEMENT_VS_RESULT = "STATEMENT_VS_RESULT", "Statement versus later result"
    STATEMENT_VS_FILING = "STATEMENT_VS_FILING", "Statement versus filing"
    GUIDANCE_VS_ACTUAL = "GUIDANCE_VS_ACTUAL", "Guidance versus actual outcome"
    OLD_VS_NEW_STATEMENT = "OLD_VS_NEW_STATEMENT", "Old statement versus new statement"
    PROMISE_VS_ACTION = "PROMISE_VS_ACTION", "Promise versus action"
    STRATEGY_VS_CAPITAL = "STRATEGY_VS_CAPITAL", "Strategy narrative versus capital allocation"
    SOURCE_VS_SOURCE = "SOURCE_VS_SOURCE", "Source versus source"
    METRIC_DEFINITION = "METRIC_DEFINITION", "Reported metric versus changed definition"


class ReviewLabel(models.TextChoices):
    UNREVIEWED = "UNREVIEWED", "Unreviewed"
    CONFIRMED_CONTRADICTION = "CONFIRMED_CONTRADICTION", "Confirmed contradiction"
    LIKELY_CONTRADICTION = "LIKELY_CONTRADICTION", "Likely contradiction"
    APPARENT_CONFLICT = "APPARENT_CONFLICT", "Apparent conflict"
    RESOLVED = "RESOLVED", "Resolved"
    NOT_CONTRADICTION = "NOT_CONTRADICTION", "Not a contradiction"


class Materiality(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class ContradictionCase(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contradiction_cases")
    company_slug = models.SlugField(max_length=255, blank=True, db_index=True)
    company_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=ContradictionCategory.choices, db_index=True)
    conflict_type = models.CharField(max_length=32, choices=ConflictType.choices, default=ConflictType.CONTRADICTION, db_index=True)
    review_label = models.CharField(max_length=32, choices=ReviewLabel.choices, default=ReviewLabel.UNREVIEWED, db_index=True)
    materiality = models.CharField(max_length=16, choices=Materiality.choices, default=Materiality.MEDIUM, db_index=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    neutral_summary = models.TextField()
    explanation = models.TextField(blank=True)
    correction_path = models.TextField(blank=True)
    human_review_required = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "company_slug"], name="contrad_owner_company_idx"),
            models.Index(fields=["owner", "review_label"], name="contrad_owner_review_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class ContradictionClaim(models.Model):
    case = models.ForeignKey(ContradictionCase, on_delete=models.CASCADE, related_name="claims")
    label = models.CharField(max_length=64)
    claim_text = models.TextField()
    claim_date = models.DateField(null=True, blank=True)
    speaker = models.CharField(max_length=255, blank=True)
    scope = models.CharField(max_length=255, blank=True)
    source_label = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    source_type = models.CharField(max_length=64, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["claim_date", "id"]


class ContradictionResolution(models.Model):
    case = models.ForeignKey(ContradictionCase, on_delete=models.CASCADE, related_name="resolutions")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contradiction_reviews")
    previous_label = models.CharField(max_length=32, choices=ReviewLabel.choices, blank=True)
    new_label = models.CharField(max_length=32, choices=ReviewLabel.choices)
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

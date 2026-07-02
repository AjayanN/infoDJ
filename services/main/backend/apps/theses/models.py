from __future__ import annotations

from django.conf import settings
from django.db import models


class ThesisState(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    STRENGTHENING = "STRENGTHENING", "Strengthening"
    WEAKENING = "WEAKENING", "Weakening"
    INVALIDATED = "INVALIDATED", "Invalidated"
    COMPLETED = "COMPLETED", "Completed"
    ARCHIVED = "ARCHIVED", "Archived"


class EvidenceSide(models.TextChoices):
    SUPPORTING = "SUPPORTING", "Supporting"
    OPPOSING = "OPPOSING", "Opposing"
    NEUTRAL = "NEUTRAL", "Neutral"


class EvidenceType(models.TextChoices):
    COMPANY = "COMPANY", "Company"
    EVENT = "EVENT", "Event"
    STRATEGIC_TURN = "STRATEGIC_TURN", "Strategic turn"
    KPI = "KPI", "KPI"
    PROMISE = "PROMISE", "Management promise"
    SOURCE = "SOURCE", "Source document"
    DASHBOARD_ROW = "DASHBOARD_ROW", "Dashboard row"
    URL = "URL", "External URL"
    NOTE = "NOTE", "User note"


class ThesisMilestoneStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACHIEVED = "ACHIEVED", "Achieved"
    MISSED = "MISSED", "Missed"
    DELAYED = "DELAYED", "Delayed"
    INVALIDATED = "INVALIDATED", "Invalidated"


class IndicatorDirection(models.TextChoices):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER", "Higher is better"
    LOWER_IS_BETTER = "LOWER_IS_BETTER", "Lower is better"
    STABILITY_IS_BETTER = "STABILITY_IS_BETTER", "Stability is better"
    QUALITATIVE = "QUALITATIVE", "Qualitative"


class StrategyThesis(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_theses")
    title = models.CharField(max_length=255)
    company_slug = models.SlugField(max_length=255, blank=True, db_index=True)
    company_name = models.CharField(max_length=255, blank=True)
    statement = models.TextField()
    state = models.CharField(max_length=32, choices=ThesisState.choices, default=ThesisState.DRAFT, db_index=True)
    time_horizon = models.CharField(max_length=255, blank=True)
    review_date = models.DateField(null=True, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    confidence_reason = models.TextField(blank=True)
    assumptions = models.JSONField(default=list, blank=True)
    is_shared = models.BooleanField(default=False, db_index=True)
    shared_label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "state"], name="thesis_owner_state_idx"),
            models.Index(fields=["owner", "company_slug"], name="thesis_owner_company_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class ThesisEvidence(models.Model):
    thesis = models.ForeignKey(StrategyThesis, on_delete=models.CASCADE, related_name="evidence")
    side = models.CharField(max_length=16, choices=EvidenceSide.choices, default=EvidenceSide.SUPPORTING, db_index=True)
    evidence_type = models.CharField(max_length=32, choices=EvidenceType.choices, db_index=True)
    company_slug = models.SlugField(max_length=255, blank=True, db_index=True)
    external_id = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    source_date = models.DateField(null=True, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    user_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["side", "-source_date", "-created_at"]
        indexes = [
            models.Index(fields=["thesis", "side"], name="thesis_evidence_side_idx"),
            models.Index(fields=["thesis", "evidence_type"], name="thesis_evidence_type_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class ThesisMilestone(models.Model):
    thesis = models.ForeignKey(StrategyThesis, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=ThesisMilestoneStatus.choices, default=ThesisMilestoneStatus.PENDING, db_index=True)
    success_criteria = models.TextField(blank=True)
    linked_evidence = models.ForeignKey(ThesisEvidence, null=True, blank=True, on_delete=models.SET_NULL, related_name="linked_milestones")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "id"]

    def __str__(self) -> str:
        return self.title


class ThesisIndicator(models.Model):
    thesis = models.ForeignKey(StrategyThesis, on_delete=models.CASCADE, related_name="indicators")
    name = models.CharField(max_length=255)
    direction = models.CharField(max_length=32, choices=IndicatorDirection.choices, default=IndicatorDirection.QUALITATIVE)
    target = models.CharField(max_length=255, blank=True)
    current_value = models.CharField(max_length=255, blank=True)
    source_hint = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ThesisRevision(models.Model):
    thesis = models.ForeignKey(StrategyThesis, on_delete=models.CASCADE, related_name="revisions")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="thesis_revisions")
    previous_state = models.CharField(max_length=32, choices=ThesisState.choices, blank=True)
    new_state = models.CharField(max_length=32, choices=ThesisState.choices)
    previous_confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    new_confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.thesis}: {self.new_state}"

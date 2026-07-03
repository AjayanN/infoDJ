from __future__ import annotations

from django.conf import settings
from django.db import models


class FailureCategory(models.TextChoices):
    FAILED_PIVOT = "FAILED_PIVOT", "Failed pivot"
    UNSUCCESSFUL_ACQUISITION = "UNSUCCESSFUL_ACQUISITION", "Unsuccessful acquisition"
    FAILED_MARKET_EXPANSION = "FAILED_MARKET_EXPANSION", "Failed market expansion"
    PRODUCT_PRICING_FAILURE = "PRODUCT_PRICING_FAILURE", "Product or pricing failure"
    RESTRUCTURING_WITHOUT_RECOVERY = "RESTRUCTURING_WITHOUT_RECOVERY", "Restructuring without recovery"
    DELAYED_ABANDONED_PROGRAM = "DELAYED_ABANDONED_PROGRAM", "Delayed or abandoned program"
    REGULATORY_BLOCKAGE = "REGULATORY_BLOCKAGE", "Regulatory blockage"
    CAPITAL_ALLOCATION_FAILURE = "CAPITAL_ALLOCATION_FAILURE", "Capital allocation failure"
    COMPETITIVE_DISPLACEMENT = "COMPETITIVE_DISPLACEMENT", "Competitive displacement"
    EXECUTION_BREAKDOWN = "EXECUTION_BREAKDOWN", "Execution breakdown"


class FailureClassification(models.TextChoices):
    FAILURE = "FAILURE", "Failure"
    PARTIAL_FAILURE = "PARTIAL_FAILURE", "Partial failure"
    TEMPORARY_SETBACK = "TEMPORARY_SETBACK", "Temporary setback"
    INCOMPLETE = "INCOMPLETE", "Incomplete"
    TOO_EARLY = "TOO_EARLY", "Too early to judge"


class FailureStage(models.TextChoices):
    THESIS = "THESIS", "Thesis"
    ANNOUNCED = "ANNOUNCED", "Announced"
    EXECUTION = "EXECUTION", "Execution"
    OUTCOME_REVIEW = "OUTCOME_REVIEW", "Outcome review"
    LESSONS = "LESSONS", "Lessons"


class EditorialStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE", "Needs evidence"
    IN_REVIEW = "IN_REVIEW", "In review"
    REVIEWED = "REVIEWED", "Reviewed"
    DISPUTED = "DISPUTED", "Disputed"
    ARCHIVED = "ARCHIVED", "Archived"


class RelatedFeatureType(models.TextChoices):
    PROMISE = "PROMISE", "Management promise"
    MILESTONE = "MILESTONE", "Strategy milestone"
    KPI = "KPI", "Operating KPI"
    CAPITAL_ALLOCATION = "CAPITAL_ALLOCATION", "Capital allocation"
    LEADERSHIP = "LEADERSHIP", "Leadership decision"
    MARKET_CONTEXT = "MARKET_CONTEXT", "Market context"
    ACQUISITION = "ACQUISITION", "Acquisition"
    CONTRADICTION = "CONTRADICTION", "Contradiction"
    OTHER = "OTHER", "Other"


class StrategyFailureCase(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_failure_cases")
    title = models.CharField(max_length=255)
    company_slug = models.SlugField(max_length=255, blank=True, db_index=True)
    company_name = models.CharField(max_length=255, blank=True)
    sector = models.CharField(max_length=255, blank=True, db_index=True)
    category = models.CharField(max_length=40, choices=FailureCategory.choices, db_index=True)
    classification = models.CharField(max_length=32, choices=FailureClassification.choices, default=FailureClassification.TOO_EARLY, db_index=True)
    stage = models.CharField(max_length=32, choices=FailureStage.choices, default=FailureStage.THESIS, db_index=True)
    decision_date = models.DateField(null=True, blank=True)
    review_start = models.DateField(null=True, blank=True)
    review_end = models.DateField(null=True, blank=True)
    minimum_evidence = models.TextField(blank=True)
    elapsed_time_definition = models.TextField(blank=True)
    decision_context = models.TextField(blank=True)
    management_rationale = models.TextField(blank=True)
    original_thesis = models.TextField(blank=True)
    expected_result = models.TextField(blank=True)
    execution_issue = models.TextField(blank=True)
    outcome_definition = models.TextField(blank=True)
    actual_outcome = models.TextField(blank=True)
    counterexamples = models.TextField(blank=True)
    lessons = models.TextField(blank=True)
    correction_path = models.TextField(blank=True)
    editorial_status = models.CharField(max_length=32, choices=EditorialStatus.choices, default=EditorialStatus.DRAFT, db_index=True)
    evidence_count = models.PositiveIntegerField(default=0)
    warning_sign_count = models.PositiveIntegerField(default=0)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "company_slug"], name="failure_owner_company_idx"),
            models.Index(fields=["owner", "category"], name="failure_owner_category_idx"),
            models.Index(fields=["owner", "classification"], name="failure_owner_class_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class FailureEvidence(models.Model):
    case = models.ForeignKey(StrategyFailureCase, on_delete=models.CASCADE, related_name="evidence")
    evidence_type = models.CharField(max_length=64, blank=True)
    label = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    evidence_date = models.DateField(null=True, blank=True)
    source_url = models.URLField(blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["evidence_date", "id"]


class FailureWarningSign(models.Model):
    case = models.ForeignKey(StrategyFailureCase, on_delete=models.CASCADE, related_name="warning_signs")
    signal_date = models.DateField(null=True, blank=True)
    signal = models.CharField(max_length=255)
    why_it_mattered = models.TextField(blank=True)
    observable_at_time = models.BooleanField(default=True)
    source_label = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["signal_date", "id"]


class FailureRelatedLink(models.Model):
    case = models.ForeignKey(StrategyFailureCase, on_delete=models.CASCADE, related_name="related_links")
    feature_type = models.CharField(max_length=32, choices=RelatedFeatureType.choices, default=RelatedFeatureType.OTHER, db_index=True)
    object_label = models.CharField(max_length=255)
    object_id = models.CharField(max_length=255, blank=True)
    relationship_note = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["feature_type", "object_label"]


class FailureReview(models.Model):
    case = models.ForeignKey(StrategyFailureCase, on_delete=models.CASCADE, related_name="reviews")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_failure_reviews")
    previous_status = models.CharField(max_length=32, choices=EditorialStatus.choices, blank=True)
    new_status = models.CharField(max_length=32, choices=EditorialStatus.choices)
    classification = models.CharField(max_length=32, choices=FailureClassification.choices)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

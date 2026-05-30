from django.db import models


class EventType(models.TextChoices):
    BUSINESS_MODEL_PIVOT = "BUSINESS_MODEL_PIVOT", "Business model pivot"
    PRICING_CHANGE = "PRICING_CHANGE", "Pricing change"
    PRODUCT_EXPANSION = "PRODUCT_EXPANSION", "Product expansion"
    GEOGRAPHIC_EXPANSION = "GEOGRAPHIC_EXPANSION", "Geographic expansion"
    CUSTOMER_SEGMENT_SHIFT = "CUSTOMER_SEGMENT_SHIFT", "Customer segment shift"
    DISTRIBUTION_CHANNEL_SHIFT = "DISTRIBUTION_CHANNEL_SHIFT", "Distribution channel shift"
    FUNDING_EVENT = "FUNDING_EVENT", "Funding event"
    ACQUISITION = "ACQUISITION", "Acquisition"
    PARTNERSHIP = "PARTNERSHIP", "Partnership"
    LEADERSHIP_CHANGE = "LEADERSHIP_CHANGE", "Leadership change"
    REGULATORY_RESPONSE = "REGULATORY_RESPONSE", "Regulatory response"
    CRISIS_RESPONSE = "CRISIS_RESPONSE", "Crisis response"
    COMPETITIVE_RESPONSE = "COMPETITIVE_RESPONSE", "Competitive response"
    BRAND_REPOSITIONING = "BRAND_REPOSITIONING", "Brand repositioning"
    REVENUE_MODEL_EXPANSION = "REVENUE_MODEL_EXPANSION", "Revenue model expansion"
    PERFORMANCE_DECLINE = "PERFORMANCE_DECLINE", "Performance decline"
    COST_RESTRUCTURING = "COST_RESTRUCTURING", "Cost restructuring"


class LifecycleStage(models.TextChoices):
    IDEA = "IDEA", "Idea"
    LAUNCH = "LAUNCH", "Launch"
    EARLY_GROWTH = "EARLY_GROWTH", "Early growth"
    SCALE = "SCALE", "Scale"
    MATURITY = "MATURITY", "Maturity"
    TURNAROUND = "TURNAROUND", "Turnaround"
    DECLINE = "DECLINE", "Decline"
    REINVENTION = "REINVENTION", "Reinvention"


class ReviewStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    MERGED = "MERGED", "Merged"


class BusinessEvent(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="business_events",
    )
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_events",
    )
    article_extraction = models.ForeignKey(
        "ingestion.ArticleExtraction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_events",
    )
    event_date = models.DateField(null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=64, choices=EventType.choices, db_index=True)
    lifecycle_stage = models.CharField(
        max_length=32,
        choices=LifecycleStage.choices,
        blank=True,
        db_index=True,
    )
    before_state = models.TextField(blank=True)
    after_state = models.TextField(blank=True)
    trigger = models.TextField(blank=True)
    decision = models.TextField(blank=True)
    decision_theme = models.CharField(max_length=128, blank=True, db_index=True)
    source_claim = models.TextField(blank=True)
    actual_change = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    evidence_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=ReviewStatus.choices,
        default=ReviewStatus.NEEDS_REVIEW,
        db_index=True,
    )
    raw_extraction_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-event_date", "-created_at"]
        indexes = [
            models.Index(fields=["company", "event_type"]),
            models.Index(fields=["company", "review_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.company} - {self.event_type}"


class StrategicTurn(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="strategic_turns",
    )
    title = models.CharField(max_length=512)
    turn_type = models.CharField(max_length=64, choices=EventType.choices, db_index=True)
    start_date = models.DateField(null=True, blank=True, db_index=True)
    end_date = models.DateField(null=True, blank=True)
    lifecycle_stage = models.CharField(
        max_length=32,
        choices=LifecycleStage.choices,
        blank=True,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    before_state = models.TextField(blank=True)
    after_state = models.TextField(blank=True)
    trigger = models.TextField(blank=True)
    decision = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    founder_lesson = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=ReviewStatus.choices,
        default=ReviewStatus.DRAFT,
        db_index=True,
    )
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "title"]
        indexes = [
            models.Index(fields=["company", "turn_type"]),
            models.Index(fields=["company", "review_status"]),
            models.Index(fields=["company", "is_published"]),
        ]

    def __str__(self) -> str:
        return self.title


class StrategicTurnSource(models.Model):
    strategic_turn = models.ForeignKey(
        StrategicTurn,
        on_delete=models.CASCADE,
        related_name="turn_sources",
    )
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        on_delete=models.CASCADE,
        related_name="strategic_turn_sources",
    )
    business_event = models.ForeignKey(
        BusinessEvent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="strategic_turn_sources",
    )
    evidence_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["strategic_turn", "source_document", "business_event"],
                name="unique_turn_source_event",
            )
        ]

    def __str__(self) -> str:
        return f"{self.strategic_turn} <- {self.source_document}"

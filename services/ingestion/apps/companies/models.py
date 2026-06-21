from django.db import models
from django.utils.text import slugify


class Company(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    industry = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255, blank=True)
    wikidata_id = models.CharField(max_length=64, blank=True, db_index=True)
    sec_cik = models.CharField(max_length=32, blank=True, db_index=True)
    website = models.URLField(blank=True)
    founded_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class CompanyProfileStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    REVIEWED = "REVIEWED", "Reviewed"
    PUBLISHED = "PUBLISHED", "Published"


class CompanyProfileSnapshot(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="profile_snapshots",
    )
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="company_profile_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    business_model = models.TextField(blank=True)
    subsidiaries = models.JSONField(default=list, blank=True)
    brands = models.JSONField(default=list, blank=True)
    segments = models.JSONField(default=list, blank=True)
    products = models.JSONField(default=list, blank=True)
    customer_groups = models.JSONField(default=list, blank=True)
    revenue_sources = models.JSONField(default=list, blank=True)
    geographies = models.JSONField(default=list, blank=True)
    leadership = models.JSONField(default=list, blank=True)
    competitors = models.JSONField(default=list, blank=True)
    strategic_priorities = models.JSONField(default=list, blank=True)
    evidence_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "effective_date", "source_document"],
                name="unique_company_profile_snapshot_source",
            )
        ]
        indexes = [
            models.Index(
                fields=["company", "status", "effective_date"],
                name="company_prof_status_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company} profile at {self.effective_date}"


class BusinessModelComponentType(models.TextChoices):
    PAYER = "PAYER", "Payer"
    USER = "USER", "User"
    OFFERING = "OFFERING", "Product or service"
    REVENUE = "REVENUE", "Revenue mechanism"
    CHANNEL = "CHANNEL", "Sales or distribution channel"
    GEOGRAPHY = "GEOGRAPHY", "Geographic market"
    PARTNER = "PARTNER", "Partner"
    COST = "COST", "Cost driver"
    ASSET = "ASSET", "Key asset"


class BusinessModelSnapshot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="business_model_snapshots")
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_model_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "effective_date", "source_document"],
                name="unique_business_model_snapshot_source",
            )
        ]

    def __str__(self) -> str:
        return f"{self.company} business model at {self.effective_date}"


class BusinessModelComponent(models.Model):
    snapshot = models.ForeignKey(BusinessModelSnapshot, on_delete=models.CASCADE, related_name="components")
    component_type = models.CharField(max_length=16, choices=BusinessModelComponentType.choices, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scope = models.CharField(max_length=255, blank=True)
    evidence_text = models.TextField(blank=True)
    is_inferred = models.BooleanField(default=False)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)

    class Meta:
        ordering = ["component_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "component_type", "name", "scope"],
                name="unique_business_model_component",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_component_type_display()}: {self.name}"


class BusinessModelRelationship(models.Model):
    snapshot = models.ForeignKey(BusinessModelSnapshot, on_delete=models.CASCADE, related_name="relationships")
    from_component = models.ForeignKey(
        BusinessModelComponent,
        on_delete=models.CASCADE,
        related_name="outgoing_relationships",
    )
    to_component = models.ForeignKey(
        BusinessModelComponent,
        on_delete=models.CASCADE,
        related_name="incoming_relationships",
    )
    relationship_type = models.CharField(max_length=64, db_index=True)
    description = models.TextField(blank=True)
    evidence_text = models.TextField(blank=True)
    is_inferred = models.BooleanField(default=False)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)

    class Meta:
        ordering = ["relationship_type", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "from_component", "to_component", "relationship_type"],
                name="unique_business_model_relationship",
            )
        ]

    def __str__(self) -> str:
        return f"{self.from_component} {self.relationship_type} {self.to_component}"


class KpiValueType(models.TextChoices):
    REPORTED = "REPORTED", "Reported"
    CALCULATED = "CALCULATED", "Calculated"


class KpiCadence(models.TextChoices):
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    ANNUAL = "ANNUAL", "Annual"
    EVENT = "EVENT", "Event aligned"


class KpiDefinition(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="kpi_definitions")
    slug = models.SlugField(max_length=120)
    name = models.CharField(max_length=255)
    description = models.TextField()
    unit = models.CharField(max_length=64)
    cadence = models.CharField(max_length=16, choices=KpiCadence.choices)
    value_type = models.CharField(max_length=16, choices=KpiValueType.choices, default=KpiValueType.REPORTED)
    scope = models.CharField(max_length=255, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    formula = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    peer_comparable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "slug"], name="unique_company_kpi_slug")]

    def __str__(self) -> str:
        return f"{self.company}: {self.name}"


class KpiDefinitionVersion(models.Model):
    kpi = models.ForeignKey(KpiDefinition, on_delete=models.CASCADE, related_name="definition_versions")
    effective_date = models.DateField(db_index=True)
    definition = models.TextField()
    scope = models.CharField(max_length=255, blank=True)
    change_note = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="kpi_definition_versions"
    )

    class Meta:
        ordering = ["-effective_date"]
        constraints = [models.UniqueConstraint(fields=["kpi", "effective_date"], name="unique_kpi_definition_date")]


class KpiObservation(models.Model):
    kpi = models.ForeignKey(KpiDefinition, on_delete=models.CASCADE, related_name="observations")
    period_start = models.DateField()
    period_end = models.DateField(db_index=True)
    fiscal_year = models.PositiveIntegerField(null=True, blank=True)
    fiscal_period = models.CharField(max_length=16, blank=True)
    value = models.DecimalField(max_digits=24, decimal_places=6)
    segment = models.CharField(max_length=255, blank=True)
    geography = models.CharField(max_length=255, blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="kpi_observations"
    )
    evidence_text = models.TextField(blank=True)
    is_estimated = models.BooleanField(default=False)
    is_restatement = models.BooleanField(default=False)
    is_non_comparable = models.BooleanField(default=False)
    definition_changed = models.BooleanField(default=False)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["period_end", "segment", "geography"]
        constraints = [
            models.UniqueConstraint(
                fields=["kpi", "period_end", "segment", "geography"], name="unique_kpi_observation_scope"
            )
        ]


class KpiTarget(models.Model):
    kpi = models.ForeignKey(KpiDefinition, on_delete=models.CASCADE, related_name="targets")
    target_date = models.DateField(db_index=True)
    target_value = models.DecimalField(max_digits=24, decimal_places=6)
    condition = models.TextField(blank=True)
    status = models.CharField(max_length=32, default="IN_PROGRESS")
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="kpi_targets"
    )

    class Meta:
        ordering = ["target_date"]


class KpiComparability(models.Model):
    kpi = models.ForeignKey(KpiDefinition, on_delete=models.CASCADE, related_name="comparability_records")
    comparable_kpi = models.ForeignKey(KpiDefinition, on_delete=models.CASCADE, related_name="compared_by_records")
    is_comparable = models.BooleanField(default=False)
    rationale = models.TextField()
    reviewed_at = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kpi", "comparable_kpi"], name="unique_kpi_comparability_pair")
        ]


class PromiseType(models.TextChoices):
    COMMITMENT = "COMMITMENT", "Commitment"
    GUIDANCE = "GUIDANCE", "Guidance"
    TARGET = "TARGET", "Target"
    ASPIRATION = "ASPIRATION", "Aspiration"
    STRATEGIC_CLAIM = "STRATEGIC_CLAIM", "Strategic claim"


class PromiseStatus(models.TextChoices):
    ANNOUNCED = "ANNOUNCED", "Announced"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    ACHIEVED = "ACHIEVED", "Achieved"
    PARTIALLY_ACHIEVED = "PARTIALLY_ACHIEVED", "Partially achieved"
    MISSED = "MISSED", "Missed"
    DELAYED = "DELAYED", "Delayed"
    REVISED = "REVISED", "Revised"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    NO_LONGER_DISCLOSED = "NO_LONGER_DISCLOSED", "No longer disclosed"
    TOO_EARLY = "TOO_EARLY", "Too early to judge"
    UNVERIFIABLE = "UNVERIFIABLE", "Unverifiable"


class PromiseReviewStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
    REVIEWED = "REVIEWED", "Reviewed"
    REJECTED = "REJECTED", "Rejected"


class ManagementPromise(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="management_promises")
    slug = models.SlugField(max_length=180)
    title = models.CharField(max_length=512)
    promise_type = models.CharField(max_length=32, choices=PromiseType.choices, db_index=True)
    original_statement = models.TextField()
    speaker = models.CharField(max_length=255, blank=True)
    speaker_role = models.CharField(max_length=255, blank=True)
    statement_date = models.DateField(db_index=True)
    target_start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True, db_index=True)
    metric_name = models.CharField(max_length=255, blank=True)
    baseline_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    target_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    unit = models.CharField(max_length=64, blank=True)
    scope = models.CharField(max_length=255, blank=True)
    conditions = models.TextField(blank=True)
    evaluation_rule = models.TextField(blank=True)
    current_status = models.CharField(
        max_length=32, choices=PromiseStatus.choices, default=PromiseStatus.ANNOUNCED, db_index=True
    )
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="management_promises"
    )
    evidence_text = models.TextField(blank=True)
    linked_kpi = models.ForeignKey(
        KpiDefinition, null=True, blank=True, on_delete=models.SET_NULL, related_name="management_promises"
    )
    linked_strategic_turn = models.ForeignKey(
        "curation.StrategicTurn", null=True, blank=True, on_delete=models.SET_NULL, related_name="management_promises"
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target_end_date", "-statement_date", "title"]
        constraints = [models.UniqueConstraint(fields=["company", "slug"], name="unique_company_promise_slug")]
        indexes = [
            models.Index(fields=["company", "current_status"], name="company_promise_status_idx"),
            models.Index(fields=["company", "target_end_date"], name="company_promise_due_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.company}: {self.title}"


class ManagementPromiseUpdate(models.Model):
    promise = models.ForeignKey(ManagementPromise, on_delete=models.CASCADE, related_name="updates")
    update_date = models.DateField(db_index=True)
    status = models.CharField(max_length=32, choices=PromiseStatus.choices)
    summary = models.TextField()
    previous_target_end_date = models.DateField(null=True, blank=True)
    revised_target_end_date = models.DateField(null=True, blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="promise_updates"
    )
    evidence_text = models.TextField(blank=True)
    is_contradiction_candidate = models.BooleanField(default=False, db_index=True)
    contradiction_note = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["update_date", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["promise", "update_date", "status", "source_document"], name="unique_promise_status_update"
            )
        ]


class EarningsPeriod(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="earnings_periods")
    accession_number = models.CharField(max_length=64)
    fiscal_year = models.IntegerField(db_index=True)
    fiscal_period = models.CharField(max_length=16, db_index=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(db_index=True)
    filed_date = models.DateField(db_index=True)
    headline = models.TextField()
    management_explanation = models.TextField(blank=True)
    infodj_interpretation = models.TextField(blank=True)
    unanswered_questions = models.JSONField(default=list, blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", on_delete=models.PROTECT, related_name="earnings_periods"
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end", "-filed_date"]
        constraints = [
            models.UniqueConstraint(fields=["company", "accession_number"], name="unique_company_earnings_accession")
        ]
        indexes = [models.Index(fields=["company", "period_end"], name="company_earnings_period_idx")]

    def __str__(self) -> str:
        return f"{self.company} {self.fiscal_period} FY{self.fiscal_year}"


class EarningsPeriodDocument(models.Model):
    period = models.ForeignKey(EarningsPeriod, on_delete=models.CASCADE, related_name="documents")
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", on_delete=models.PROTECT, related_name="earnings_document_links"
    )
    document_type = models.CharField(max_length=32, db_index=True)
    evidence_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_type", "source_document_id"]
        constraints = [
            models.UniqueConstraint(fields=["period", "source_document"], name="unique_earnings_period_document")
        ]


class EarningsGuidanceComparison(models.Model):
    period = models.ForeignKey(EarningsPeriod, on_delete=models.CASCADE, related_name="guidance_comparisons")
    metric_name = models.CharField(max_length=255)
    forecast_value = models.DecimalField(max_digits=24, decimal_places=6)
    actual_value = models.DecimalField(max_digits=24, decimal_places=6)
    unit = models.CharField(max_length=64)
    comparison_status = models.CharField(max_length=32)
    forecast_source = models.ForeignKey(
        "ingestion.SourceDocument", on_delete=models.PROTECT, related_name="earnings_guidance_forecasts"
    )
    actual_source = models.ForeignKey(
        "ingestion.SourceDocument", on_delete=models.PROTECT, related_name="earnings_guidance_actuals"
    )
    forecast_evidence = models.TextField()
    actual_evidence = models.TextField()
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["metric_name"]
        constraints = [
            models.UniqueConstraint(fields=["period", "metric_name"], name="unique_earnings_guidance_metric")
        ]


class MilestoneType(models.TextChoices):
    LAUNCH = "LAUNCH", "Launch"
    REGULATORY_APPROVAL = "REGULATORY_APPROVAL", "Regulatory approval"
    MARKET_ENTRY = "MARKET_ENTRY", "Market entry"
    CUSTOMER_TARGET = "CUSTOMER_TARGET", "Customer or user target"
    CAPACITY_TARGET = "CAPACITY_TARGET", "Capacity or production target"
    INTEGRATION = "INTEGRATION", "Integration step"
    COST_SYNERGY = "COST_SYNERGY", "Cost or synergy target"
    PROFITABILITY = "PROFITABILITY", "Profitability or cash-flow target"
    HIRING_RESTRUCTURING = "HIRING_RESTRUCTURING", "Hiring or restructuring step"
    PARTNERSHIP = "PARTNERSHIP", "Partnership delivery"
    PRODUCT_ADOPTION = "PRODUCT_ADOPTION", "Product adoption target"
    STRATEGIC_EXECUTION = "STRATEGIC_EXECUTION", "Strategic execution"


class MilestoneOrigin(models.TextChoices):
    MANAGEMENT = "MANAGEMENT_ANNOUNCED", "Management announced"
    REGULATOR = "REGULATOR_DEFINED", "Regulator defined"
    CONTRACTUAL = "CONTRACTUAL", "Contractual"
    ANALYST_INFERRED = "ANALYST_INFERRED", "Analyst inferred"


class MilestoneStatus(models.TextChoices):
    EXPECTED = "EXPECTED", "Expected"
    STARTED = "STARTED", "Started"
    COMPLETED = "COMPLETED", "Completed"
    DELAYED = "DELAYED", "Delayed"
    CHANGED = "CHANGED", "Changed"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"
    UNKNOWN = "UNKNOWN", "Unknown"


class StrategyMilestone(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="strategy_milestones")
    slug = models.SlugField(max_length=180)
    title = models.CharField(max_length=512)
    milestone_type = models.CharField(max_length=32, choices=MilestoneType.choices, db_index=True)
    origin = models.CharField(max_length=32, choices=MilestoneOrigin.choices, db_index=True)
    current_status = models.CharField(max_length=32, choices=MilestoneStatus.choices, db_index=True)
    expected_start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True, db_index=True)
    date_precision = models.CharField(max_length=16, default="UNKNOWN")
    owner = models.CharField(max_length=255, blank=True)
    success_condition = models.TextField()
    blocker = models.TextField(blank=True)
    outcome_review = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", on_delete=models.PROTECT, related_name="strategy_milestones"
    )
    evidence_text = models.TextField()
    linked_promise = models.ForeignKey(
        ManagementPromise, null=True, blank=True, on_delete=models.SET_NULL, related_name="strategy_milestones"
    )
    linked_kpi = models.ForeignKey(
        KpiDefinition, null=True, blank=True, on_delete=models.SET_NULL, related_name="strategy_milestones"
    )
    linked_strategic_turn = models.ForeignKey(
        "curation.StrategicTurn", null=True, blank=True, on_delete=models.SET_NULL, related_name="milestones"
    )
    related_entities = models.JSONField(default=list, blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expected_end_date", "title"]
        constraints = [models.UniqueConstraint(fields=["company", "slug"], name="unique_company_milestone_slug")]
        indexes = [
            models.Index(fields=["company", "current_status"], name="company_milestone_status_idx"),
            models.Index(fields=["company", "expected_end_date"], name="company_milestone_due_idx"),
        ]


class StrategyMilestoneStatusUpdate(models.Model):
    milestone = models.ForeignKey(StrategyMilestone, on_delete=models.CASCADE, related_name="status_updates")
    status_date = models.DateField(db_index=True)
    status = models.CharField(max_length=32, choices=MilestoneStatus.choices)
    summary = models.TextField()
    blocker = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", on_delete=models.PROTECT, related_name="milestone_status_updates"
    )
    evidence_text = models.TextField()
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["status_date", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "status_date", "status", "source_document"],
                name="unique_milestone_status_update",
            )
        ]


class StrategyMilestoneDependency(models.Model):
    milestone = models.ForeignKey(StrategyMilestone, on_delete=models.CASCADE, related_name="dependencies")
    depends_on = models.ForeignKey(StrategyMilestone, on_delete=models.CASCADE, related_name="dependents")
    relationship = models.CharField(max_length=32, default="REQUIRES")
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["milestone", "depends_on"], name="unique_milestone_dependency")
        ]


class CapitalAllocationCategory(models.TextChoices):
    ACQUISITION_INVESTMENT = "ACQUISITION_INVESTMENT", "Acquisitions and investments"
    CAPEX = "CAPEX", "Capital expenditure"
    R_AND_D = "R_AND_D", "Research and development"
    BUYBACK = "BUYBACK", "Share repurchases"
    DIVIDEND = "DIVIDEND", "Dividends"
    DEBT_ISSUANCE = "DEBT_ISSUANCE", "Debt issuance"
    DEBT_REPAYMENT = "DEBT_REPAYMENT", "Debt repayment"
    RESTRUCTURING = "RESTRUCTURING", "Restructuring"
    CONTENT_INVENTORY = "CONTENT_INVENTORY", "Content and inventory investment"
    INTERNAL_PROGRAM = "INTERNAL_PROGRAM", "Internal strategic programs"
    OPERATING_CASH_FLOW = "OPERATING_CASH_FLOW", "Operating cash flow context"
    CASH_CONTEXT = "CASH_CONTEXT", "Cash balance context"
    FREE_CASH_FLOW = "FREE_CASH_FLOW", "Free cash flow context"


class CapitalAllocationPeriod(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="capital_allocation_periods")
    fiscal_year = models.IntegerField(db_index=True)
    fiscal_period = models.CharField(max_length=16, db_index=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(db_index=True)
    filed_date = models.DateField(null=True, blank=True, db_index=True)
    accession_number = models.CharField(max_length=64, blank=True)
    cadence = models.CharField(max_length=16, choices=KpiCadence.choices, default=KpiCadence.QUARTERLY)
    headline = models.TextField(blank=True)
    total_deployment = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    operating_cash_flow = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    cash_balance = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    free_cash_flow = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    calculation_note = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end", "-filed_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "fiscal_year", "fiscal_period", "period_end"],
                name="unique_capital_allocation_period",
            )
        ]
        indexes = [models.Index(fields=["company", "period_end"], name="company_cap_alloc_period_idx")]

    def __str__(self) -> str:
        return f"{self.company} capital allocation {self.fiscal_period} FY{self.fiscal_year}"


class CapitalAllocationItem(models.Model):
    period = models.ForeignKey(CapitalAllocationPeriod, on_delete=models.CASCADE, related_name="items")
    category = models.CharField(max_length=32, choices=CapitalAllocationCategory.choices, db_index=True)
    label = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=24, decimal_places=6)
    unit = models.CharField(max_length=64, default="USD")
    concept = models.CharField(max_length=255, blank=True, db_index=True)
    source_fact = models.ForeignKey(
        "ingestion.FinancialFact", null=True, blank=True, on_delete=models.SET_NULL, related_name="capital_allocation_items"
    )
    source_document = models.ForeignKey(
        "ingestion.SourceDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="capital_allocation_items"
    )
    evidence_text = models.TextField(blank=True)
    is_context = models.BooleanField(default=False, db_index=True)
    is_calculated = models.BooleanField(default=False)
    calculation_method = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_context", "category", "label"]
        constraints = [
            models.UniqueConstraint(fields=["period", "category", "label", "concept"], name="unique_capital_allocation_item")
        ]

    def __str__(self) -> str:
        return f"{self.period}: {self.label}"


class CompetitiveRelationshipType(models.TextChoices):
    DIRECT = "DIRECT", "Direct competitor"
    CATEGORY = "CATEGORY", "Category competitor"
    SUBSTITUTE = "SUBSTITUTE", "Substitute"
    PLATFORM = "PLATFORM", "Platform competitor"
    SUPPLIER_CUSTOMER = "SUPPLIER_CUSTOMER", "Supplier or customer overlap"
    PEER_BENCHMARK = "PEER_BENCHMARK", "Peer benchmark"


class CompetitiveDimensionType(models.TextChoices):
    PRODUCT_OVERLAP = "PRODUCT_OVERLAP", "Product overlap"
    PRICING_POSITION = "PRICING_POSITION", "Pricing position"
    GEOGRAPHIC_OVERLAP = "GEOGRAPHIC_OVERLAP", "Geographic overlap"
    CUSTOMER_OVERLAP = "CUSTOMER_OVERLAP", "Customer overlap"
    SCALE_COMPARISON = "SCALE_COMPARISON", "Scale comparison"
    COMPETITIVE_ACTION = "COMPETITIVE_ACTION", "Competitive action"
    MOAT_EVIDENCE = "MOAT_EVIDENCE", "Moat evidence"
    OPPOSING_EVIDENCE = "OPPOSING_EVIDENCE", "Opposing evidence"


class CompetitivePositionSnapshot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="competitive_position_snapshots")
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competitive_position_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "effective_date"], name="unique_competitive_position_snapshot")
        ]
        indexes = [models.Index(fields=["company", "status", "effective_date"], name="company_comp_pos_status_idx")]

    def __str__(self) -> str:
        return f"{self.company} competitive position at {self.effective_date}"


class CompetitivePeer(models.Model):
    snapshot = models.ForeignKey(CompetitivePositionSnapshot, on_delete=models.CASCADE, related_name="peers")
    peer_name = models.CharField(max_length=255)
    peer_company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competitive_peer_mentions",
    )
    relationship_type = models.CharField(max_length=32, choices=CompetitiveRelationshipType.choices, db_index=True)
    scope = models.CharField(max_length=255, blank=True)
    geography = models.CharField(max_length=255, blank=True)
    product_overlap = models.JSONField(default=list, blank=True)
    customer_overlap = models.JSONField(default=list, blank=True)
    evidence_text = models.TextField(blank=True)
    is_in_universe = models.BooleanField(default=False, db_index=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)

    class Meta:
        ordering = ["relationship_type", "peer_name"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "peer_name", "relationship_type", "scope"], name="unique_competitive_peer")
        ]

    def __str__(self) -> str:
        return f"{self.snapshot.company} vs {self.peer_name}"


class CompetitiveDimension(models.Model):
    snapshot = models.ForeignKey(CompetitivePositionSnapshot, on_delete=models.CASCADE, related_name="dimensions")
    peer = models.ForeignKey(CompetitivePeer, null=True, blank=True, on_delete=models.CASCADE, related_name="dimensions")
    dimension_type = models.CharField(max_length=32, choices=CompetitiveDimensionType.choices, db_index=True)
    label = models.CharField(max_length=255)
    description = models.TextField()
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competitive_dimensions",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)

    class Meta:
        ordering = ["dimension_type", "label"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "peer", "dimension_type", "label"], name="unique_competitive_dimension")
        ]

    def __str__(self) -> str:
        return f"{self.snapshot.company}: {self.label}"


class ProductOfferingType(models.TextChoices):
    FAMILY = "FAMILY", "Product family"
    PRODUCT = "PRODUCT", "Product"
    EDITION = "EDITION", "Edition"
    PLAN = "PLAN", "Plan"
    FEATURE = "FEATURE", "Feature"
    ADD_ON = "ADD_ON", "Add-on"


class ProductChangeType(models.TextChoices):
    LAUNCH = "LAUNCH", "Launch"
    UPDATE = "UPDATE", "Update"
    RENAME = "RENAME", "Rename"
    BUNDLE = "BUNDLE", "Bundle"
    DISCONTINUATION = "DISCONTINUATION", "Discontinuation"
    MIGRATION = "MIGRATION", "Migration"
    PRICE_CHANGE = "PRICE_CHANGE", "Price change"
    PACKAGING_CHANGE = "PACKAGING_CHANGE", "Packaging change"


class ProductCatalogSnapshot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="product_catalog_snapshots")
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_catalog_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    chronology_note = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "effective_date"], name="unique_product_catalog_snapshot")
        ]
        indexes = [models.Index(fields=["company", "status", "effective_date"], name="company_prod_cat_status_idx")]


class ProductOffering(models.Model):
    snapshot = models.ForeignKey(ProductCatalogSnapshot, on_delete=models.CASCADE, related_name="offerings")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    offering_type = models.CharField(max_length=16, choices=ProductOfferingType.choices, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    availability = models.CharField(max_length=255, blank=True)
    geography = models.CharField(max_length=255, blank=True)
    customer_segment = models.CharField(max_length=255, blank=True)
    evidence_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)

    class Meta:
        ordering = ["offering_type", "name"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "offering_type", "name"], name="unique_product_offering")
        ]


class ProductChange(models.Model):
    snapshot = models.ForeignKey(ProductCatalogSnapshot, on_delete=models.CASCADE, related_name="changes")
    offering = models.ForeignKey(ProductOffering, null=True, blank=True, on_delete=models.SET_NULL, related_name="changes")
    change_type = models.CharField(max_length=32, choices=ProductChangeType.choices, db_index=True)
    title = models.CharField(max_length=512)
    announcement_date = models.DateField(null=True, blank=True, db_index=True)
    effective_date = models.DateField(null=True, blank=True, db_index=True)
    before_state = models.TextField(blank=True)
    after_state = models.TextField(blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_changes",
    )
    linked_event = models.ForeignKey(
        "curation.BusinessEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_changes",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)

    class Meta:
        ordering = ["-effective_date", "-announcement_date", "title"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "title", "change_type", "announcement_date"], name="unique_product_change")
        ]


class PriceObservation(models.Model):
    offering = models.ForeignKey(ProductOffering, on_delete=models.CASCADE, related_name="price_observations")
    observed_date = models.DateField(db_index=True)
    effective_date = models.DateField(null=True, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=6)
    currency = models.CharField(max_length=16)
    billing_period = models.CharField(max_length=32, blank=True)
    geography = models.CharField(max_length=255, blank=True)
    customer_segment = models.CharField(max_length=255, blank=True)
    tax_treatment = models.CharField(max_length=255, blank=True)
    is_promotional = models.BooleanField(default=False, db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="price_observations",
    )
    evidence_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)

    class Meta:
        ordering = ["-effective_date", "-observed_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "observed_date", "currency", "geography", "customer_segment", "billing_period"],
                name="unique_price_observation",
            )
        ]


class AcquisitionStage(models.TextChoices):
    RUMORED_REPORTED = "RUMORED_REPORTED", "Rumored or reported"
    ANNOUNCED = "ANNOUNCED", "Announced"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    APPROVED = "APPROVED", "Approved"
    BLOCKED_ABANDONED = "BLOCKED_ABANDONED", "Blocked or abandoned"
    CLOSED = "CLOSED", "Closed"
    INTEGRATING = "INTEGRATING", "Integrating"
    INTEGRATED = "INTEGRATED", "Integrated"
    DIVESTED = "DIVESTED", "Divested"
    IMPAIRED_WRITTEN_DOWN = "IMPAIRED_WRITTEN_DOWN", "Impaired or written down"
    OUTCOME_REVIEWED = "OUTCOME_REVIEWED", "Outcome reviewed"


class AcquisitionTransactionType(models.TextChoices):
    ACQUISITION = "ACQUISITION", "Acquisition"
    MERGER = "MERGER", "Merger"
    ASSET_PURCHASE = "ASSET_PURCHASE", "Asset purchase"
    MINORITY_INVESTMENT = "MINORITY_INVESTMENT", "Minority investment"
    JOINT_VENTURE = "JOINT_VENTURE", "Joint venture"
    DIVESTITURE = "DIVESTITURE", "Divestiture"


class AcquisitionOutcomeCategory(models.TextChoices):
    TOO_EARLY = "TOO_EARLY", "Too early to assess"
    ON_TRACK = "ON_TRACK", "On track"
    INTEGRATED = "INTEGRATED", "Integrated"
    DELAYED = "DELAYED", "Delayed"
    REVISED = "REVISED", "Revised"
    IMPAIRED = "IMPAIRED", "Impaired"
    DIVESTED = "DIVESTED", "Divested"
    ABANDONED = "ABANDONED", "Abandoned"
    VALUE_UNCLEAR = "VALUE_UNCLEAR", "Value unclear"


class AcquisitionLifecycleDeal(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="acquisition_lifecycle_deals")
    slug = models.SlugField(max_length=255)
    target_name = models.CharField(max_length=255)
    target_company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_target_mentions",
    )
    transaction_type = models.CharField(max_length=32, choices=AcquisitionTransactionType.choices, db_index=True)
    current_stage = models.CharField(max_length=32, choices=AcquisitionStage.choices, db_index=True)
    outcome_category = models.CharField(max_length=32, choices=AcquisitionOutcomeCategory.choices, db_index=True)
    announcement_date = models.DateField(null=True, blank=True, db_index=True)
    expected_close_date = models.DateField(null=True, blank=True, db_index=True)
    close_date = models.DateField(null=True, blank=True, db_index=True)
    purchase_price = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    currency = models.CharField(max_length=16, blank=True)
    payment_form = models.CharField(max_length=128, blank=True)
    approvals = models.JSONField(default=list, blank=True)
    conditions = models.JSONField(default=list, blank=True)
    management_rationale = models.TextField(blank=True)
    promised_synergies = models.TextField(blank=True)
    integration_summary = models.TextField(blank=True)
    outcome_review = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_lifecycle_deals",
    )
    linked_event = models.ForeignKey(
        "curation.BusinessEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_lifecycle_deals",
    )
    linked_strategic_turn = models.ForeignKey(
        "curation.StrategicTurn",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_lifecycle_deals",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-announcement_date", "target_name"]
        constraints = [models.UniqueConstraint(fields=["company", "slug"], name="unique_acquisition_lifecycle_deal")]
        indexes = [
            models.Index(fields=["company", "current_stage"], name="company_acq_stage_idx"),
            models.Index(fields=["company", "outcome_category"], name="company_acq_outcome_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.company} acquisition lifecycle: {self.target_name}"


class AcquisitionLifecycleEvent(models.Model):
    deal = models.ForeignKey(AcquisitionLifecycleDeal, on_delete=models.CASCADE, related_name="stage_events")
    stage = models.CharField(max_length=32, choices=AcquisitionStage.choices, db_index=True)
    event_date = models.DateField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    price_revision = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    currency = models.CharField(max_length=16, blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_lifecycle_events",
    )
    linked_milestone = models.ForeignKey(
        StrategyMilestone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_lifecycle_events",
    )
    linked_product_change = models.ForeignKey(
        ProductChange,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_lifecycle_events",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["event_date", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["deal", "stage", "title", "event_date"], name="unique_acquisition_lifecycle_event")
        ]


class DependencyType(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Named customer"
    CUSTOMER_SEGMENT = "CUSTOMER_SEGMENT", "Customer segment"
    SUPPLIER = "SUPPLIER", "Supplier"
    MANUFACTURER = "MANUFACTURER", "Manufacturer"
    PLATFORM = "PLATFORM", "Platform"
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
    LICENSOR = "LICENSOR", "Licensor"
    INFRASTRUCTURE = "INFRASTRUCTURE", "Infrastructure provider"
    CONTRACT = "CONTRACT", "Contractual dependency"
    PARTNER = "PARTNER", "Partner"


class DependencyMaterialityBand(models.TextChoices):
    DISCLOSED_MATERIAL = "DISCLOSED_MATERIAL", "Disclosed material"
    CONCENTRATION_DISCLOSED = "CONCENTRATION_DISCLOSED", "Concentration disclosed"
    IMPORTANT = "IMPORTANT", "Important"
    CONTEXT = "CONTEXT", "Context"
    UNKNOWN = "UNKNOWN", "Unknown"


class DependencyDisclosureConfidence(models.TextChoices):
    NAMED = "NAMED", "Named counterparty"
    UNNAMED = "UNNAMED", "Unnamed disclosed counterparty"
    CATEGORY_ONLY = "CATEGORY_ONLY", "Category only"
    REVIEWED_INFERENCE = "REVIEWED_INFERENCE", "Reviewed inference"


class DependencyContractTermType(models.TextChoices):
    CONCENTRATION = "CONCENTRATION", "Concentration disclosure"
    RENEWAL = "RENEWAL", "Renewal"
    EXPIRATION = "EXPIRATION", "Expiration"
    EXCLUSIVITY = "EXCLUSIVITY", "Exclusivity"
    MINIMUM_COMMITMENT = "MINIMUM_COMMITMENT", "Minimum commitment"
    TERMINATION = "TERMINATION", "Termination"
    OTHER = "OTHER", "Other contract term"


class CustomerSupplierDependencySnapshot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="dependency_snapshots")
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dependency_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "effective_date"], name="unique_dependency_snapshot")
        ]
        indexes = [models.Index(fields=["company", "status", "effective_date"], name="company_dep_status_idx")]


class CustomerSupplierDependency(models.Model):
    snapshot = models.ForeignKey(CustomerSupplierDependencySnapshot, on_delete=models.CASCADE, related_name="dependencies")
    dependency_type = models.CharField(max_length=32, choices=DependencyType.choices, db_index=True)
    counterparty_name = models.CharField(max_length=255)
    counterparty_company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dependency_counterparty_mentions",
    )
    is_named_counterparty = models.BooleanField(default=False, db_index=True)
    materiality_band = models.CharField(max_length=32, choices=DependencyMaterialityBand.choices, db_index=True)
    disclosure_confidence = models.CharField(max_length=32, choices=DependencyDisclosureConfidence.choices, db_index=True)
    concentration_percent = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    geography = models.CharField(max_length=255, blank=True)
    product_scope = models.CharField(max_length=255, blank=True)
    relationship_summary = models.TextField(blank=True)
    risk_summary = models.TextField(blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_supplier_dependencies",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dependency_type", "counterparty_name"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "dependency_type", "counterparty_name", "product_scope"], name="unique_dependency_relationship")
        ]


class DependencyContractTerm(models.Model):
    dependency = models.ForeignKey(CustomerSupplierDependency, on_delete=models.CASCADE, related_name="contract_terms")
    term_type = models.CharField(max_length=32, choices=DependencyContractTermType.choices, db_index=True)
    effective_date = models.DateField(null=True, blank=True, db_index=True)
    expiration_date = models.DateField(null=True, blank=True, db_index=True)
    description = models.TextField()
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dependency_contract_terms",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32, choices=PromiseReviewStatus.choices, default=PromiseReviewStatus.NEEDS_REVIEW, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["term_type", "expiration_date", "effective_date"]
        constraints = [
            models.UniqueConstraint(fields=["dependency", "term_type", "description"], name="unique_dependency_contract_term")
        ]


class GeographicExpansionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active market"
    ENTERED = "ENTERED", "Entered"
    EXPANDING = "EXPANDING", "Expanding"
    EXITED = "EXITED", "Exited"
    PAUSED = "PAUSED", "Paused"
    UNKNOWN = "UNKNOWN", "Unknown"


class GeographicExpansionSnapshot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="geographic_expansion_snapshots")
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="geographic_expansion_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "effective_date"], name="unique_geographic_expansion_snapshot")
        ]
        indexes = [models.Index(fields=["company", "status", "effective_date"], name="company_geo_exp_status_idx")]

    def __str__(self) -> str:
        return f"{self.company} geographic expansion at {self.effective_date}"


class GeographicExpansionMarket(models.Model):
    snapshot = models.ForeignKey(GeographicExpansionSnapshot, on_delete=models.CASCADE, related_name="markets")
    geography = models.CharField(max_length=255)
    market_type = models.CharField(max_length=64, default="REGION", db_index=True)
    current_status = models.CharField(max_length=32, choices=GeographicExpansionStatus.choices, db_index=True)
    entry_date = models.DateField(null=True, blank=True, db_index=True)
    exit_date = models.DateField(null=True, blank=True, db_index=True)
    local_partnerships = models.JSONField(default=list, blank=True)
    regulatory_barriers = models.JSONField(default=list, blank=True)
    revenue_contribution = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    revenue_currency = models.CharField(max_length=16, blank=True)
    revenue_period = models.CharField(max_length=64, blank=True)
    expansion_rationale = models.TextField(blank=True)
    outcome_summary = models.TextField(blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="geographic_expansion_markets",
    )
    linked_event = models.ForeignKey(
        "curation.BusinessEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="geographic_expansion_markets",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=PromiseReviewStatus.choices,
        default=PromiseReviewStatus.REVIEWED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["geography", "market_type"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "geography", "market_type"], name="unique_geo_expansion_market")
        ]
        indexes = [
            models.Index(fields=["snapshot", "current_status"], name="geo_exp_market_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.snapshot.company} geography: {self.geography}"


class OwnershipHolderType(models.TextChoices):
    FOUNDER = "FOUNDER", "Founder"
    EXECUTIVE = "EXECUTIVE", "Executive"
    DIRECTOR = "DIRECTOR", "Director"
    INSTITUTIONAL = "INSTITUTIONAL", "Institutional"
    STRATEGIC = "STRATEGIC", "Strategic holder"
    GOVERNMENT = "GOVERNMENT", "Government"
    PUBLIC_MARKET = "PUBLIC_MARKET", "Public market"
    UNKNOWN = "UNKNOWN", "Unknown"


class OwnershipPositionType(models.TextChoices):
    INSIDER_CONTEXT = "INSIDER_CONTEXT", "Insider context"
    BENEFICIAL_OWNERSHIP = "BENEFICIAL_OWNERSHIP", "Beneficial ownership"
    VOTING_CONTROL = "VOTING_CONTROL", "Voting control"
    INSTITUTIONAL_POSITION = "INSTITUTIONAL_POSITION", "Institutional position"
    STRATEGIC_STAKE = "STRATEGIC_STAKE", "Strategic stake"


class InsiderTransactionType(models.TextChoices):
    PURCHASE = "PURCHASE", "Purchase"
    SALE = "SALE", "Sale"
    GRANT = "GRANT", "Grant"
    EXERCISE = "EXERCISE", "Exercise"
    PLANNED_SALE = "PLANNED_SALE", "Planned sale"
    OTHER = "OTHER", "Other"


class OwnershipInsiderSnapshot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="ownership_insider_snapshots")
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ownership_insider_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "effective_date"], name="unique_ownership_insider_snapshot")
        ]
        indexes = [models.Index(fields=["company", "status", "effective_date"], name="company_owner_status_idx")]

    def __str__(self) -> str:
        return f"{self.company} ownership and insider activity at {self.effective_date}"


class OwnershipPosition(models.Model):
    snapshot = models.ForeignKey(OwnershipInsiderSnapshot, on_delete=models.CASCADE, related_name="positions")
    holder_name = models.CharField(max_length=255)
    holder_type = models.CharField(max_length=32, choices=OwnershipHolderType.choices, db_index=True)
    position_type = models.CharField(max_length=32, choices=OwnershipPositionType.choices, db_index=True)
    economic_ownership_pct = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    voting_power_pct = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    shares_owned = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    share_class = models.CharField(max_length=128, blank=True)
    filing_date = models.DateField(null=True, blank=True, db_index=True)
    report_period = models.CharField(max_length=64, blank=True)
    disclosure_form = models.CharField(max_length=64, blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ownership_positions",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=PromiseReviewStatus.choices,
        default=PromiseReviewStatus.REVIEWED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["holder_type", "holder_name"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "holder_name", "holder_type", "position_type"], name="unique_ownership_position")
        ]


class InsiderTransaction(models.Model):
    snapshot = models.ForeignKey(OwnershipInsiderSnapshot, on_delete=models.CASCADE, related_name="insider_transactions")
    insider_name = models.CharField(max_length=255)
    insider_role = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(max_length=32, choices=InsiderTransactionType.choices, db_index=True)
    transaction_date = models.DateField(null=True, blank=True, db_index=True)
    shares = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    planned_sale = models.BooleanField(default=False, db_index=True)
    plan_reference = models.CharField(max_length=255, blank=True)
    ownership_after = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="insider_transactions",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=PromiseReviewStatus.choices,
        default=PromiseReviewStatus.REVIEWED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "insider_name"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "insider_name", "transaction_type", "transaction_date"], name="unique_insider_transaction")
        ]


class LeadershipRoleType(models.TextChoices):
    CEO = "CEO", "Chief executive"
    CFO = "CFO", "Chief financial"
    COO = "COO", "Chief operating"
    CHAIR = "CHAIR", "Board chair"
    DIRECTOR = "DIRECTOR", "Director"
    EXECUTIVE = "EXECUTIVE", "Executive"
    BOARD = "BOARD", "Board"
    UNKNOWN = "UNKNOWN", "Unknown"


class LeadershipTransitionType(models.TextChoices):
    CURRENT_ROLE = "CURRENT_ROLE", "Current role"
    APPOINTMENT = "APPOINTMENT", "Appointment"
    DEPARTURE = "DEPARTURE", "Departure"
    ROLE_CHANGE = "ROLE_CHANGE", "Role change"
    BOARD_CHANGE = "BOARD_CHANGE", "Board change"
    SUCCESSION_PLAN = "SUCCESSION_PLAN", "Succession plan"


class LeadershipDecisionType(models.TextChoices):
    STRATEGIC_PRIORITY = "STRATEGIC_PRIORITY", "Strategic priority"
    MATERIAL_DECISION = "MATERIAL_DECISION", "Material decision"
    SUCCESSION = "SUCCESSION", "Succession"
    CAPITAL_ALLOCATION = "CAPITAL_ALLOCATION", "Capital allocation"
    ACQUISITION = "ACQUISITION", "Acquisition"
    MILESTONE = "MILESTONE", "Milestone"
    PROMISE = "PROMISE", "Promise"
    OTHER = "OTHER", "Other"


class LeadershipDecisionSnapshot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="leadership_decision_snapshots")
    effective_date = models.DateField(db_index=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leadership_decision_snapshots",
    )
    status = models.CharField(
        max_length=16,
        choices=CompanyProfileStatus.choices,
        default=CompanyProfileStatus.DRAFT,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    non_causation_note = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "effective_date"], name="unique_leadership_decision_snapshot")
        ]
        indexes = [models.Index(fields=["company", "status", "effective_date"], name="company_leader_status_idx")]


class LeadershipRoleRecord(models.Model):
    snapshot = models.ForeignKey(LeadershipDecisionSnapshot, on_delete=models.CASCADE, related_name="roles")
    leader_name = models.CharField(max_length=255)
    role_title = models.CharField(max_length=255, blank=True)
    role_type = models.CharField(max_length=32, choices=LeadershipRoleType.choices, db_index=True)
    transition_type = models.CharField(max_length=32, choices=LeadershipTransitionType.choices, db_index=True)
    start_date = models.DateField(null=True, blank=True, db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    interim_status = models.BooleanField(default=False, db_index=True)
    co_leadership = models.BooleanField(default=False, db_index=True)
    stated_priorities = models.JSONField(default=list, blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leadership_role_records",
    )
    linked_event = models.ForeignKey(
        "curation.BusinessEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leadership_role_records",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=PromiseReviewStatus.choices,
        default=PromiseReviewStatus.REVIEWED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["leader_name", "role_title"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "leader_name", "role_title", "transition_type"], name="unique_leadership_role_record")
        ]


class LeadershipDecisionRecord(models.Model):
    snapshot = models.ForeignKey(LeadershipDecisionSnapshot, on_delete=models.CASCADE, related_name="decisions")
    title = models.CharField(max_length=255)
    decision_type = models.CharField(max_length=32, choices=LeadershipDecisionType.choices, db_index=True)
    decision_date = models.DateField(null=True, blank=True, db_index=True)
    leader_name = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    evidence_text = models.TextField(blank=True)
    source_document = models.ForeignKey(
        "ingestion.SourceDocument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leadership_decision_records",
    )
    linked_event = models.ForeignKey(
        "curation.BusinessEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leadership_decision_records",
    )
    linked_strategic_turn = models.ForeignKey(
        "curation.StrategicTurn",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leadership_decision_records",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=PromiseReviewStatus.choices,
        default=PromiseReviewStatus.REVIEWED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-decision_date", "title"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "title", "decision_type", "decision_date"], name="unique_leadership_decision_record")
        ]

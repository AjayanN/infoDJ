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

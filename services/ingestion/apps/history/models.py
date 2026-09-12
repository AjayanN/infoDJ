import uuid
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models


class SubjectKind(models.TextChoices):
    COMPANY = "COMPANY", "Company"
    PRODUCT = "PRODUCT", "Product"
    BUSINESS_LINE = "BUSINESS_LINE", "Business line"


class Precision(models.TextChoices):
    DAY = "DAY", "Day"
    MONTH = "MONTH", "Month"
    QUARTER = "QUARTER", "Quarter"
    YEAR = "YEAR", "Year"
    RANGE = "RANGE", "Range"
    UNKNOWN = "UNKNOWN", "Unknown"


class ReviewState(models.TextChoices):
    PENDING = "PENDING", "Pending"
    REVIEWED = "REVIEWED", "Reviewed"
    REJECTED = "REJECTED", "Rejected"
    CONFLICTED = "CONFLICTED", "Conflicted"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class EvidenceRole(models.TextChoices):
    SUPPORTS = "SUPPORTS", "Supports"
    CONTRADICTS = "CONTRADICTS", "Contradicts"


class ResearchSubject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=24, choices=SubjectKind.choices)
    company = models.OneToOneField("companies.Company", null=True, blank=True, on_delete=models.CASCADE, related_name="history_subject")
    parent_subject = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    canonical_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if (self.kind == SubjectKind.COMPANY) != bool(self.company_id):
            raise ValidationError("Only company subjects map directly to Company.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SubjectIdentifier(models.Model):
    subject = models.ForeignKey(ResearchSubject, on_delete=models.CASCADE, related_name="identifiers")
    namespace = models.CharField(max_length=64)
    external_id = models.CharField(max_length=255)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["namespace", "external_id"], name="history_identifier_unique")]


class SubjectAlias(models.Model):
    subject = models.ForeignKey(ResearchSubject, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=255)
    language = models.CharField(max_length=16, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["subject", "alias", "language"], name="history_alias_unique")]


class SubjectRelation(models.Model):
    subject = models.ForeignKey(ResearchSubject, on_delete=models.PROTECT, related_name="relations")
    related_subject = models.ForeignKey(ResearchSubject, on_delete=models.PROTECT, related_name="reverse_relations")
    relation_type = models.CharField(max_length=32)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    precision = models.CharField(max_length=16, choices=Precision.choices, default=Precision.UNKNOWN)
    supporting_claim = models.ForeignKey("HistoricalClaim", null=True, blank=True, on_delete=models.PROTECT, related_name="supported_subject_relations")
    def clean(self):
        if self.subject_id == self.related_subject_id:
            raise ValidationError("A subject cannot relate to itself.")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError("Subject relation date bounds are reversed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class HistoricalClaim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(ResearchSubject, on_delete=models.PROTECT, related_name="claims")
    track = models.CharField(max_length=32)
    claim_type = models.CharField(max_length=64)
    event_kind = models.CharField(max_length=64)
    statement = models.TextField()
    value = models.JSONField(default=dict)
    date_min = models.DateField(null=True, blank=True)
    date_max = models.DateField(null=True, blank=True)
    date_precision = models.CharField(max_length=16, choices=Precision.choices, default=Precision.UNKNOWN)
    original_date_expression = models.CharField(max_length=255, blank=True)
    observed_at = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    schema_version = models.CharField(max_length=16, default="1.0")
    extraction_run = models.ForeignKey("ingestion.ExtractionRun", null=True, blank=True, on_delete=models.PROTECT, related_name="historical_claims")
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="revisions")
    review_state = models.CharField(max_length=16, choices=ReviewState.choices, default=ReviewState.PENDING, db_index=True)
    class Meta:
        indexes = [models.Index(fields=["subject", "track", "review_state"]), models.Index(fields=["date_min", "date_max"])]
    def clean(self):
        if self.date_precision == Precision.UNKNOWN and (self.date_min or self.date_max):
            raise ValidationError("UNKNOWN dates must have null bounds.")
        if self.date_min and self.date_max and self.date_min > self.date_max:
            raise ValidationError("Date bounds are reversed.")
        if self.date_precision == Precision.DAY and self.date_min != self.date_max:
            raise ValidationError("DAY requires equal bounds.")
        if self.value and not isinstance(self.value, dict):
            raise ValidationError("Claim values must be JSON objects.")
        if self.value.get("money") and not {"amount", "currency", "unit"}.issubset(self.value["money"]):
            raise ValidationError("Money claim values require amount, currency, and unit.")
        if self.value.get("headcount") and not {"as_of", "workforce_scope"}.issubset(self.value["headcount"]):
            raise ValidationError("Headcount claim values require as_of and workforce_scope.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ClaimEvidence(models.Model):
    claim = models.ForeignKey(HistoricalClaim, on_delete=models.CASCADE, related_name="evidence_links")
    evidence_span = models.ForeignKey("ingestion.EvidenceSpan", on_delete=models.PROTECT, related_name="claim_links")
    role = models.CharField(max_length=16, choices=EvidenceRole.choices)
    source_family = models.CharField(max_length=128, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["claim", "evidence_span", "role"], name="history_claim_evidence_unique")]


class ClaimReview(models.Model):
    claim = models.ForeignKey(HistoricalClaim, on_delete=models.CASCADE, related_name="review_journal")
    decision = models.CharField(max_length=16, choices=ReviewState.choices)
    reviewer = models.CharField(max_length=255)
    reviewer_type = models.CharField(max_length=64, default="staff")
    rationale = models.TextField()
    conflict_group = models.CharField(max_length=128, blank=True)
    resolution_options = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ClaimRelation(models.Model):
    from_claim = models.ForeignKey(HistoricalClaim, on_delete=models.CASCADE, related_name="outgoing_relations")
    to_claim = models.ForeignKey(HistoricalClaim, on_delete=models.CASCADE, related_name="incoming_relations")
    relation_type = models.CharField(max_length=32)
    supporting_evidence = models.ForeignKey("ingestion.EvidenceSpan", null=True, blank=True, on_delete=models.PROTECT, related_name="claim_relation_links")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["from_claim", "to_claim", "relation_type"], name="history_claim_relation_unique")]


class EpisodeClaim(models.Model):
    episode = models.ForeignKey("curation.LifecycleEpisode", on_delete=models.CASCADE, related_name="history_claims")
    claim = models.ForeignKey(HistoricalClaim, on_delete=models.PROTECT, related_name="episode_links")
    track = models.CharField(max_length=32, blank=True)
    ordering = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["episode", "claim"], name="history_episode_claim_unique")]


class EpisodeStory(models.Model):
    episode = models.ForeignKey("curation.LifecycleEpisode", on_delete=models.CASCADE, related_name="history_stories")
    recipe_version = models.CharField(max_length=32)
    input_evidence_hash = models.CharField(max_length=64)
    input_claim_ids = models.JSONField(default=list)
    chapters = models.JSONField(default=list)
    status = models.CharField(max_length=16)
    access_scope = models.CharField(max_length=64, default="internal")
    generated_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["episode", "recipe_version", "input_evidence_hash"], name="history_episode_story_unique")]


class SourceConnectorConfig(models.Model):
    connector_key = models.CharField(max_length=96, unique=True)
    schema_version = models.CharField(max_length=32)
    endpoint = models.URLField(max_length=2048)
    allowed_domain = models.CharField(max_length=255)
    secret_env_reference = models.CharField(max_length=128, blank=True)
    enabled = models.BooleanField(default=False)
    owner = models.CharField(max_length=255, blank=True)
    coverage_tracks = models.JSONField(default=list, blank=True)
    coverage_start = models.DateField(null=True, blank=True)
    coverage_end = models.DateField(null=True, blank=True)
    requests_per_minute = models.PositiveIntegerField(null=True, blank=True)
    monthly_cost_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        host = (urlparse(self.endpoint).hostname or "").lower()
        allowed = self.allowed_domain.lower().lstrip(".")
        if not host or not allowed or (host != allowed and not host.endswith("." + allowed)):
            raise ValidationError({"endpoint": "Connector endpoint must be inside its allowed_domain."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SubjectSource(models.Model):
    subject = models.ForeignKey(ResearchSubject, on_delete=models.CASCADE, related_name="source_registrations")
    connector = models.ForeignKey(SourceConnectorConfig, on_delete=models.PROTECT, related_name="subject_registrations")
    external_reference = models.CharField(max_length=512)
    enabled = models.BooleanField(default=True)
    coverage_tracks = models.JSONField(default=list, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["subject", "connector", "external_reference"], name="history_subject_source_unique")]


class ConnectorCursor(models.Model):
    subject_source = models.OneToOneField(SubjectSource, on_delete=models.CASCADE, related_name="cursor")
    cursor = models.JSONField(default=dict)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

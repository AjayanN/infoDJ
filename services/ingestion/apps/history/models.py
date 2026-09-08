import uuid
from django.core.exceptions import ValidationError
from django.db import models

class SubjectKind(models.TextChoices):
    COMPANY = "COMPANY", "Company"
    PRODUCT = "PRODUCT", "Product"
    BUSINESS_LINE = "BUSINESS_LINE", "Business line"
class Precision(models.TextChoices):
    DAY = "DAY", "Day"; MONTH = "MONTH", "Month"; QUARTER = "QUARTER", "Quarter"; YEAR = "YEAR", "Year"; RANGE = "RANGE", "Range"; UNKNOWN = "UNKNOWN", "Unknown"
class ReviewState(models.TextChoices):
    PENDING = "PENDING", "Pending"; REVIEWED = "REVIEWED", "Reviewed"; REJECTED = "REJECTED", "Rejected"; CONFLICTED = "CONFLICTED", "Conflicted"; SUPERSEDED = "SUPERSEDED", "Superseded"
class ResearchSubject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=24, choices=SubjectKind.choices)
    company = models.OneToOneField("companies.Company", null=True, blank=True, on_delete=models.CASCADE, related_name="history_subject")
    parent_subject = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    canonical_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):
        if (self.kind == SubjectKind.COMPANY) != bool(self.company_id): raise ValidationError("Only company subjects map directly to Company.")
class SubjectIdentifier(models.Model):
    subject = models.ForeignKey(ResearchSubject, on_delete=models.CASCADE, related_name="identifiers")
    namespace = models.CharField(max_length=64); external_id = models.CharField(max_length=255)
    class Meta: constraints = [models.UniqueConstraint(fields=["namespace", "external_id"], name="history_identifier_unique")]
class SubjectAlias(models.Model):
    subject = models.ForeignKey(ResearchSubject, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=255); language = models.CharField(max_length=16, blank=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["subject", "alias", "language"], name="history_alias_unique")]
class SubjectRelation(models.Model):
    subject = models.ForeignKey(ResearchSubject, on_delete=models.PROTECT, related_name="relations")
    related_subject = models.ForeignKey(ResearchSubject, on_delete=models.PROTECT, related_name="reverse_relations")
    relation_type = models.CharField(max_length=32)
    valid_from = models.DateField(null=True, blank=True); valid_to = models.DateField(null=True, blank=True)
    precision = models.CharField(max_length=16, choices=Precision.choices, default=Precision.UNKNOWN)
    def clean(self):
        if self.subject_id == self.related_subject_id or (self.valid_from and self.valid_to and self.valid_from > self.valid_to): raise ValidationError("Invalid subject relation.")
class HistoricalClaim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(ResearchSubject, on_delete=models.PROTECT, related_name="claims")
    track = models.CharField(max_length=32); claim_type = models.CharField(max_length=64); event_kind = models.CharField(max_length=64)
    statement = models.TextField(); value = models.JSONField(default=dict)
    date_min = models.DateField(null=True, blank=True); date_max = models.DateField(null=True, blank=True)
    date_precision = models.CharField(max_length=16, choices=Precision.choices, default=Precision.UNKNOWN)
    original_date_expression = models.CharField(max_length=255, blank=True); observed_at = models.DateTimeField(null=True, blank=True); recorded_at = models.DateTimeField(auto_now_add=True)
    schema_version = models.CharField(max_length=16, default="1.0"); supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="revisions")
    review_state = models.CharField(max_length=16, choices=ReviewState.choices, default=ReviewState.PENDING, db_index=True)
    class Meta: indexes = [models.Index(fields=["subject", "track", "review_state"]), models.Index(fields=["date_min", "date_max"])]
    def clean(self):
        if self.date_precision == Precision.UNKNOWN and (self.date_min or self.date_max): raise ValidationError("UNKNOWN dates must have null bounds.")
        if self.date_min and self.date_max and self.date_min > self.date_max: raise ValidationError("Date bounds are reversed.")
        if self.date_precision == Precision.DAY and self.date_min != self.date_max: raise ValidationError("DAY requires equal bounds.")
class ClaimReview(models.Model):
    claim = models.ForeignKey(HistoricalClaim, on_delete=models.CASCADE, related_name="review_journal")
    decision = models.CharField(max_length=16, choices=ReviewState.choices); reviewer = models.CharField(max_length=255); rationale = models.TextField(); created_at = models.DateTimeField(auto_now_add=True)
class ClaimRelation(models.Model):
    from_claim = models.ForeignKey(HistoricalClaim, on_delete=models.CASCADE, related_name="outgoing_relations")
    to_claim = models.ForeignKey(HistoricalClaim, on_delete=models.CASCADE, related_name="incoming_relations"); relation_type = models.CharField(max_length=32)
    class Meta: constraints = [models.UniqueConstraint(fields=["from_claim", "to_claim", "relation_type"], name="history_claim_relation_unique")]
class EpisodeClaim(models.Model):
    episode = models.ForeignKey("curation.LifecycleEpisode", on_delete=models.CASCADE, related_name="history_claims")
    claim = models.ForeignKey(HistoricalClaim, on_delete=models.PROTECT, related_name="episode_links"); ordering = models.PositiveIntegerField(default=0)
    class Meta: constraints = [models.UniqueConstraint(fields=["episode", "claim"], name="history_episode_claim_unique")]
class EpisodeStory(models.Model):
    episode = models.ForeignKey("curation.LifecycleEpisode", on_delete=models.CASCADE, related_name="history_stories")
    recipe_version = models.CharField(max_length=32); input_evidence_hash = models.CharField(max_length=64); chapters = models.JSONField(default=list); status = models.CharField(max_length=16); generated_at = models.DateTimeField(auto_now_add=True)
    class Meta: constraints = [models.UniqueConstraint(fields=["episode", "recipe_version", "input_evidence_hash"], name="history_episode_story_unique")]

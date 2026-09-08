from django.db import models

from apps.ingestion.services.url_utils import apply_source_hashes


class SourceStatus(models.TextChoices):
    DISCOVERED = "DISCOVERED", "Discovered"
    APPROVED = "APPROVED", "Approved"
    IGNORED = "IGNORED", "Ignored"
    DUPLICATE = "DUPLICATE", "Duplicate"
    EXTRACTION_PENDING = "EXTRACTION_PENDING", "Extraction pending"
    EXTRACTED = "EXTRACTED", "Extracted"
    EXTRACTION_FAILED = "EXTRACTION_FAILED", "Extraction failed"


class ExtractionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class IngestionJobType(models.TextChoices):
    COMPANY_METADATA_SYNC = "COMPANY_METADATA_SYNC", "Company metadata sync"
    SOURCE_DISCOVERY = "SOURCE_DISCOVERY", "Source discovery"
    ARTICLE_EXTRACTION = "ARTICLE_EXTRACTION", "Article extraction"
    EVENT_EXTRACTION = "EVENT_EXTRACTION", "Event extraction"
    EVENT_CLUSTERING = "EVENT_CLUSTERING", "Event clustering"
    MARKET_DATA = "MARKET_DATA", "Market data"
    FINANCIAL_FACTS = "FINANCIAL_FACTS", "Financial facts"
    FULL_COMPANY_PIPELINE = "FULL_COMPANY_PIPELINE", "Full company pipeline"


class IngestionJobStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    PARTIAL = "PARTIAL", "Partial"
    CANCELLED = "CANCELLED", "Cancelled"


class SourceGapStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    RESOLVED = "RESOLVED", "Resolved"
    WONT_FIX = "WONT_FIX", "Won't fix"


class SourceDocument(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="source_documents",
    )
    source_api = models.CharField(max_length=64)
    url = models.URLField(max_length=2048)
    canonical_url = models.URLField(max_length=2048, blank=True)
    title = models.CharField(max_length=1024)
    publisher = models.CharField(max_length=255, blank=True)
    published_date = models.DateTimeField(null=True, blank=True)
    snippet = models.TextField(blank=True)
    language = models.CharField(max_length=32, blank=True)
    url_hash = models.CharField(max_length=64, unique=True)
    title_hash = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(
        max_length=32,
        choices=SourceStatus.choices,
        default=SourceStatus.DISCOVERED,
        db_index=True,
    )
    duplicate_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="duplicates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_date", "title"]
        indexes = [
            models.Index(fields=["company", "published_date"]),
            models.Index(fields=["company", "source_api"]),
            models.Index(fields=["publisher", "published_date"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.canonical_url or not self.url_hash or not self.title_hash:
            apply_source_hashes(self)
        super().save(*args, **kwargs)


class ArticleExtraction(models.Model):
    source_document = models.OneToOneField(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="article_extraction",
    )
    clean_text = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    extraction_status = models.CharField(
        max_length=32,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.PENDING,
        db_index=True,
    )
    extraction_error = models.TextField(blank=True)
    extractor_name = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.source_document} ({self.extraction_status})"


class EvidenceRecordType(models.TextChoices):
    BUSINESS_EVENT = "BUSINESS_EVENT", "Business event"
    STRATEGIC_TURN = "STRATEGIC_TURN", "Strategic turn"
    FINANCIAL_FACT = "FINANCIAL_FACT", "Financial fact"


class EvidenceReviewStatus(models.TextChoices):
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
    REVIEWED = "REVIEWED", "Reviewed"
    REJECTED = "REJECTED", "Rejected"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class EvidenceRecord(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="evidence_records",
    )
    source_document = models.ForeignKey(
        SourceDocument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="evidence_records",
    )
    record_type = models.CharField(max_length=32, choices=EvidenceRecordType.choices, db_index=True)
    claim_type = models.CharField(max_length=32, default="reported_fact", db_index=True)
    sector = models.CharField(max_length=255, blank=True, db_index=True)
    event_date = models.DateField(null=True, blank=True, db_index=True)
    published_date = models.DateTimeField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=512)
    summary = models.TextField(blank=True)
    source_excerpt = models.TextField(blank=True)
    geography = models.JSONField(default=list, blank=True)
    entities = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    review_status = models.CharField(
        max_length=32,
        choices=EvidenceReviewStatus.choices,
        default=EvidenceReviewStatus.NEEDS_REVIEW,
        db_index=True,
    )
    source_fingerprint = models.CharField(max_length=128, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-event_date", "-published_date", "-updated_at"]
        indexes = [
            models.Index(fields=["company", "record_type", "event_date"]),
            models.Index(fields=["sector", "record_type", "event_date"]),
            models.Index(fields=["review_status", "record_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.company}: {self.title}"


class IngestionJob(models.Model):
    job_type = models.CharField(max_length=64, choices=IngestionJobType.choices)
    company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ingestion_jobs",
    )
    query = models.TextField(blank=True)
    source = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=32,
        choices=IngestionJobStatus.choices,
        default=IngestionJobStatus.PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    sources_found = models.PositiveIntegerField(default=0)
    sources_inserted = models.PositiveIntegerField(default=0)
    duplicates_skipped = models.PositiveIntegerField(default=0)
    articles_extracted = models.PositiveIntegerField(default=0)
    events_extracted = models.PositiveIntegerField(default=0)
    turns_created = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job_type", "status"]),
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["source", "status"]),
        ]

    def __str__(self) -> str:
        company = self.company.name if self.company_id else "global"
        return f"{self.job_type} for {company} ({self.status})"


class SourceGap(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="source_gaps",
    )
    dashboard = models.CharField(max_length=96, db_index=True)
    gap_type = models.CharField(max_length=96, db_index=True)
    provider = models.CharField(max_length=96, blank=True, db_index=True)
    reason = models.TextField()
    next_ingestion_task = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=SourceGapStatus.choices,
        default=SourceGapStatus.OPEN,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["dashboard", "gap_type", "company_id", "provider"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "dashboard", "gap_type", "provider"],
                name="unique_source_gap_scope",
            )
        ]
        indexes = [
            models.Index(fields=["dashboard", "status"]),
            models.Index(fields=["gap_type", "status"]),
            models.Index(fields=["company", "dashboard"]),
        ]

    def __str__(self) -> str:
        company = self.company.name if self.company_id else "global"
        return f"{self.dashboard}:{self.gap_type} for {company}"


class SourceGapResolutionCandidate(models.Model):
    source_gap = models.ForeignKey(
        SourceGap,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="resolution_candidates",
    )
    company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="source_gap_resolution_candidates",
    )
    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="source_gap_resolution_candidates",
    )
    dashboard = models.CharField(max_length=96, db_index=True)
    gap_type = models.CharField(max_length=96, db_index=True)
    candidate_type = models.CharField(max_length=96, db_index=True)
    evidence_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    extraction_status = models.CharField(max_length=32, default="CANDIDATE", db_index=True)
    review_status = models.CharField(max_length=32, default="NEEDS_REVIEW", db_index=True)
    next_action = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["dashboard", "gap_type", "company_id", "-confidence_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "dashboard", "gap_type", "source_document", "candidate_type"],
                name="unique_source_gap_resolution_candidate",
            )
        ]
        indexes = [
            models.Index(fields=["dashboard", "gap_type"]),
            models.Index(fields=["company", "review_status"]),
            models.Index(fields=["source_gap", "review_status"]),
        ]

    def __str__(self) -> str:
        company = self.company.name if self.company_id else "global"
        return f"{self.dashboard}:{self.gap_type} candidate for {company}"


class MarketPrice(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="market_prices",
    )
    ticker = models.CharField(max_length=32, db_index=True)
    provider = models.CharField(max_length=64, default="STOOQ", db_index=True)
    price_date = models.DateField(db_index=True)
    open_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    high_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    low_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    close_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    volume = models.BigIntegerField(null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company", "-price_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "ticker", "provider", "price_date"],
                name="unique_market_price_day",
            )
        ]
        indexes = [
            models.Index(fields=["company", "price_date"]),
            models.Index(fields=["ticker", "price_date"]),
            models.Index(fields=["provider", "price_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.company} {self.ticker} {self.price_date}"


class FinancialFact(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="financial_facts",
    )
    taxonomy = models.CharField(max_length=64, db_index=True)
    concept = models.CharField(max_length=128, db_index=True)
    label = models.CharField(max_length=255, blank=True)
    unit = models.CharField(max_length=64, db_index=True)
    fy = models.IntegerField(null=True, blank=True, db_index=True)
    fp = models.CharField(max_length=16, blank=True, db_index=True)
    filed = models.DateField(null=True, blank=True, db_index=True)
    frame = models.CharField(max_length=64, blank=True, db_index=True)
    value = models.DecimalField(max_digits=24, decimal_places=3)
    accession_number = models.CharField(max_length=64, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company", "concept", "-fy", "-filed"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "taxonomy", "concept", "unit", "fy", "fp", "frame", "filed", "accession_number"],
                name="unique_financial_fact_period",
            )
        ]
        indexes = [
            models.Index(fields=["company", "concept", "fy"]),
            models.Index(fields=["company", "filed"]),
            models.Index(fields=["concept", "unit"]),
        ]

    def __str__(self) -> str:
        return f"{self.company} {self.concept} {self.fy or ''}{self.fp}"

class SourceRevision(models.Model):
    source_document=models.ForeignKey(SourceDocument,on_delete=models.PROTECT,related_name="revisions")
    content_sha256=models.CharField(max_length=64); retrieved_at=models.DateTimeField(); published_at=models.DateTimeField(null=True,blank=True)
    archive_captured_at=models.DateTimeField(null=True,blank=True); media_type=models.CharField(max_length=128); storage_key=models.CharField(max_length=1024)
    rights_scope=models.CharField(max_length=64,default="internal"); etag=models.CharField(max_length=255,blank=True); last_modified=models.CharField(max_length=255,blank=True); parser_version=models.CharField(max_length=64)
    class Meta: constraints=[models.UniqueConstraint(fields=["source_document","content_sha256"],name="ingestion_source_revision_hash")]
class ExtractionRun(models.Model):
    revision=models.ForeignKey(SourceRevision,on_delete=models.PROTECT,related_name="extraction_runs"); run_fingerprint=models.CharField(max_length=128,unique=True)
    schema_version=models.CharField(max_length=32); parser_version=models.CharField(max_length=64); status=models.CharField(max_length=16); error=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
class EvidenceSpan(models.Model):
    revision=models.ForeignKey(SourceRevision,on_delete=models.PROTECT,related_name="evidence_spans"); extraction_run=models.ForeignKey(ExtractionRun,null=True,blank=True,on_delete=models.SET_NULL)
    locator=models.CharField(max_length=512); excerpt=models.TextField(); excerpt_sha256=models.CharField(max_length=64); page=models.PositiveIntegerField(null=True,blank=True); char_start=models.PositiveIntegerField(null=True,blank=True); char_end=models.PositiveIntegerField(null=True,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["revision","locator","excerpt_sha256"],name="ingestion_evidence_span_unique")]

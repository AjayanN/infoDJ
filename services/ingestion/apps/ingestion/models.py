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
    FULL_COMPANY_PIPELINE = "FULL_COMPANY_PIPELINE", "Full company pipeline"


class IngestionJobStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    PARTIAL = "PARTIAL", "Partial"
    CANCELLED = "CANCELLED", "Cancelled"


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

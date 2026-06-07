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

from __future__ import annotations

from django.contrib import admin
from django.utils import timezone

from apps.curation.admin_helpers import register_planned_model
from apps.ingestion.models import IngestionJob, IngestionJobType, SourceDocument
from apps.ingestion.services.gdelt_client import discover_sources_for_company
from apps.ingestion.services.query_generator import generate_query_strings
from apps.ingestion.services.sec_edgar_client import discover_sec_filings_for_company
from apps.ingestion.services.wikidata_client import sync_company_metadata


class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "country",
        "industry",
        "wikidata_id",
        "sec_cik",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active", "country", "industry", "created_at", "updated_at")
    search_fields = (
        "name",
        "slug",
        "aliases",
        "country",
        "industry",
        "wikidata_id",
        "sec_cik",
        "website",
        "description",
    )
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    actions = ("resolve_from_wikidata", "collect_gdelt_sources", "collect_sec_edgar_filings")

    @admin.action(description="Resolve selected companies from Wikidata")
    def resolve_from_wikidata(self, request, queryset):
        succeeded = 0
        failed = 0
        for company in queryset:
            job = IngestionJob.objects.create(
                company=company,
                job_type=IngestionJobType.COMPANY_METADATA_SYNC,
                source="WIKIDATA",
                status="PENDING",
            )
            try:
                sync_company_metadata(company, job=job)
                succeeded += 1
            except Exception:
                failed += 1
        self.message_user(request, f"Wikidata sync complete: {succeeded} succeeded, {failed} failed.")

    @admin.action(description="Collect GDELT sources for selected companies")
    def collect_gdelt_sources(self, request, queryset):
        succeeded = 0
        failed = 0
        inserted = 0
        duplicates = 0
        for company in queryset:
            aliases = company.aliases if isinstance(company.aliases, list) else []
            queries = generate_query_strings(company.name, aliases=aliases, include_aliases=False)
            job = IngestionJob.objects.create(
                company=company,
                job_type=IngestionJobType.SOURCE_DISCOVERY,
                source="GDELT_DOC_2",
                query="\n".join(queries),
                status="PENDING",
                started_at=timezone.now(),
            )
            try:
                counters = discover_sources_for_company(
                    company=company,
                    queries=queries,
                    source_document_model=SourceDocument,
                    job=job,
                    max_records_per_query=25,
                )
                inserted += counters["sources_inserted"]
                duplicates += counters["duplicates_skipped"]
                succeeded += 1
            except Exception:
                failed += 1
        self.message_user(
            request,
            f"GDELT collection complete: {succeeded} succeeded, {failed} failed, "
            f"{inserted} inserted, {duplicates} duplicates skipped.",
        )

    @admin.action(description="Collect SEC EDGAR filings for selected companies")
    def collect_sec_edgar_filings(self, request, queryset):
        succeeded = 0
        failed = 0
        inserted = 0
        duplicates = 0
        for company in queryset:
            ticker = "NFLX" if company.slug == "netflix" else company.slug.upper()
            job = IngestionJob.objects.create(
                company=company,
                job_type=IngestionJobType.SOURCE_DISCOVERY,
                source="SEC_EDGAR",
                query=f"{ticker}: 10-K, 10-Q, 8-K",
                status="PENDING",
            )
            try:
                counters = discover_sec_filings_for_company(
                    company=company,
                    source_document_model=SourceDocument,
                    ticker=ticker,
                    forms=("10-K", "10-Q", "8-K"),
                    limit=20,
                    job=job,
                )
                inserted += counters["sources_inserted"]
                duplicates += counters["duplicates_skipped"]
                succeeded += 1
            except Exception:
                failed += 1
        self.message_user(
            request,
            f"SEC EDGAR collection complete: {succeeded} succeeded, {failed} failed, "
            f"{inserted} inserted, {duplicates} duplicates skipped.",
        )


register_planned_model("companies", "Company", CompanyAdmin)

from __future__ import annotations

from django.contrib import admin
from django.utils import timezone

from apps.curation.admin_helpers import register_planned_model
from apps.ingestion.models import IngestionJob, IngestionJobType, SourceDocument
from apps.ingestion.services.gdelt_client import discover_sources_for_company
from apps.ingestion.services.query_generator import generate_query_strings
from apps.ingestion.services.sec_edgar_client import discover_sec_filings_for_company
from apps.ingestion.services.wikidata_client import sync_company_metadata
from apps.companies.models import (
    BusinessModelComponent,
    BusinessModelRelationship,
    BusinessModelSnapshot,
    CapitalAllocationItem,
    CapitalAllocationPeriod,
    CompanyProfileSnapshot,
    EarningsGuidanceComparison,
    EarningsPeriod,
    EarningsPeriodDocument,
    KpiComparability,
    KpiDefinition,
    KpiDefinitionVersion,
    KpiObservation,
    KpiTarget,
    ManagementPromise,
    ManagementPromiseUpdate,
    StrategyMilestone,
    StrategyMilestoneDependency,
    StrategyMilestoneStatusUpdate,
)


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


@admin.register(CompanyProfileSnapshot)
class CompanyProfileSnapshotAdmin(admin.ModelAdmin):
    list_display = ("company", "effective_date", "status", "confidence_score", "source_document", "updated_at")
    list_filter = ("status", "effective_date", "company")
    search_fields = ("company__name", "summary", "business_model", "evidence_text")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-effective_date", "company__name")


class BusinessModelComponentInline(admin.TabularInline):
    model = BusinessModelComponent
    extra = 0


class BusinessModelRelationshipInline(admin.TabularInline):
    model = BusinessModelRelationship
    extra = 0
    fk_name = "snapshot"


@admin.register(BusinessModelSnapshot)
class BusinessModelSnapshotAdmin(admin.ModelAdmin):
    list_display = ("company", "effective_date", "status", "confidence_score", "source_document", "updated_at")
    list_filter = ("status", "effective_date", "company")
    search_fields = ("company__name", "summary")
    readonly_fields = ("created_at", "updated_at")
    inlines = (BusinessModelComponentInline, BusinessModelRelationshipInline)


@admin.register(BusinessModelComponent)
class BusinessModelComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "component_type", "snapshot", "scope", "is_inferred", "confidence_score")
    list_filter = ("component_type", "is_inferred", "snapshot__company")
    search_fields = ("name", "description", "evidence_text", "snapshot__company__name")


@admin.register(BusinessModelRelationship)
class BusinessModelRelationshipAdmin(admin.ModelAdmin):
    list_display = ("from_component", "relationship_type", "to_component", "snapshot", "is_inferred")
    list_filter = ("relationship_type", "is_inferred", "snapshot__company")
    search_fields = ("description", "evidence_text", "snapshot__company__name")


class KpiDefinitionVersionInline(admin.TabularInline):
    model = KpiDefinitionVersion
    extra = 0


class KpiObservationInline(admin.TabularInline):
    model = KpiObservation
    extra = 0


@admin.register(KpiDefinition)
class KpiDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "unit", "cadence", "value_type", "is_active", "peer_comparable")
    list_filter = ("cadence", "value_type", "is_active", "peer_comparable", "company")
    search_fields = ("name", "slug", "description", "aliases", "company__name")
    inlines = (KpiDefinitionVersionInline, KpiObservationInline)


@admin.register(KpiObservation)
class KpiObservationAdmin(admin.ModelAdmin):
    list_display = ("kpi", "period_end", "value", "segment", "geography", "is_estimated", "is_restatement")
    list_filter = ("is_estimated", "is_restatement", "is_non_comparable", "definition_changed", "kpi__company")
    search_fields = ("kpi__name", "evidence_text", "segment", "geography")


admin.site.register(KpiDefinitionVersion)
admin.site.register(KpiTarget)
admin.site.register(KpiComparability)


class ManagementPromiseUpdateInline(admin.TabularInline):
    model = ManagementPromiseUpdate
    extra = 0


@admin.register(ManagementPromise)
class ManagementPromiseAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "promise_type", "current_status", "target_end_date", "review_status", "is_published")
    list_filter = ("promise_type", "current_status", "review_status", "is_published", "company")
    search_fields = ("title", "original_statement", "speaker", "metric_name", "company__name")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (ManagementPromiseUpdateInline,)


@admin.register(ManagementPromiseUpdate)
class ManagementPromiseUpdateAdmin(admin.ModelAdmin):
    list_display = ("promise", "update_date", "status", "is_contradiction_candidate", "review_status")
    list_filter = ("status", "is_contradiction_candidate", "review_status", "promise__company")
    search_fields = ("promise__title", "summary", "evidence_text", "contradiction_note")


@admin.register(EarningsPeriod)
class EarningsPeriodAdmin(admin.ModelAdmin):
    list_display = ("company", "fiscal_period", "fiscal_year", "period_end", "filed_date", "review_status", "is_published")
    list_filter = ("fiscal_period", "review_status", "is_published", "company")
    search_fields = ("company__name", "accession_number", "headline", "management_explanation")


@admin.register(EarningsPeriodDocument)
class EarningsPeriodDocumentAdmin(admin.ModelAdmin):
    list_display = ("period", "document_type", "source_document", "review_status", "confidence_score")
    list_filter = ("document_type", "review_status", "period__company")
    search_fields = ("period__company__name", "source_document__title", "evidence_text")
    actions = ("mark_reviewed",)

    @admin.action(description="Mark selected earnings documents reviewed")
    def mark_reviewed(self, request, queryset):
        queryset.exclude(evidence_text="").update(review_status="REVIEWED")


@admin.register(EarningsGuidanceComparison)
class EarningsGuidanceComparisonAdmin(admin.ModelAdmin):
    list_display = ("period", "metric_name", "forecast_value", "actual_value", "comparison_status", "review_status")
    list_filter = ("comparison_status", "review_status", "period__company")
    search_fields = ("period__company__name", "metric_name", "forecast_evidence", "actual_evidence")


class StrategyMilestoneStatusUpdateInline(admin.TabularInline):
    model = StrategyMilestoneStatusUpdate
    extra = 0


class StrategyMilestoneDependencyInline(admin.TabularInline):
    model = StrategyMilestoneDependency
    fk_name = "milestone"
    extra = 0


@admin.register(StrategyMilestone)
class StrategyMilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "milestone_type", "origin", "current_status", "expected_end_date", "review_status", "is_published")
    list_filter = ("milestone_type", "origin", "current_status", "review_status", "is_published", "company")
    search_fields = ("title", "success_condition", "evidence_text", "company__name")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (StrategyMilestoneStatusUpdateInline, StrategyMilestoneDependencyInline)


admin.site.register(StrategyMilestoneStatusUpdate)
admin.site.register(StrategyMilestoneDependency)


class CapitalAllocationItemInline(admin.TabularInline):
    model = CapitalAllocationItem
    extra = 0
    readonly_fields = ("source_fact", "source_document")


@admin.register(CapitalAllocationPeriod)
class CapitalAllocationPeriodAdmin(admin.ModelAdmin):
    list_display = ("company", "fiscal_period", "fiscal_year", "period_end", "total_deployment", "operating_cash_flow", "review_status", "is_published")
    list_filter = ("fiscal_period", "cadence", "review_status", "is_published", "company")
    search_fields = ("company__name", "accession_number", "headline", "calculation_note")
    inlines = (CapitalAllocationItemInline,)


@admin.register(CapitalAllocationItem)
class CapitalAllocationItemAdmin(admin.ModelAdmin):
    list_display = ("period", "category", "label", "value", "unit", "is_context", "is_calculated", "review_status")
    list_filter = ("category", "is_context", "is_calculated", "review_status", "period__company")
    search_fields = ("period__company__name", "label", "concept", "evidence_text")

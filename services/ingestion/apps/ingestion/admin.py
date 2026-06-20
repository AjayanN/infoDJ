from __future__ import annotations

from django.contrib import admin

from apps.curation.admin_helpers import (
    register_planned_model,
    source_status_action,
)
from apps.ingestion.services.url_utils import apply_source_hashes
from apps.ingestion.models import FinancialFact, MarketPrice, SourceGap, SourceGapResolutionCandidate


class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "source_api",
        "publisher",
        "language",
        "published_date",
        "status",
        "duplicate_of",
        "updated_at",
    )
    list_filter = (
        "company",
        "source_api",
        "publisher",
        "language",
        "status",
        "published_date",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "title",
        "url",
        "canonical_url",
        "publisher",
        "snippet",
        "url_hash",
        "title_hash",
    )
    readonly_fields = ("url_hash", "title_hash", "created_at", "updated_at")
    autocomplete_fields = ("company", "duplicate_of")
    date_hierarchy = "published_date"
    ordering = ("-published_date", "-created_at")
    actions = (
        source_status_action("APPROVED", "Mark selected sources as approved"),
        source_status_action("IGNORED", "Mark selected sources as ignored"),
        source_status_action("EXTRACTION_PENDING", "Queue selected sources for extraction"),
        "recalculate_hashes",
    )

    @admin.action(description="Recalculate selected source hashes")
    def recalculate_hashes(self, request, queryset):
        updated = 0
        for source in queryset:
            apply_source_hashes(source)
            source.save(update_fields=["canonical_url", "url_hash", "title_hash", "updated_at"])
            updated += 1
        self.message_user(request, f"Recalculated hashes for {updated} source documents.")


class ArticleExtractionAdmin(admin.ModelAdmin):
    list_display = (
        "source_title",
        "publisher",
        "extraction_status",
        "word_count",
        "extractor_name",
        "updated_at",
    )
    list_filter = (
        "extraction_status",
        "extractor_name",
        "source_document__company",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "source_document__title",
        "source_document__url",
        "source_document__publisher",
        "clean_text",
        "extraction_error",
    )
    readonly_fields = ("created_at", "updated_at", "clean_text_preview")
    autocomplete_fields = ("source_document",)
    ordering = ("-updated_at",)

    @admin.display(description="Source title", ordering="source_document__title")
    def source_title(self, obj):
        return obj.source_document.title

    @admin.display(description="Publisher", ordering="source_document__publisher")
    def publisher(self, obj):
        return obj.source_document.publisher

    @admin.display(description="Clean text preview")
    def clean_text_preview(self, obj):
        text = obj.clean_text or ""
        return text[:600]


class IngestionJobAdmin(admin.ModelAdmin):
    list_display = (
        "job_type",
        "company",
        "source",
        "status",
        "sources_found",
        "sources_inserted",
        "duplicates_skipped",
        "articles_extracted",
        "events_extracted",
        "created_at",
    )
    list_filter = ("job_type", "company", "source", "status", "created_at", "started_at", "finished_at")
    search_fields = ("query", "source", "error_message", "company__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company",)
    ordering = ("-created_at",)


class SourceGapAdmin(admin.ModelAdmin):
    list_display = (
        "dashboard",
        "gap_type",
        "company",
        "provider",
        "status",
        "updated_at",
    )
    list_filter = ("dashboard", "gap_type", "provider", "status", "company", "created_at", "updated_at")
    search_fields = ("reason", "next_ingestion_task", "provider", "company__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company",)
    ordering = ("dashboard", "gap_type", "company")


class SourceGapResolutionCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "dashboard",
        "gap_type",
        "company",
        "candidate_type",
        "confidence_score",
        "review_status",
        "updated_at",
    )
    list_filter = ("dashboard", "gap_type", "candidate_type", "review_status", "company", "created_at", "updated_at")
    search_fields = ("evidence_text", "next_action", "company__name", "source_document__title", "source_document__url")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company", "source_gap", "source_document")
    ordering = ("dashboard", "gap_type", "company", "-confidence_score")


class MarketPriceAdmin(admin.ModelAdmin):
    list_display = ("company", "ticker", "provider", "price_date", "close_price", "volume", "updated_at")
    list_filter = ("provider", "ticker", "company", "price_date", "created_at", "updated_at")
    search_fields = ("company__name", "ticker", "provider")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company",)
    date_hierarchy = "price_date"
    ordering = ("company", "-price_date")


class FinancialFactAdmin(admin.ModelAdmin):
    list_display = ("company", "concept", "unit", "fy", "fp", "filed", "value", "updated_at")
    list_filter = ("taxonomy", "concept", "unit", "fy", "fp", "company", "filed", "created_at", "updated_at")
    search_fields = ("company__name", "concept", "label", "accession_number", "frame")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company",)
    date_hierarchy = "filed"
    ordering = ("company", "concept", "-fy", "-filed")


register_planned_model("ingestion", "SourceDocument", SourceDocumentAdmin)
register_planned_model("ingestion", "ArticleExtraction", ArticleExtractionAdmin)
register_planned_model("ingestion", "IngestionJob", IngestionJobAdmin)
register_planned_model("ingestion", "SourceGap", SourceGapAdmin)
register_planned_model("ingestion", "SourceGapResolutionCandidate", SourceGapResolutionCandidateAdmin)
register_planned_model("ingestion", "MarketPrice", MarketPriceAdmin)
register_planned_model("ingestion", "FinancialFact", FinancialFactAdmin)

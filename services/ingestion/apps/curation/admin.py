from __future__ import annotations

from django.contrib import admin

from apps.curation.admin_helpers import (
    register_planned_model,
    review_status_action,
)


class StrategicTurnSourceInline(admin.TabularInline):
    extra = 0
    autocomplete_fields = ("source_document", "business_event")
    fields = ("source_document", "business_event", "evidence_text", "created_at")
    readonly_fields = ("created_at",)

    def has_registered_model(self):
        return self.model is not None


class BusinessEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "decision_theme",
        "company",
        "event_date",
        "lifecycle_stage",
        "review_status",
        "confidence_score",
        "updated_at",
    )
    list_filter = (
        "company",
        "event_type",
        "decision_theme",
        "lifecycle_stage",
        "review_status",
        "event_date",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "company__name",
        "source_document__title",
        "before_state",
        "after_state",
        "trigger",
        "decision",
        "decision_theme",
        "source_claim",
        "actual_change",
        "outcome",
        "evidence_text",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company", "source_document", "article_extraction")
    date_hierarchy = "event_date"
    ordering = ("-event_date", "-created_at")
    actions = (
        review_status_action("NEEDS_REVIEW", "Mark selected events as needing review"),
        review_status_action("APPROVED", "Approve selected events"),
        review_status_action("REJECTED", "Reject selected events"),
    )


class StrategicTurnAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "turn_type",
        "start_date",
        "end_date",
        "review_status",
        "is_published",
        "confidence_score",
        "updated_at",
    )
    list_filter = (
        "company",
        "turn_type",
        "lifecycle_stage",
        "review_status",
        "is_published",
        "start_date",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "title",
        "company__name",
        "summary",
        "before_state",
        "after_state",
        "trigger",
        "decision",
        "outcome",
        "founder_lesson",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company",)
    date_hierarchy = "start_date"
    ordering = ("-start_date", "-created_at")
    actions = (
        review_status_action("NEEDS_REVIEW", "Mark selected turns as needing review"),
        review_status_action("APPROVED", "Approve selected turns"),
        review_status_action("REJECTED", "Reject selected turns"),
        review_status_action("MERGED", "Mark selected turns as merged"),
        "publish_selected",
        "unpublish_selected",
    )

    @admin.action(description="Publish selected turns")
    def publish_selected(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"Published {updated} strategic turns.")

    @admin.action(description="Unpublish selected turns")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Unpublished {updated} strategic turns.")


class StrategicTurnSourceAdmin(admin.ModelAdmin):
    list_display = ("strategic_turn", "source_document", "business_event", "created_at")
    list_filter = ("strategic_turn__company", "created_at")
    search_fields = (
        "strategic_turn__title",
        "source_document__title",
        "source_document__url",
        "business_event__decision",
        "evidence_text",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("strategic_turn", "source_document", "business_event")
    ordering = ("-created_at",)


BusinessEvent = register_planned_model("curation", "BusinessEvent", BusinessEventAdmin)
StrategicTurn = register_planned_model("curation", "StrategicTurn", StrategicTurnAdmin)
StrategicTurnSource = register_planned_model(
    "curation",
    "StrategicTurnSource",
    StrategicTurnSourceAdmin,
)

if StrategicTurn is not None and StrategicTurnSource is not None:
    StrategicTurnSourceInline.model = StrategicTurnSource
    StrategicTurnAdmin.inlines = (StrategicTurnSourceInline,)

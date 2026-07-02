from django.contrib import admin

from apps.theses.models import StrategyThesis, ThesisEvidence, ThesisIndicator, ThesisMilestone, ThesisRevision


class ThesisEvidenceInline(admin.TabularInline):
    model = ThesisEvidence
    extra = 0


class ThesisMilestoneInline(admin.TabularInline):
    model = ThesisMilestone
    extra = 0


class ThesisIndicatorInline(admin.TabularInline):
    model = ThesisIndicator
    extra = 0


@admin.register(StrategyThesis)
class StrategyThesisAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "company_slug", "state", "confidence_score", "is_shared", "updated_at")
    list_filter = ("state", "is_shared")
    search_fields = ("title", "statement", "company_slug", "company_name", "owner__username", "owner__email")
    inlines = (ThesisEvidenceInline, ThesisMilestoneInline, ThesisIndicatorInline)


@admin.register(ThesisRevision)
class ThesisRevisionAdmin(admin.ModelAdmin):
    list_display = ("thesis", "changed_by", "new_state", "new_confidence_score", "created_at")
    list_filter = ("new_state",)
    search_fields = ("thesis__title", "changed_by__username", "reason")

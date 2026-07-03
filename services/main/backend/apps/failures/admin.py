from django.contrib import admin

from apps.failures.models import FailureEvidence, FailureRelatedLink, FailureReview, FailureWarningSign, StrategyFailureCase


class FailureEvidenceInline(admin.TabularInline):
    model = FailureEvidence
    extra = 0


class FailureWarningSignInline(admin.TabularInline):
    model = FailureWarningSign
    extra = 0


class FailureRelatedLinkInline(admin.TabularInline):
    model = FailureRelatedLink
    extra = 0


class FailureReviewInline(admin.TabularInline):
    model = FailureReview
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(StrategyFailureCase)
class StrategyFailureCaseAdmin(admin.ModelAdmin):
    list_display = ("title", "company_slug", "category", "classification", "editorial_status", "is_published", "updated_at")
    list_filter = ("category", "classification", "stage", "editorial_status", "is_published")
    search_fields = ("title", "company_name", "decision_context", "lessons")
    inlines = [FailureEvidenceInline, FailureWarningSignInline, FailureRelatedLinkInline, FailureReviewInline]

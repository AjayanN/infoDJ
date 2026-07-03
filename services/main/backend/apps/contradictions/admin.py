from django.contrib import admin

from apps.contradictions.models import ContradictionCase, ContradictionClaim, ContradictionResolution


class ContradictionClaimInline(admin.TabularInline):
    model = ContradictionClaim
    extra = 0


@admin.register(ContradictionCase)
class ContradictionCaseAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "company_slug", "category", "conflict_type", "review_label", "materiality", "is_published")
    list_filter = ("category", "conflict_type", "review_label", "materiality", "is_published")
    search_fields = ("title", "neutral_summary", "company_slug", "company_name", "owner__username")
    inlines = (ContradictionClaimInline,)


admin.site.register(ContradictionResolution)

from django.contrib import admin

from apps.scenarios.models import (
    ScenarioActualResult,
    ScenarioAssumption,
    ScenarioCase,
    ScenarioIndicator,
    ScenarioRevision,
    ScenarioSet,
)


class ScenarioCaseInline(admin.TabularInline):
    model = ScenarioCase
    extra = 0


class ScenarioIndicatorInline(admin.TabularInline):
    model = ScenarioIndicator
    extra = 0


@admin.register(ScenarioSet)
class ScenarioSetAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "company_slug", "status", "source_type", "updated_at")
    list_filter = ("status", "source_type", "is_shared")
    search_fields = ("title", "company_slug", "company_name", "thesis", "owner__username")
    inlines = (ScenarioCaseInline, ScenarioIndicatorInline)


admin.site.register(ScenarioAssumption)
admin.site.register(ScenarioActualResult)
admin.site.register(ScenarioRevision)

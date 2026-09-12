from django.contrib import admin
from apps.history.models import ConnectorCursor, ResearchSubject, SourceConnectorConfig, SubjectSource

@admin.register(SourceConnectorConfig)
class SourceConnectorConfigAdmin(admin.ModelAdmin):
    list_display = ("connector_key", "enabled", "allowed_domain", "owner", "requests_per_minute", "coverage_start", "coverage_end", "updated_at")
    list_filter = ("enabled", "allowed_domain", "coverage_start", "coverage_end")
    search_fields = ("connector_key", "endpoint", "allowed_domain", "owner", "secret_env_reference")
    readonly_fields = ("created_at", "updated_at")
    fields = ("connector_key", "schema_version", "endpoint", "allowed_domain", "enabled", "owner", "secret_env_reference", "coverage_tracks", "coverage_start", "coverage_end", "requests_per_minute", "monthly_cost_limit", "created_at", "updated_at")

@admin.register(ResearchSubject)
class ResearchSubjectAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "kind", "company", "parent_subject", "created_at")
    list_filter = ("kind",)
    search_fields = ("canonical_name", "aliases__alias", "identifiers__external_id")
    autocomplete_fields = ("company", "parent_subject")
    readonly_fields = ("created_at",)

@admin.register(SubjectSource)
class SubjectSourceAdmin(admin.ModelAdmin):
    list_display = ("subject", "connector", "external_reference", "enabled")
    list_filter = ("enabled", "connector")
    search_fields = ("subject__canonical_name", "connector__connector_key", "external_reference")
    autocomplete_fields = ("subject", "connector")

@admin.register(ConnectorCursor)
class ConnectorCursorAdmin(admin.ModelAdmin):
    list_display = ("subject_source", "last_success_at", "updated_at")
    list_filter = ("last_success_at",)
    search_fields = ("subject_source__subject__canonical_name", "subject_source__connector__connector_key", "last_error")
    readonly_fields = ("updated_at",)
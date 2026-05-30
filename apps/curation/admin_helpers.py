from __future__ import annotations

from django.apps import apps
from django.contrib import admin, messages


def get_planned_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def register_planned_model(app_label: str, model_name: str, admin_class):
    model = get_planned_model(app_label, model_name)
    if model is None:
        return None

    try:
        admin.site.register(model, admin_class)
    except admin.sites.AlreadyRegistered:
        pass
    return model


def set_field_value(modeladmin, request, queryset, field_name: str, value: str):
    updated = queryset.update(**{field_name: value})
    modeladmin.message_user(
        request,
        f"Updated {updated} {queryset.model._meta.verbose_name_plural}.",
        messages.SUCCESS,
    )


def source_status_action(status: str, label: str):
    def action(modeladmin, request, queryset):
        set_field_value(modeladmin, request, queryset, "status", status)

    action.short_description = label
    action.__name__ = f"mark_sources_{status.lower()}"
    return action


def review_status_action(status: str, label: str):
    def action(modeladmin, request, queryset):
        set_field_value(modeladmin, request, queryset, "review_status", status)

    action.short_description = label
    action.__name__ = f"mark_review_{status.lower()}"
    return action

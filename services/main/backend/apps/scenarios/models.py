from __future__ import annotations

from django.conf import settings
from django.db import models


class ScenarioSetStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    REVIEWING = "REVIEWING", "Reviewing"
    COMPLETED = "COMPLETED", "Completed"
    ARCHIVED = "ARCHIVED", "Archived"


class ScenarioKind(models.TextChoices):
    BEST = "BEST", "Best case"
    BASE = "BASE", "Base case"
    WORST = "WORST", "Worst case"


class ScenarioSourceType(models.TextChoices):
    USER_CREATED = "USER_CREATED", "User-created"
    INFODJ_REVIEWED = "INFODJ_REVIEWED", "InfoDJ reviewed"


class ScenarioDriverType(models.TextChoices):
    KPI = "KPI", "KPI"
    MACRO_FACTOR = "MACRO_FACTOR", "Macro factor"
    PROMISE = "PROMISE", "Management promise"
    MILESTONE = "MILESTONE", "Strategy milestone"
    RISK = "RISK", "Risk"
    COMPETITIVE = "COMPETITIVE", "Competitive factor"
    REGULATORY = "REGULATORY", "Regulatory factor"
    OTHER = "OTHER", "Other"


class ScenarioIndicatorStatus(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Not started"
    ON_TRACK = "ON_TRACK", "On track"
    WATCH = "WATCH", "Watch"
    OFF_TRACK = "OFF_TRACK", "Off track"
    UNKNOWN = "UNKNOWN", "Unknown"


class ScenarioSet(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scenario_sets")
    title = models.CharField(max_length=255)
    company_slug = models.SlugField(max_length=255, blank=True, db_index=True)
    company_name = models.CharField(max_length=255, blank=True)
    thesis = models.TextField(blank=True)
    horizon_start = models.DateField(null=True, blank=True)
    horizon_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=ScenarioSetStatus.choices, default=ScenarioSetStatus.DRAFT, db_index=True)
    source_type = models.CharField(max_length=32, choices=ScenarioSourceType.choices, default=ScenarioSourceType.USER_CREATED, db_index=True)
    non_prediction_note = models.TextField(
        default="Scenarios are assumption workspaces, not predictions, investment advice, or probability-weighted forecasts."
    )
    is_shared = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "company_slug"], name="scenario_owner_company_idx"),
            models.Index(fields=["owner", "status"], name="scenario_owner_status_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class ScenarioCase(models.Model):
    scenario_set = models.ForeignKey(ScenarioSet, on_delete=models.CASCADE, related_name="cases")
    kind = models.CharField(max_length=16, choices=ScenarioKind.choices, db_index=True)
    title = models.CharField(max_length=255)
    narrative = models.TextField()
    qualitative_outcome = models.TextField(blank=True)
    low_value = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    high_value = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=64, blank=True)
    probability_label = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind"]
        constraints = [models.UniqueConstraint(fields=["scenario_set", "kind"], name="unique_scenario_kind")]

    def __str__(self) -> str:
        return self.title


class ScenarioAssumption(models.Model):
    scenario_case = models.ForeignKey(ScenarioCase, on_delete=models.CASCADE, related_name="assumptions")
    driver_type = models.CharField(max_length=32, choices=ScenarioDriverType.choices, db_index=True)
    driver_label = models.CharField(max_length=255)
    assumption = models.TextField()
    rationale = models.TextField(blank=True)
    evidence_type = models.CharField(max_length=64, blank=True)
    evidence_id = models.CharField(max_length=255, blank=True)
    evidence_label = models.CharField(max_length=255, blank=True)
    evidence_url = models.URLField(blank=True)
    confidence_label = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["driver_type", "driver_label"]


class ScenarioIndicator(models.Model):
    scenario_set = models.ForeignKey(ScenarioSet, on_delete=models.CASCADE, related_name="indicators")
    name = models.CharField(max_length=255)
    driver_type = models.CharField(max_length=32, choices=ScenarioDriverType.choices, default=ScenarioDriverType.OTHER)
    target = models.CharField(max_length=255, blank=True)
    current_value = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=ScenarioIndicatorStatus.choices, default=ScenarioIndicatorStatus.UNKNOWN, db_index=True)
    source_hint = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]


class ScenarioActualResult(models.Model):
    scenario_set = models.ForeignKey(ScenarioSet, on_delete=models.CASCADE, related_name="actual_results")
    result_date = models.DateField()
    metric_label = models.CharField(max_length=255)
    actual_value = models.CharField(max_length=255)
    comparison_note = models.TextField()
    evidence_label = models.CharField(max_length=255, blank=True)
    evidence_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-result_date", "-id"]


class ScenarioRevision(models.Model):
    scenario_set = models.ForeignKey(ScenarioSet, on_delete=models.CASCADE, related_name="revisions")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scenario_revisions")
    previous_status = models.CharField(max_length=32, choices=ScenarioSetStatus.choices, blank=True)
    new_status = models.CharField(max_length=32, choices=ScenarioSetStatus.choices)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

from django.urls import path

from apps.failures import api


urlpatterns = [
    path("strategy-failures", api.failure_cases, name="app-strategy-failures"),
    path("strategy-failures/evidence-suggestions", api.failure_evidence_suggestions, name="app-strategy-failure-evidence-suggestions"),
    path("strategy-failures/<int:case_id>", api.failure_detail, name="app-strategy-failure-detail"),
    path("strategy-failures/<int:case_id>/evidence", api.failure_evidence, name="app-strategy-failure-evidence"),
    path("strategy-failures/<int:case_id>/warning-signs", api.failure_warning_signs, name="app-strategy-failure-warning-signs"),
    path("strategy-failures/<int:case_id>/related-links", api.failure_related_links, name="app-strategy-failure-related-links"),
    path("strategy-failures/<int:case_id>/review", api.failure_review, name="app-strategy-failure-review"),
]

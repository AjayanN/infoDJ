from django.urls import path

from apps.contradictions import api


urlpatterns = [
    path("contradictions", api.contradiction_cases, name="app-contradictions"),
    path("contradictions/evidence-suggestions", api.contradiction_evidence_suggestions, name="app-contradiction-evidence-suggestions"),
    path("contradictions/<int:case_id>", api.contradiction_detail, name="app-contradiction-detail"),
    path("contradictions/<int:case_id>/claims", api.contradiction_claims, name="app-contradiction-claims"),
    path("contradictions/<int:case_id>/review", api.contradiction_review, name="app-contradiction-review"),
]

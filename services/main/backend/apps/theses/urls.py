from django.urls import path

from apps.theses import api


urlpatterns = [
    path("theses", api.theses, name="app-theses"),
    path("theses/evidence-suggestions", api.evidence_suggestions, name="app-thesis-evidence-suggestions"),
    path("theses/<int:thesis_id>", api.thesis_detail, name="app-thesis-detail"),
    path("theses/<int:thesis_id>/evidence", api.thesis_evidence, name="app-thesis-evidence"),
    path("theses/<int:thesis_id>/evidence/<int:evidence_id>", api.thesis_evidence_detail, name="app-thesis-evidence-detail"),
    path("theses/<int:thesis_id>/milestones", api.thesis_milestones, name="app-thesis-milestones"),
    path("theses/<int:thesis_id>/indicators", api.thesis_indicators, name="app-thesis-indicators"),
    path("theses/<int:thesis_id>/confidence", api.thesis_confidence, name="app-thesis-confidence"),
]

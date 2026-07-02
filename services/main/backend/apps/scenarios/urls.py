from django.urls import path

from apps.scenarios import api


urlpatterns = [
    path("scenarios", api.scenario_sets, name="app-scenarios"),
    path("scenarios/evidence-suggestions", api.scenario_evidence_suggestions, name="app-scenario-evidence-suggestions"),
    path("scenarios/<int:scenario_id>", api.scenario_detail, name="app-scenario-detail"),
    path("scenarios/<int:scenario_id>/cases/<int:case_id>", api.scenario_case_detail, name="app-scenario-case-detail"),
    path("scenarios/<int:scenario_id>/cases/<int:case_id>/assumptions", api.scenario_assumptions, name="app-scenario-assumptions"),
    path("scenarios/<int:scenario_id>/indicators", api.scenario_indicators, name="app-scenario-indicators"),
    path("scenarios/<int:scenario_id>/actual-results", api.scenario_actual_results, name="app-scenario-actual-results"),
]

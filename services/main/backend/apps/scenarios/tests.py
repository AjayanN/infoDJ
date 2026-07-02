from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.scenarios.models import ScenarioSet


class ScenarioExplorerApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("scenariouser", "scenario@example.com", "StrongPass123!")
        self.other_user = get_user_model().objects.create_user("otherscenario", "other@example.com", "StrongPass123!")
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_scenarios_require_authentication(self):
        response = APIClient().get("/api/app/scenarios")

        self.assertEqual(response.status_code, 401)

    def test_create_scenario_set_scaffolds_three_cases_and_guardrail(self):
        response = self.client.post(
            "/api/app/scenarios",
            {
                "title": "Netflix ad tier scenarios",
                "company_slug": "netflix",
                "company_name": "Netflix",
                "thesis": "Ad tier economics may change revenue mix.",
                "horizon_start": "2026-01-01",
                "horizon_end": "2026-12-31",
                "status": "ACTIVE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["scenario_set"]
        self.assertEqual({row["kind"] for row in payload["cases"]}, {"BEST", "BASE", "WORST"})
        self.assertEqual(payload["source_type"], "USER_CREATED")
        self.assertIn("not predictions", payload["non_prediction_note"])
        self.assertEqual(payload["revisions"][0]["reason"], "Scenario set created.")

    def test_visibility_is_scoped_to_owner(self):
        ScenarioSet.objects.create(owner=self.other_user, title="Other private scenario")

        response = self.client.get("/api/app/scenarios")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scenario_sets"], [])

    def test_assumptions_differences_indicators_status_and_actuals(self):
        scenario = self.client.post("/api/app/scenarios", {"title": "Disney scenario", "company_slug": "disney"}, format="json").json()["scenario_set"]
        cases = {row["kind"]: row["id"] for row in scenario["cases"]}

        for kind, text in {"BEST": "Streaming margins expand quickly.", "BASE": "Streaming margins expand gradually.", "WORST": "Streaming margins remain pressured."}.items():
            response = self.client.post(
                f"/api/app/scenarios/{scenario['id']}/cases/{cases[kind]}/assumptions",
                {
                    "driver_type": "KPI",
                    "driver_label": "Streaming margin",
                    "assumption": text,
                    "evidence_type": "KPI",
                    "evidence_label": "Operating KPI dashboard",
                    "confidence_label": "medium",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201)

        detail = self.client.get(f"/api/app/scenarios/{scenario['id']}").json()["scenario_set"]
        self.assertEqual(len(detail["differences"]), 1)
        self.assertEqual(detail["differences"][0]["driver_label"], "Streaming margin")

        indicator = self.client.post(
            f"/api/app/scenarios/{scenario['id']}/indicators",
            {"name": "Margin trend", "driver_type": "KPI", "target": "Improving", "current_value": "Under review", "status": "WATCH"},
            format="json",
        )
        self.assertEqual(indicator.status_code, 201)
        self.assertEqual(indicator.json()["indicator"]["status"], "WATCH")

        actual = self.client.post(
            f"/api/app/scenarios/{scenario['id']}/actual-results",
            {"result_date": "2026-12-31", "metric_label": "Streaming margin", "actual_value": "Improved", "comparison_note": "Actual result aligned most closely with base case."},
            format="json",
        )
        self.assertEqual(actual.status_code, 201)

        status = self.client.patch(f"/api/app/scenarios/{scenario['id']}", {"status": "COMPLETED", "reason": "Horizon ended."}, format="json")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["scenario_set"]["revisions"][0]["new_status"], "COMPLETED")

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.scenarios.api.requests.get")
    def test_evidence_suggestions_use_ingestion_search(self, get):
        get.return_value = json_response(
            {
                "results": {
                    "companies": [{"id": 1, "name": "Netflix", "slug": "netflix", "sector": "Communication Services"}],
                    "events": [{"id": 10, "company_slug": "netflix", "event_type": "PRICE_CHANGE", "actual_change": "Price changed."}],
                    "strategic_turns": [],
                }
            }
        )

        response = self.client.get("/api/app/scenarios/evidence-suggestions?q=netflix&company=netflix")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/search")
        self.assertEqual(response.json()["suggestions"][0]["evidence_type"], "COMPANY")
        self.assertEqual(response.json()["suggestions"][1]["evidence_type"], "EVENT")


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

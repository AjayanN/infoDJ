from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.failures.models import EditorialStatus, StrategyFailureCase


class StrategyFailureLibraryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("failureuser", "failure@example.com", "StrongPass123!")
        self.other_user = get_user_model().objects.create_user("otherfailure", "otherfailure@example.com", "StrongPass123!")
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_failures_require_authentication(self):
        response = APIClient().get("/api/app/strategy-failures")

        self.assertEqual(response.status_code, 401)

    def test_create_case_study_with_evidence_warning_and_links(self):
        response = self.client.post(
            "/api/app/strategy-failures",
            {
                "title": "Failed expansion case",
                "company_slug": "netflix",
                "company_name": "Netflix",
                "sector": "Communication Services",
                "category": "FAILED_MARKET_EXPANSION",
                "classification": "PARTIAL_FAILURE",
                "stage": "OUTCOME_REVIEW",
                "decision_date": "2024-01-01",
                "review_start": "2024-01-01",
                "review_end": "2026-01-01",
                "minimum_evidence": "At least one management source and one outcome source.",
                "elapsed_time_definition": "Two years after launch.",
                "decision_context": "Management entered a new market.",
                "management_rationale": "Management expected a larger addressable market.",
                "original_thesis": "Expansion would increase growth.",
                "expected_result": "Meaningful adoption.",
                "execution_issue": "Adoption lagged the plan.",
                "outcome_definition": "Underperformance versus stated adoption target.",
                "actual_outcome": "Adoption remained below target.",
                "counterexamples": "Some regions performed better.",
                "lessons": "Review local demand before scaling.",
                "correction_path": "Allow corrections with new evidence.",
                "evidence": [{"label": "Annual report", "summary": "Outcome source.", "evidence_date": "2026-02-01"}],
                "warning_signs": [{"signal": "Early adoption slowdown", "why_it_mattered": "Observable before full scale.", "signal_date": "2024-06-01"}],
                "related_links": [{"feature_type": "MILESTONE", "object_label": "Expansion milestone", "relationship_note": "Milestone slipped."}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        case = response.json()["case"]
        self.assertEqual(case["evidence_count"], 1)
        self.assertEqual(case["warning_sign_count"], 1)
        self.assertEqual(case["quality"]["ready_for_review"], True)
        self.assertIn("editorial review before publication", case["guardrail_note"])
        self.assertEqual(case["related_links"][0]["feature_type"], "MILESTONE")

    def test_visibility_is_scoped_to_owner(self):
        StrategyFailureCase.objects.create(
            owner=self.other_user,
            title="Other failure",
            category="EXECUTION_BREAKDOWN",
            decision_context="Private case.",
        )

        response = self.client.get("/api/app/strategy-failures")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cases"], [])

    def test_review_requires_evidence_period_and_reviewed_status_before_publication(self):
        case = StrategyFailureCase.objects.create(
            owner=self.user,
            title="Draft case",
            category="EXECUTION_BREAKDOWN",
            minimum_evidence="Need sources.",
            outcome_definition="Outcome definition.",
            review_start="2024-01-01",
            review_end="2026-01-01",
        )

        unready = self.client.post(
            f"/api/app/strategy-failures/{case.id}/review",
            {"editorial_status": "REVIEWED", "classification": "FAILURE", "is_published": True, "note": "Reviewed but missing evidence."},
            format="json",
        )
        self.assertEqual(unready.status_code, 200)
        self.assertFalse(unready.json()["case"]["is_published"])

        self.client.post(f"/api/app/strategy-failures/{case.id}/evidence", {"label": "10-K", "summary": "Outcome evidence."}, format="json")
        self.client.post(f"/api/app/strategy-failures/{case.id}/warning-signs", {"signal": "Missed milestone", "why_it_mattered": "Observable early."}, format="json")
        ready = self.client.post(
            f"/api/app/strategy-failures/{case.id}/review",
            {"editorial_status": "REVIEWED", "classification": "FAILURE", "is_published": True, "note": "Evidence and warning signs present."},
            format="json",
        )

        self.assertEqual(ready.status_code, 200)
        self.assertTrue(ready.json()["case"]["is_published"])
        self.assertEqual(ready.json()["review"]["previous_status"], EditorialStatus.REVIEWED)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.failures.api.requests.get")
    def test_evidence_suggestions_use_ingestion_search(self, get):
        get.return_value = json_response(
            {
                "results": {
                    "companies": [{"id": 1, "name": "Netflix", "slug": "netflix", "sector": "Communication Services"}],
                    "events": [{"id": 10, "company_slug": "netflix", "event_type": "EXPANSION", "actual_change": "Expansion slowed."}],
                    "strategic_turns": [],
                }
            }
        )

        response = self.client.get("/api/app/strategy-failures/evidence-suggestions?q=netflix&company=netflix")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/search")
        self.assertEqual(response.json()["suggestions"][0]["evidence_type"], "COMPANY")
        self.assertEqual(response.json()["suggestions"][1]["evidence_type"], "EVENT")


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

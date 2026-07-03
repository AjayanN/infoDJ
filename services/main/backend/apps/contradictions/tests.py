from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.contradictions.models import ContradictionCase


class ContradictionViewApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("contraduser", "contrad@example.com", "StrongPass123!")
        self.other_user = get_user_model().objects.create_user("othercontrad", "other@example.com", "StrongPass123!")
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_contradictions_require_authentication(self):
        response = APIClient().get("/api/app/contradictions")

        self.assertEqual(response.status_code, 401)

    def test_create_case_with_two_neutral_claims(self):
        response = self.client.post(
            "/api/app/contradictions",
            {
                "title": "Guidance versus later result",
                "company_slug": "netflix",
                "company_name": "Netflix",
                "category": "GUIDANCE_VS_ACTUAL",
                "conflict_type": "CONTRADICTION",
                "materiality": "HIGH",
                "confidence_score": "72",
                "neutral_summary": "Two sourced claims appear to differ and require review.",
                "claims": [
                    {"label": "Earlier guidance", "claim_text": "Management expected growth.", "claim_date": "2026-01-01", "speaker": "CFO", "scope": "FY2026", "source_label": "Earnings call"},
                    {"label": "Later result", "claim_text": "Reported growth was lower.", "claim_date": "2026-04-01", "source_label": "10-Q"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        case = response.json()["case"]
        self.assertEqual(len(case["claims"]), 2)
        self.assertEqual(case["review_label"], "UNREVIEWED")
        self.assertTrue(case["human_review_required"])
        self.assertIn("must not imply deception", case["neutrality_note"])

    def test_visibility_is_scoped_to_owner(self):
        ContradictionCase.objects.create(
            owner=self.other_user,
            title="Other case",
            category="SOURCE_VS_SOURCE",
            neutral_summary="Private case",
        )

        response = self.client.get("/api/app/contradictions")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cases"], [])

    def test_review_required_before_publication(self):
        case = ContradictionCase.objects.create(
            owner=self.user,
            title="Apparent conflict",
            category="SOURCE_VS_SOURCE",
            neutral_summary="Needs review.",
        )

        unreviewed = self.client.post(
            f"/api/app/contradictions/{case.id}/review",
            {"review_label": "UNREVIEWED", "is_published": True, "explanation": "Still unreviewed."},
            format="json",
        )
        self.assertEqual(unreviewed.status_code, 200)
        self.assertFalse(unreviewed.json()["case"]["is_published"])

        reviewed = self.client.post(
            f"/api/app/contradictions/{case.id}/review",
            {"review_label": "APPARENT_CONFLICT", "conflict_type": "CLARIFICATION", "is_published": True, "explanation": "Scope changed, so label stays neutral."},
            format="json",
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertTrue(reviewed.json()["case"]["is_published"])
        self.assertEqual(reviewed.json()["resolution"]["previous_label"], "UNREVIEWED")

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.contradictions.api.requests.get")
    def test_evidence_suggestions_use_ingestion_search(self, get):
        get.return_value = json_response(
            {
                "results": {
                    "companies": [{"id": 1, "name": "Netflix", "slug": "netflix", "sector": "Communication Services"}],
                    "events": [{"id": 10, "company_slug": "netflix", "event_type": "GUIDANCE", "actual_change": "Guidance changed."}],
                    "strategic_turns": [],
                }
            }
        )

        response = self.client.get("/api/app/contradictions/evidence-suggestions?q=netflix&company=netflix")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/search")
        self.assertEqual(response.json()["suggestions"][0]["source_type"], "COMPANY")
        self.assertEqual(response.json()["suggestions"][1]["source_type"], "EVENT")


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

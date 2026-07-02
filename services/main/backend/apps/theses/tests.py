from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.theses.models import StrategyThesis


class StrategyThesisApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="thesisuser",
            email="thesisuser@example.com",
            password="StrongPass123!",
        )
        self.other_user = get_user_model().objects.create_user(
            username="otheruser",
            email="otheruser@example.com",
            password="StrongPass123!",
        )
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_thesis_workspace_requires_authentication(self):
        response = APIClient().get("/api/app/theses")

        self.assertEqual(response.status_code, 401)

    def test_user_can_create_private_falsifiable_thesis(self):
        response = self.client.post(
            "/api/app/theses",
            {
                "title": "Netflix ad tier thesis",
                "company_slug": "netflix",
                "company_name": "Netflix",
                "statement": "Advertising tier growth should expand revenue without raising churn.",
                "state": "ACTIVE",
                "time_horizon": "12 months",
                "review_date": "2026-12-31",
                "confidence_score": "62.5",
                "assumptions": ["Ad load remains tolerable", "Advertiser demand remains healthy"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        thesis = response.json()["thesis"]
        self.assertEqual(thesis["state"], "ACTIVE")
        self.assertEqual(thesis["company_slug"], "netflix")
        self.assertEqual(thesis["privacy_note"], "This is private user-authored analysis unless explicitly shared. User notes are not published InfoDJ facts.")
        self.assertEqual(thesis["revisions"][0]["reason"], "Thesis created.")

    def test_thesis_visibility_is_scoped_to_owner(self):
        StrategyThesis.objects.create(
            owner=self.other_user,
            title="Other thesis",
            statement="Private note",
            company_slug="disney",
        )

        response = self.client.get("/api/app/theses")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["theses"], [])

    def test_evidence_balance_and_user_note_separation(self):
        thesis = StrategyThesis.objects.create(
            owner=self.user,
            title="Caterpillar cycle thesis",
            statement="Dealer demand should recover with construction spend.",
            company_slug="caterpillar",
        )

        response = self.client.post(
            f"/api/app/theses/{thesis.id}/evidence",
            {
                "side": "OPPOSING",
                "evidence_type": "SOURCE",
                "title": "10-K cyclicality disclosure",
                "summary": "Management described cyclical demand exposure.",
                "source_url": "https://example.com/filing",
                "source_date": "2026-02-15",
                "source_payload": {"document": "10-K"},
                "user_note": "This is my concern, not a reviewed fact.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["balance"]["opposing"], 1)
        self.assertEqual(payload["evidence"]["source_payload"], {"document": "10-K"})
        self.assertEqual(payload["evidence"]["user_note"], "This is my concern, not a reviewed fact.")
        self.assertIn("user_note is private user-authored commentary", payload["evidence"]["separation_note"])

    def test_confidence_update_creates_revision_history(self):
        thesis = StrategyThesis.objects.create(
            owner=self.user,
            title="Disney streaming thesis",
            statement="Streaming profitability improves as content spending normalizes.",
            company_slug="disney",
            state="ACTIVE",
            confidence_score="50",
        )

        response = self.client.post(
            f"/api/app/theses/{thesis.id}/confidence",
            {"state": "STRENGTHENING", "confidence_score": "70", "reason": "Latest operating evidence supports margin progress."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revision"]["previous_state"], "ACTIVE")
        self.assertEqual(response.json()["revision"]["new_state"], "STRENGTHENING")
        self.assertEqual(response.json()["thesis"]["confidence_score"], 70.0)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.theses.api.requests.get")
    def test_evidence_suggestions_use_ingestion_search(self, get):
        get.return_value = json_response(
            {
                "results": {
                    "companies": [{"id": 1, "name": "Netflix", "slug": "netflix", "sector": "Communication Services"}],
                    "events": [
                        {
                            "id": 10,
                            "company_slug": "netflix",
                            "event_type": "PRICE_CHANGE",
                            "actual_change": "Plan price changed.",
                            "event_date": "2026-01-01",
                        }
                    ],
                    "strategic_turns": [],
                }
            }
        )

        response = self.client.get("/api/app/theses/evidence-suggestions?q=netflix&company=netflix")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/search")
        self.assertEqual(response.json()["suggestions"][0]["evidence_type"], "COMPANY")
        self.assertEqual(response.json()["suggestions"][1]["evidence_type"], "EVENT")


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

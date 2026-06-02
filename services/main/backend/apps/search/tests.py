from __future__ import annotations

from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


class DashboardSearchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="searchuser",
            email="searchuser@example.com",
            password="StrongPass123!",
        )
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_dashboard_requires_authentication(self):
        client = APIClient()

        response = client.get("/api/app/dashboard")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_dashboard_returns_grouped_sector_counts(self, get):
        get.side_effect = [
            json_response(
                {
                    "companies": [
                        {
                            "name": "Netflix",
                            "slug": "netflix",
                            "sector": "Communication Services",
                            "source_count": 5,
                            "event_count": 7,
                            "strategic_turn_count": 3,
                        },
                        {
                            "name": "Apple",
                            "slug": "apple",
                            "sector": "Information Technology",
                            "source_count": 2,
                            "event_count": 4,
                            "strategic_turn_count": 1,
                        },
                    ]
                }
            ),
            json_response({"jobs": [{"id": 1, "status": "SUCCEEDED"}]}),
        ]

        response = self.client.get("/api/app/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["company_count"], 2)
        self.assertEqual(response.data["summary"]["event_count"], 11)
        self.assertEqual(response.data["sector_counts"][0]["sector"], "Communication Services")
        self.assertEqual(response.data["latest_jobs"][0]["status"], "SUCCEEDED")

    @patch("apps.search.api.requests.get")
    def test_dashboard_handles_ingestion_failure(self, get):
        get.side_effect = requests.RequestException("network unavailable")

        response = self.client.get("/api/app/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["ingestion"]["available"])
        self.assertEqual(response.data["summary"]["company_count"], 0)

    def test_search_requires_query(self):
        response = self.client.get("/api/app/search")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "q is required")

    @patch("apps.search.api.requests.get")
    def test_search_proxies_grouped_results(self, get):
        get.return_value = json_response(
            {
                "query": "netflix",
                "language": "en",
                "results": {
                    "companies": [{"name": "Netflix", "slug": "netflix"}],
                    "events": [{"id": 10, "actual_change": "Netflix introduced an ad-supported plan."}],
                    "strategic_turns": [{"id": 2, "title": "Netflix advertising turn"}],
                },
            }
        )

        response = self.client.get("/api/app/search?q=netflix")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], "en")
        self.assertEqual(response.data["results"]["companies"][0]["slug"], "netflix")

    @patch("apps.search.api.requests.get")
    def test_search_suggest_proxies_suggestions(self, get):
        get.return_value = json_response(
            {
                "query": "net",
                "language": "en",
                "suggestions": [{"type": "company", "label": "Netflix", "slug": "netflix"}],
            }
        )

        response = self.client.get("/api/app/search/suggest?q=net")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["suggestions"][0]["label"], "Netflix")


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

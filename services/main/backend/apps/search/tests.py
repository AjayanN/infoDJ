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
            json_response(
                {
                    "latest_events": [{"id": 10, "company": "Netflix"}],
                    "patterns": [{"pattern": "REVENUE_MODEL_EXPANSION", "sample_size": 2}],
                    "risk_signals": [],
                    "turn_impact": [],
                    "source_confidence": {
                        "events": {"total": 1, "with_date": 1, "with_source": 1, "avg_confidence": 0.7},
                        "turns": {"total": 1, "published": 0, "avg_confidence": 0.6},
                        "source_types": [],
                        "source_statuses": [],
                        "event_reviews": [],
                        "market_prices": {"total": 0, "companies": 0, "latest_price_date": None},
                        "financial_facts": {"total": 0, "companies": 0, "latest_filed": None},
                    },
                    "scorecard_candidates": [],
                    "company_situations": [],
                    "compare_examples": [],
                    "source_gaps": [
                        {
                            "key": "market_prices",
                            "dashboard": "turn_impact",
                            "reason": "Market reaction dashboards need daily price and benchmark ingestion.",
                            "source": "stooq",
                            "next_action": "Add ticker mapping and OHLCV ingestion.",
                        }
                    ],
                    "sections": {
                        "latest_moves": {
                            "key": "latest_moves",
                            "status": "available",
                            "eligible_count": 1,
                            "raw_count": 1,
                            "excluded_count": 0,
                            "items": [{"id": 10, "company": "Netflix"}],
                            "source_gaps": [],
                            "required_data": ["event_date"],
                            "next_action": "",
                        },
                        "turn_impact": {
                            "key": "turn_impact",
                            "status": "unavailable",
                            "eligible_count": 0,
                            "raw_count": 1,
                            "excluded_count": 1,
                            "items": [],
                            "source_gaps": [],
                            "required_data": ["daily_prices", "financial_facts"],
                            "next_action": "Run market price and SEC companyfacts ingestion.",
                        },
                        "compare": {
                            "key": "compare",
                            "status": "unavailable",
                            "eligible_count": 0,
                            "raw_count": 1,
                            "excluded_count": 1,
                            "items": [],
                            "source_gaps": [
                                {
                                    "key": "compare",
                                    "reason": "Need at least two eligible turns in the same comparable pattern/type.",
                                    "source": "turn_rebuild",
                                    "next_action": "Rebuild eligible turns.",
                                }
                            ],
                            "required_data": ["eligible_turns"],
                            "next_action": "Rebuild eligible turns.",
                        },
                    },
                }
            ),
        ]

        response = self.client.get("/api/app/dashboard?section=turn_impact&page=2&limit=25")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["company_count"], 2)
        self.assertEqual(response.data["summary"]["event_count"], 11)
        self.assertEqual(response.data["sector_counts"][0]["sector"], "Communication Services")
        self.assertEqual(response.data["latest_jobs"][0]["status"], "SUCCEEDED")
        self.assertEqual(response.data["source_gaps"][0]["key"], "market_prices")
        self.assertEqual(response.data["dashboards"]["latest_events"][0]["company"], "Netflix")
        self.assertEqual(response.data["dashboards"]["patterns"][0]["pattern"], "REVENUE_MODEL_EXPANSION")
        self.assertEqual(response.data["dashboards"]["sections"]["latest_moves"]["status"], "available")
        self.assertIn("turn_impact", response.data["dashboards"]["sections"])
        self.assertEqual(get.call_args_list[2].kwargs["params"], {"limit": "25", "section": "turn_impact", "page": "2"})

    @patch("apps.search.api.requests.get")
    def test_dashboard_handles_ingestion_failure(self, get):
        get.side_effect = requests.RequestException("network unavailable")

        response = self.client.get("/api/app/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["ingestion"]["available"])
        self.assertEqual(response.data["summary"]["company_count"], 0)
        self.assertEqual(response.data["source_gaps"][0]["key"], "companies_ingestion_unavailable")
        self.assertEqual(response.data["source_gaps"][0]["source"], "ingestion.companies")
        self.assertEqual(response.data["dashboards"]["latest_events"], [])

    @patch("apps.search.api.requests.get")
    def test_dashboard_reports_empty_source_backed_coverage_gap(self, get):
        get.side_effect = [json_response({"companies": []}), json_response({"jobs": []}), json_response({})]

        response = self.client.get("/api/app/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["company_count"], 0)
        self.assertEqual(response.data["source_gaps"][0]["key"], "companies_not_ingested")
        self.assertIn("source-backed companies", response.data["source_gaps"][0]["reason"])

    @patch("apps.search.api.requests.get")
    def test_dashboard_reports_companies_missing_source_documents(self, get):
        get.side_effect = [
            json_response(
                {
                    "companies": [
                        {
                            "name": "Netflix",
                            "slug": "netflix",
                            "sector": "Communication Services",
                            "source_count": 0,
                            "event_count": 7,
                            "strategic_turn_count": 3,
                        }
                    ]
                }
            ),
            json_response({"jobs": []}),
            json_response({}),
        ]

        response = self.client.get("/api/app/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["source_gaps"][0]["key"], "companies_missing_sources")
        self.assertEqual(response.data["source_gaps"][0]["source"], "ingestion.source_documents")

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

        response = self.client.get("/api/app/search?q=netflix&limit=5&event_page=2&turn_page=3&company_page=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], "en")
        self.assertEqual(response.data["results"]["companies"][0]["slug"], "netflix")
        self.assertEqual(
            get.call_args.kwargs["params"],
            {
                "q": "netflix",
                "language": "en",
                "limit": "5",
                "company_page": "1",
                "event_page": "2",
                "turn_page": "3",
            },
        )

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

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_company_profile_proxies_authenticated_ingestion_response(self, get):
        get.return_value = json_response(
            {
                "status": "partial",
                "company": {"name": "Netflix", "slug": "netflix"},
                "sections": {"summary": {"status": "available", "text": "Streaming service", "items": []}},
                "source_gaps": [],
            }
        )

        response = self.client.get("/api/app/companies/netflix/profile?as_of=2024-12-31")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["company"]["slug"], "netflix")
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/profile")
        self.assertEqual(get.call_args.kwargs["params"], {"as_of": "2024-12-31"})

    def test_company_profile_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/profile")

        self.assertEqual(response.status_code, 401)


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

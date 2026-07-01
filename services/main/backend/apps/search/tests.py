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
        get.side_effect = dashboard_responses(
            companies=json_response(
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
            jobs=json_response({"jobs": [{"id": 1, "status": "SUCCEEDED"}]}),
            dashboard=json_response(
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
        )

        response = self.client.get("/api/app/dashboard?section=turn_impact&page=2&limit=25&company=netflix")

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
        dashboard_call = next(call for call in get.call_args_list if call.args[0].endswith("/dashboard-data"))
        self.assertEqual(
            dashboard_call.kwargs["params"],
            {"limit": "25", "section": "turn_impact", "page": "2", "company": "netflix"},
        )

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
        get.side_effect = dashboard_responses(
            companies=json_response({"companies": []}), jobs=json_response({"jobs": []}), dashboard=json_response({})
        )

        response = self.client.get("/api/app/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["company_count"], 0)
        self.assertEqual(response.data["source_gaps"][0]["key"], "companies_not_ingested")
        self.assertIn("source-backed companies", response.data["source_gaps"][0]["reason"])

    @patch("apps.search.api.requests.get")
    def test_dashboard_reports_companies_missing_source_documents(self, get):
        get.side_effect = dashboard_responses(
            companies=json_response(
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
            jobs=json_response({"jobs": []}),
            dashboard=json_response({}),
        )

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

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_business_model_proxies_dates_and_response(self, get):
        get.return_value = json_response(
            {
                "status": "available",
                "company": {"name": "Netflix", "slug": "netflix"},
                "snapshot": {"effective_date": "2022-12-31", "components": [], "relationships": []},
                "source_gaps": [],
            }
        )

        response = self.client.get(
            "/api/app/companies/netflix/business-model?as_of=2022-12-31&compare_to=2011-12-31"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["company"]["slug"], "netflix")
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/business-model")
        self.assertEqual(get.call_args.kwargs["params"], {"as_of": "2022-12-31", "compare_to": "2011-12-31"})

    def test_business_model_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/business-model")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_operating_kpis_proxies_filters_and_response(self, get):
        get.return_value = json_response({"status": "available", "company": {"slug": "netflix"}, "series": []})

        response = self.client.get(
            "/api/app/companies/netflix/operating-kpis?metric=paid-memberships&segment=Streaming&comparable_only=true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/operating-kpis")
        self.assertEqual(get.call_args.kwargs["params"], {"metric": "paid-memberships", "segment": "Streaming", "comparable_only": "true"})

    def test_operating_kpis_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/operating-kpis")
        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_management_promises_proxies_register_filters(self, get):
        get.return_value = Mock(status_code=200, json=lambda: {"status": "available", "promises": []})
        get.return_value.raise_for_status.return_value = None

        response = self.client.get(
            "/api/app/companies/netflix/management-promises?status=IN_PROGRESS&due=due_soon&promise=subscriber-target"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/management-promises")
        self.assertEqual(get.call_args.kwargs["params"], {
            "status": "IN_PROGRESS", "due": "due_soon", "promise": "subscriber-target"
        })

    def test_management_promises_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/management-promises")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_strategy_milestones_proxies_filters(self, get):
        get.return_value = json_response({"status": "available", "company": {"slug": "netflix"}, "milestones": []})

        response = self.client.get(
            "/api/app/companies/netflix/strategy-milestones?status=STARTED&type=LAUNCH&origin=MANAGEMENT_ANNOUNCED&view=upcoming&milestone=ad-plan"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/strategy-milestones")
        self.assertEqual(get.call_args.kwargs["params"], {
            "status": "STARTED", "type": "LAUNCH", "origin": "MANAGEMENT_ANNOUNCED",
            "view": "upcoming", "milestone": "ad-plan",
        })

    def test_strategy_milestones_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/strategy-milestones")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_earnings_proxies_period_filter(self, get):
        get.return_value = json_response({"status": "available", "company": {"slug": "netflix"}, "periods": []})

        response = self.client.get("/api/app/companies/netflix/earnings?period=FY2026-Q1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/earnings")
        self.assertEqual(get.call_args.kwargs["params"], {"period": "FY2026-Q1"})

    def test_earnings_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/earnings")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_geographic_expansion_proxies_filters(self, get):
        get.return_value = json_response({"status": "available", "company": {"slug": "netflix"}, "markets": []})

        response = self.client.get(
            "/api/app/companies/netflix/geographic-expansion?status=ACTIVE&market_type=REGION"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/geographic-expansion")
        self.assertEqual(get.call_args.kwargs["params"], {"status": "ACTIVE", "market_type": "REGION"})

    def test_geographic_expansion_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/geographic-expansion")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_ownership_insider_proxies_filters(self, get):
        get.return_value = json_response({"status": "available", "company": {"slug": "netflix"}, "positions": []})

        response = self.client.get(
            "/api/app/companies/netflix/ownership-insider?holder_type=EXECUTIVE&transaction_type=SALE"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/ownership-insider")
        self.assertEqual(get.call_args.kwargs["params"], {"holder_type": "EXECUTIVE", "transaction_type": "SALE"})

    def test_ownership_insider_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/ownership-insider")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_valuation_context_proxies_filters(self, get):
        get.return_value = json_response({"status": "available", "company": {"slug": "netflix"}, "observations": []})

        response = self.client.get(
            "/api/app/companies/netflix/valuation-context?measure=PRICE_TO_SALES&as_of=2026-01-31"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/valuation-context")
        self.assertEqual(get.call_args.kwargs["params"], {"as_of": "2026-01-31", "measure": "PRICE_TO_SALES"})

    def test_valuation_context_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/valuation-context")

        self.assertEqual(response.status_code, 401)

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.search.api.requests.get")
    def test_leadership_decisions_proxies_filters(self, get):
        get.return_value = json_response({"status": "available", "company": {"slug": "netflix"}, "roles": []})

        response = self.client.get(
            "/api/app/companies/netflix/leadership-decisions?role_type=CEO&decision_type=SUCCESSION"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "http://ingestion.test/api/ingestion/companies/netflix/leadership-decisions")
        self.assertEqual(get.call_args.kwargs["params"], {"role_type": "CEO", "decision_type": "SUCCESSION"})

    def test_leadership_decisions_requires_authentication(self):
        response = APIClient().get("/api/app/companies/netflix/leadership-decisions")

        self.assertEqual(response.status_code, 401)


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def dashboard_responses(*, companies, jobs, dashboard):
    def respond(url, **_kwargs):
        if url.endswith("/companies"):
            return companies
        if url.endswith("/jobs"):
            return jobs
        if url.endswith("/dashboard-data"):
            return dashboard
        raise AssertionError(f"Unexpected dashboard URL: {url}")

    return respond

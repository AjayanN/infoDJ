from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.alerts.models import AlertDeliveryPreference, Briefing, Notification, WatchItem, Watchlist


class WatchlistAlertApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("alertuser", "alertuser@example.com", "StrongPass123!")
        self.other_user = get_user_model().objects.create_user("otheralert", "otheralert@example.com", "StrongPass123!")
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_watchlists_require_authentication(self):
        response = APIClient().get("/api/app/watchlists")

        self.assertEqual(response.status_code, 401)

    def test_user_can_create_private_watchlist_and_follow_company(self):
        response = self.client.post("/api/app/watchlists", {"name": "Core companies", "description": "Primary coverage"}, format="json")

        self.assertEqual(response.status_code, 201)
        watchlist_id = response.json()["watchlist"]["id"]
        item_response = self.client.post(
            f"/api/app/watchlists/{watchlist_id}/items",
            {"entity_type": "COMPANY", "entity_id": "netflix", "label": "Netflix", "company_slug": "netflix"},
            format="json",
        )
        self.assertEqual(item_response.status_code, 201)
        self.assertEqual(item_response.json()["item"]["entity_type"], "COMPANY")

    def test_watchlist_visibility_is_scoped_to_owner(self):
        Watchlist.objects.create(owner=self.other_user, name="Other private watchlist")

        response = self.client.get("/api/app/watchlists")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["watchlists"], [])

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.alerts.services.requests.get")
    def test_refresh_groups_duplicate_source_backed_alerts(self, get):
        get.return_value = json_response(
            {
                "latest_events": [
                    {
                        "id": 10,
                        "event_type": "PRICE_CHANGE",
                        "actual_change": "Netflix raised plan pricing.",
                        "event_date": "2026-01-01",
                        "source_count": 3,
                        "confidence_score": 0.8,
                    },
                    {
                        "id": 10,
                        "event_type": "PRICE_CHANGE",
                        "actual_change": "Netflix raised plan pricing.",
                        "event_date": "2026-01-01",
                        "source_count": 2,
                        "confidence_score": 0.8,
                    },
                ],
                "latest_turns": [],
                "risk_signals": [],
                "sections": {},
            }
        )
        self.client.post("/api/app/watchlists/follow-company", {"company_slug": "netflix", "company_name": "Netflix"}, format="json")

        response = self.client.post("/api/app/notifications/refresh", {"limit": 5}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stats"]["notifications_created"], 1)
        notification = Notification.objects.get(owner=self.user)
        self.assertEqual(notification.category, "PRODUCT_PRICING")
        self.assertEqual(notification.duplicate_count, 5)
        self.assertIn("Netflix raised plan pricing", notification.what_changed)

    def test_notification_center_status_feedback_and_preferences(self):
        watchlist = Watchlist.objects.create(owner=self.user, name="Core companies")
        notification = Notification.objects.create(
            owner=self.user,
            watchlist=watchlist,
            category="STRATEGIC_MOVE",
            severity="MEDIUM",
            title="Netflix strategic move",
            what_changed="A strategic move occurred.",
            why_it_matters="It may affect the thesis.",
            dedupe_key="netflix:move:1",
        )

        list_response = self.client.get("/api/app/notifications")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["summary"]["unread"], 1)

        update_response = self.client.patch(f"/api/app/notifications/{notification.id}", {"status": "READ"}, format="json")
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["notification"]["status"], "READ")

        feedback_response = self.client.post(f"/api/app/notifications/{notification.id}/feedback", {"rating": "useful"}, format="json")
        self.assertEqual(feedback_response.status_code, 201)

        preference_response = self.client.patch(
            "/api/app/notifications/delivery-preference",
            {"email_enabled": True, "email_frequency": "WEEKLY", "timezone": "UTC"},
            format="json",
        )
        self.assertEqual(preference_response.status_code, 200)
        self.assertTrue(preference_response.json()["delivery_preference"]["email_enabled"])
        self.assertEqual(preference_response.json()["delivery_preference"]["email_frequency"], "WEEKLY")

    @override_settings(INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.alerts.services.requests.get")
    def test_generate_daily_briefing_groups_alerts_and_coverage_gaps(self, get):
        get.side_effect = [
            json_response(
                {
                    "latest_events": [
                        {
                            "id": 10,
                            "event_type": "PRICE_CHANGE",
                            "actual_change": "Netflix raised plan pricing.",
                            "event_date": "2026-01-01",
                            "source_count": 2,
                            "confidence_score": 0.8,
                        }
                    ],
                    "latest_turns": [],
                    "risk_signals": [],
                    "sections": {},
                }
            ),
            json_response({"latest_events": [], "latest_turns": [], "risk_signals": [], "sections": {}}),
        ]
        self.client.post("/api/app/watchlists/follow-company", {"company_slug": "netflix", "company_name": "Netflix"}, format="json")
        watchlist = Watchlist.objects.get(owner=self.user)
        WatchItem.objects.create(watchlist=watchlist, entity_type="COMPANY", entity_id="quiet-company", label="Quiet Company", company_slug="quiet-company")

        response = self.client.post("/api/app/briefings", {"cadence": "DAILY", "refresh_alerts": True}, format="json")

        self.assertEqual(response.status_code, 201)
        briefing = response.json()["briefing"]
        self.assertEqual(briefing["cadence"], "DAILY")
        self.assertEqual(briefing["notification_count"], 1)
        self.assertEqual(briefing["source_gap_count"], 1)
        sections = {item["section"] for item in briefing["items"]}
        self.assertIn("COMPETITIVE_THEME", sections)
        self.assertIn("COVERAGE_GAPS", sections)
        self.assertIn("severity", briefing["ranking_note"])

    def test_briefing_detail_archive_feedback_and_email_log(self):
        watchlist = Watchlist.objects.create(owner=self.user, name="Core companies")
        notification = Notification.objects.create(
            owner=self.user,
            watchlist=watchlist,
            category="RISK_ESCALATION",
            severity="HIGH",
            title="Netflix risk escalation",
            what_changed="A risk increased.",
            why_it_matters="It may invalidate a thesis.",
            dedupe_key="netflix:risk:1",
        )
        AlertDeliveryPreference.objects.create(owner=self.user, email_enabled=True, email_frequency="DAILY")
        response = self.client.post("/api/app/briefings", {"cadence": "DAILY", "refresh_alerts": False}, format="json")
        self.assertEqual(response.status_code, 201)
        briefing_id = response.json()["briefing"]["id"]

        detail = self.client.get(f"/api/app/briefings/{briefing_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["briefing"]["status"], "SENT")
        self.assertEqual(detail.json()["briefing"]["delivery_logs"][0]["channel"], "EMAIL")
        self.assertEqual(detail.json()["briefing"]["items"][0]["notification_id"], notification.id)

        archive = self.client.patch(f"/api/app/briefings/{briefing_id}", {"status": "ARCHIVED"}, format="json")
        self.assertEqual(archive.status_code, 200)
        self.assertEqual(archive.json()["briefing"]["status"], "ARCHIVED")

        feedback = self.client.post(f"/api/app/briefings/{briefing_id}/feedback", {"rating": "useful"}, format="json")
        self.assertEqual(feedback.status_code, 201)
        self.assertEqual(Briefing.objects.filter(owner=self.user).count(), 1)


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

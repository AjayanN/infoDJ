from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.alerts.models import Notification, Watchlist


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


def json_response(payload: dict):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

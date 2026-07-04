from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


class FoundationStandardsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("foundationuser", "foundation@example.com", "StrongPass123!")
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_foundation_standards_require_authentication(self):
        response = APIClient().get("/api/app/foundations/standards")

        self.assertEqual(response.status_code, 401)

    def test_foundation_standards_include_wave_zero_rules(self):
        response = self.client.get("/api/app/foundations/standards")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["pilot"]["company_slug"], "netflix")
        rule_keys = {row["key"] for row in payload["rules"]}
        self.assertTrue({"evidence", "claims", "metrics", "periods", "company_identity", "confidence"}.issubset(rule_keys))
        state_keys = {row["key"] for row in payload["states"]}
        self.assertTrue({"partial", "unavailable", "stale", "conflict"}.issubset(state_keys))
        workflow_keys = {row["key"] for row in payload["review_workflows"]}
        self.assertTrue({"source_gap", "correction", "editorial_review"}.issubset(workflow_keys))

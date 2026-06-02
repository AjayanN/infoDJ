from __future__ import annotations

from django.test import Client, TestCase

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn
from apps.ingestion.services.event_extractor import EventSignal, actual_change_for, find_evidence_sentence


class IngestionSearchApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.netflix = Company.objects.create(
            name="Netflix",
            industry="Communication Services",
            country="United States",
        )
        BusinessEvent.objects.create(
            company=self.netflix,
            event_type="REVENUE_MODEL_EXPANSION",
            event_date="2022-10-13",
            decision_theme="AD_SUPPORTED_PLAN",
            actual_change="Netflix introduced advertising through an ad-supported subscription plan.",
            source_claim="Netflix launched Basic with Ads.",
            review_status="NEEDS_REVIEW",
        )
        StrategicTurn.objects.create(
            company=self.netflix,
            title="Netflix advertising revenue model expansion",
            turn_type="REVENUE_MODEL_EXPANSION",
            start_date="2022-10-13",
            summary="Netflix added advertising as a second revenue model.",
            decision="Introduce an ad-supported plan.",
            outcome="Advertising became a new monetization channel.",
        )
        StrategicTurn.objects.create(
            company=self.netflix,
            title="Netflix adapts to regulatory and legal risk",
            turn_type="REGULATORY_RESPONSE",
            start_date="2025-01-27",
            summary="Adapt to legal, regulatory, and compliance pressure.",
            decision="Adapt to legal, regulatory, and compliance pressure.",
            outcome="Compliance, risk management, and market-entry decisions become part of strategy.",
        )

    def test_search_requires_query(self):
        response = self.client.get("/search")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "q is required")

    def test_search_returns_company_event_and_turn_results(self):
        response = self.client.get("/search?q=advertising")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["language"], "en")
        self.assertEqual(payload["results"]["events"][0]["company_slug"], "netflix")
        self.assertEqual(payload["results"]["strategic_turns"][0]["title"], "Netflix advertising revenue model expansion")

    def test_search_suggest_returns_company_prefix_match(self):
        response = self.client.get("/search/suggest?q=net")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggestions"][0]["slug"], "netflix")

    def test_search_filters_generic_strategic_turn_templates(self):
        response = self.client.get("/search?q=legal")

        self.assertEqual(response.status_code, 200)
        titles = [turn["title"] for turn in response.json()["results"]["strategic_turns"]]
        self.assertNotIn("Netflix adapts to regulatory and legal risk", titles)


class EventClaimTextTests(TestCase):
    def regulatory_signal(self):
        return EventSignal(
            decision_theme="REGULATORY_LEGAL_RISK",
            event_type="REGULATORY_RESPONSE",
            lifecycle_stage="MATURITY",
            decision="Adapt to legal, regulatory, and compliance pressure.",
            trigger="Legal pressure.",
            before_state="",
            after_state="",
            outcome="",
            founder_lesson="",
            keywords=("regulatory", "litigation", "legal proceedings"),
        )

    def test_regulatory_actual_change_uses_source_specific_action(self):
        signal = self.regulatory_signal()

        actual_change = actual_change_for(
            signal,
            "The company settled litigation with state regulators and agreed to modify its compliance program.",
            company_name="ExampleCo",
        )

        self.assertIn("ExampleCo:", actual_change)
        self.assertIn("settled litigation", actual_change)
        self.assertNotIn("disclosed legal, regulatory, or compliance pressure", actual_change)

    def test_regulatory_actual_change_marks_risk_when_no_action_is_extracted(self):
        signal = self.regulatory_signal()

        actual_change = actual_change_for(
            signal,
            "The company is subject to laws and regulations in each market where it operates.",
            company_name="ExampleCo",
        )

        self.assertIn("no response action was extracted", actual_change)
        self.assertIn("laws and regulations", actual_change)

    def test_regulatory_evidence_prefers_action_over_heading_fragments(self):
        signal = self.regulatory_signal()
        text = (
            "Government Regulation. "
            "Legal Proceedings | ||||||| Item 4. "
            "Regulatory emissions standards require us to continue to make investments as new products and new regulations are introduced."
        )

        evidence = find_evidence_sentence(text, signal, signal.keywords)

        self.assertIn("require us to continue to make investments", evidence)
        self.assertNotIn("Legal Proceedings |", evidence)

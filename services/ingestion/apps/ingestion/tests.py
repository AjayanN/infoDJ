from __future__ import annotations

from datetime import date

from django.core.management import call_command
from django.test import Client, TestCase

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import FinancialFact, MarketPrice, SourceDocument, SourceGap
from apps.ingestion.services.event_extractor import EventSignal, actual_change_for, find_evidence_sentence
from apps.ingestion.services.market_price_client import (
    parse_alpha_vantage_daily_csv,
    parse_fmp_historical_prices,
)


class IngestionSearchApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.netflix = Company.objects.create(
            name="Netflix",
            aliases=["NFLX"],
            industry="Communication Services",
            country="United States",
            sec_cik="0001065280",
        )
        self.source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="SEC",
            url="https://example.com/netflix-10k",
            title="Netflix 10-K",
            publisher="SEC",
            language="en",
        )
        BusinessEvent.objects.create(
            company=self.netflix,
            source_document=self.source,
            event_type="REVENUE_MODEL_EXPANSION",
            event_date="2022-10-13",
            decision_theme="AD_SUPPORTED_PLAN",
            actual_change="Netflix introduced advertising through an ad-supported subscription plan.",
            source_claim="Netflix launched Basic with Ads.",
            evidence_text="Netflix launched Basic with Ads on November 3, 2022.",
            confidence_score="0.850",
            review_status="NEEDS_REVIEW",
        )
        self.turn = StrategicTurn.objects.create(
            company=self.netflix,
            title="Netflix advertising revenue model expansion",
            turn_type="REVENUE_MODEL_EXPANSION",
            start_date="2022-10-13",
            summary="Netflix introduced advertising as a second revenue model.",
            decision="Introduce an ad-supported plan.",
            outcome="Advertising became a new monetization channel.",
            confidence_score="0.850",
        )
        StrategicTurnSource.objects.create(strategic_turn=self.turn, source_document=self.source)
        StrategicTurn.objects.create(
            company=self.netflix,
            title="Netflix adapts to regulatory and legal risk",
            turn_type="REGULATORY_RESPONSE",
            start_date="2025-01-27",
            summary="Adapt to legal, regulatory, and compliance pressure.",
            decision="Adapt to legal, regulatory, and compliance pressure.",
            outcome="Compliance, risk management, and market-entry decisions become part of strategy.",
        )
        MarketPrice.objects.create(
            company=self.netflix,
            ticker="NFLX",
            provider="STOOQ",
            price_date=date(2022, 10, 13),
            close_price="230.000000",
            raw={"fixture": True},
        )
        MarketPrice.objects.create(
            company=self.netflix,
            ticker="NFLX",
            provider="STOOQ",
            price_date=date(2022, 10, 20),
            close_price="253.000000",
            raw={"fixture": True},
        )
        FinancialFact.objects.create(
            company=self.netflix,
            taxonomy="us-gaap",
            concept="Revenues",
            label="Revenues",
            unit="USD",
            fy=2022,
            fp="FY",
            filed=date(2023, 1, 27),
            frame="CY2022",
            value="31615550000.000",
            accession_number="0001065280-23-000017",
            raw={"fixture": True},
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
        self.assertEqual(payload["pagination"]["events"]["total"], 1)
        self.assertEqual(payload["pagination"]["strategic_turns"]["page"], 1)

    def test_search_suggest_returns_company_prefix_match(self):
        response = self.client.get("/search/suggest?q=net")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggestions"][0]["slug"], "netflix")

    def test_search_filters_generic_strategic_turn_templates(self):
        response = self.client.get("/search?q=legal")

        self.assertEqual(response.status_code, 200)
        titles = [turn["title"] for turn in response.json()["results"]["strategic_turns"]]
        self.assertNotIn("Netflix adapts to regulatory and legal risk", titles)

    def test_dashboard_data_returns_source_backed_surfaces(self):
        response = self.client.get("/dashboard-data")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["latest_events"][0]["company_slug"], "netflix")
        self.assertEqual(payload["sections"]["latest_moves"]["status"], "available")
        self.assertEqual(payload["sections"]["strategic_turns"]["eligible_count"], 1)
        self.assertEqual(payload["sections"]["strategic_turns"]["excluded_count"], 1)
        self.assertIn("REVENUE_MODEL_EXPANSION", [row["pattern"] for row in payload["patterns"]])
        self.assertEqual(payload["scorecard_candidates"][0]["source_count"], 1)
        self.assertEqual(payload["sections"]["turn_impact"]["status"], "available")
        self.assertEqual(payload["sections"]["turn_impact"]["items"][0]["ticker"], "NFLX")
        self.assertIn("T+7", [row["window"] for row in payload["sections"]["turn_impact"]["items"][0]["windows"]])
        self.assertNotIn("market_prices", [gap["key"] for gap in payload["source_gaps"]])
        self.assertNotIn("financial_facts", [gap["key"] for gap in payload["source_gaps"]])
        self.assertEqual(payload["source_confidence"]["source_types"][0]["source_api"], "SEC")
        self.assertEqual(payload["source_confidence"]["market_prices"]["total"], 2)
        self.assertEqual(payload["source_confidence"]["financial_facts"]["total"], 1)
        self.assertIn("company_situations", payload)
        self.assertEqual(payload["sections"]["compare"]["status"], "unavailable")
        self.assertTrue(SourceGap.objects.filter(gap_type="compare_turns", dashboard="compare").exists())

    def test_dashboard_data_paginates_section_items(self):
        BusinessEvent.objects.create(
            company=self.netflix,
            source_document=self.source,
            event_type="REVENUE_MODEL_EXPANSION",
            event_date="2022-11-03",
            decision_theme="PAID_SHARING",
            actual_change="Netflix launched paid sharing as a monetization program.",
            source_claim="Netflix began paid sharing.",
            evidence_text="Netflix launched paid sharing in 2022.",
            confidence_score="0.850",
            review_status="NEEDS_REVIEW",
        )

        response = self.client.get("/dashboard-data?section=latest_moves&page=2&limit=1")

        self.assertEqual(response.status_code, 200)
        section = response.json()["sections"]["latest_moves"]
        self.assertEqual(section["eligible_count"], 2)
        self.assertEqual(section["page"], 2)
        self.assertEqual(section["page_size"], 1)
        self.assertEqual(section["total_pages"], 2)
        self.assertTrue(section["has_previous"])
        self.assertFalse(section["has_next"])
        self.assertEqual(len(section["items"]), 1)

    def test_rebuild_specific_turns_unlocks_pattern_scorecard_and_compare(self):
        BusinessEvent.objects.create(
            company=self.netflix,
            source_document=self.source,
            event_type="REVENUE_MODEL_EXPANSION",
            event_date="2022-11-03",
            decision_theme="PAID_SHARING",
            actual_change="Netflix launched paid sharing as a monetization program.",
            source_claim="Netflix began paid sharing.",
            evidence_text="Netflix launched paid sharing in 2022.",
            confidence_score="0.850",
            review_status="NEEDS_REVIEW",
        )

        call_command("rebuild_specific_turns", company="netflix")
        response = self.client.get("/dashboard-data")
        payload = response.json()

        self.assertEqual(payload["sections"]["strategic_turns"]["status"], "available")
        self.assertEqual(payload["sections"]["patterns"]["status"], "available")
        self.assertEqual(payload["sections"]["scorecards"]["status"], "available")
        self.assertEqual(payload["sections"]["compare"]["status"], "available")
        self.assertGreaterEqual(payload["sections"]["compare"]["items"][0]["sample_size"], 2)


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


class MarketPriceClientTests(TestCase):
    def test_parse_fmp_historical_prices(self):
        bars = parse_fmp_historical_prices(
            [
                {"date": "2022-10-14", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 1000},
                {"date": "2022-10-13", "open": 8, "high": 9, "low": 7, "close": 8.5, "volume": 900},
            ],
            ticker="NFLX",
        )

        self.assertEqual([bar.price_date.isoformat() for bar in bars], ["2022-10-13", "2022-10-14"])
        self.assertEqual(bars[0].provider, "FMP")
        self.assertEqual(str(bars[0].close_price), "8.5")

    def test_parse_alpha_vantage_daily_csv(self):
        bars = parse_alpha_vantage_daily_csv(
            "\n".join(
                [
                    "timestamp,open,high,low,close,adjusted_close,volume,dividend_amount,split_coefficient",
                    "2022-10-14,10,12,9,11,10.5,1000,0,1",
                    "2022-10-13,8,9,7,8.5,8.25,900,0,1",
                ]
            ),
            ticker="NFLX",
        )

        self.assertEqual([bar.price_date.isoformat() for bar in bars], ["2022-10-13", "2022-10-14"])
        self.assertEqual(bars[0].provider, "ALPHA_VANTAGE")
        self.assertEqual(str(bars[0].close_price), "8.25")

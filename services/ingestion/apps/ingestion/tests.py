from __future__ import annotations

from datetime import date

from django.core.management import call_command
from django.test import Client, TestCase

from apps.companies.models import (
    BusinessModelComponent,
    BusinessModelRelationship,
    BusinessModelSnapshot,
    Company,
    CompanyProfileSnapshot,
)
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import FinancialFact, MarketPrice, SourceDocument, SourceGap
from apps.ingestion.services.event_extractor import EventSignal, actual_change_for, find_evidence_sentence
from apps.ingestion.services.company_profile_client import collect_official_company_profile, parse_official_profile_html
from apps.ingestion.services.business_model_builder import build_business_model_from_profile, collect_business_model_page
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

    def test_company_profile_returns_source_backed_360_sections(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 12, 31),
            source_document=self.source,
            status="PUBLISHED",
            summary="Netflix is a global entertainment service.",
            business_model="Subscriptions and advertising fund streaming entertainment.",
            subsidiaries=["Netflix Studios"],
            brands=["Netflix"],
            segments=["Streaming entertainment", "Advertising"],
            products=["Streaming plans", "Ad-supported plan"],
            customer_groups=["Consumers", "Advertisers"],
            revenue_sources=["Subscriptions", "Advertising"],
            geographies=["United States", "International"],
            leadership=[{"name": "Executive team", "role": "Management"}],
            competitors=["Disney+", "Prime Video"],
            strategic_priorities=["Grow advertising", "Improve member value"],
            evidence_text="Netflix described its services and revenue model in its filing.",
            confidence_score="0.900",
        )

        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["company"]["name"], "Netflix")
        self.assertEqual(payload["sections"]["revenue_sources"]["items"], ["Subscriptions", "Advertising"])
        self.assertEqual(payload["coverage"]["completeness_percent"], 100)
        self.assertEqual(payload["highlights"]["latest_events"][0]["company_slug"], "netflix")
        self.assertEqual(payload["highlights"]["financial_facts"][0]["concept"], "Revenues")
        self.assertEqual(payload["evidence"][0]["title"], "Netflix 10-K")
        self.assertEqual(payload["source_gaps"], [])

    def test_company_profile_reports_partial_section_gaps(self):
        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["sections"]["geographies"]["status"], "available")
        self.assertEqual(payload["sections"]["business_model"]["status"], "unavailable")
        self.assertIn("company_profile_business_model", [gap["key"] for gap in payload["source_gaps"]])

    def test_company_profile_supports_historical_snapshot_selection(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2021, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            summary="Netflix was a subscription streaming service.",
            business_model="Subscription streaming.",
            subsidiaries=["Netflix Studios"],
            brands=["Netflix"],
            segments=["Streaming entertainment"],
            products=["Streaming plans"],
            customer_groups=["Streaming members"],
            revenue_sources=["Subscriptions"],
            geographies=["United States", "International"],
            leadership=["Executive team"],
            competitors=["Disney+"],
            strategic_priorities=["Grow memberships"],
            confidence_score="0.800",
        )
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 12, 31),
            source_document=self.source,
            status="PUBLISHED",
            summary="Netflix expanded its monetization model.",
            business_model="Subscriptions and advertising.",
            subsidiaries=["Netflix Studios"],
            brands=["Netflix"],
            segments=["Streaming entertainment", "Advertising"],
            products=["Streaming plans", "Ad-supported plan"],
            customer_groups=["Streaming members", "Advertisers"],
            revenue_sources=["Subscriptions", "Advertising"],
            geographies=["United States", "International"],
            leadership=["Executive team"],
            competitors=["Disney+"],
            strategic_priorities=["Grow advertising"],
            confidence_score="0.900",
        )

        response = self.client.get("/companies/netflix/profile?as_of=2021-12-31")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"]["effective_date"], "2021-12-31")
        self.assertEqual(payload["sections"]["business_model"]["text"], "Subscription streaming.")
        self.assertEqual(len(payload["snapshot_history"]), 2)

    def test_company_profile_unknown_company_returns_404(self):
        response = self.client.get("/companies/unknown/profile")

        self.assertEqual(response.status_code, 404)

    def test_business_model_returns_components_relationships_and_changes(self):
        older = BusinessModelSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2011, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            summary="DVD and streaming subscriptions.",
            confidence_score="0.800",
        )
        old_payer = BusinessModelComponent.objects.create(snapshot=older, component_type="PAYER", name="DVD members", confidence_score="0.8")
        old_offer = BusinessModelComponent.objects.create(snapshot=older, component_type="OFFERING", name="DVD-by-mail", confidence_score="0.8")
        BusinessModelRelationship.objects.create(snapshot=older, from_component=old_payer, to_component=old_offer, relationship_type="PAYS_FOR", confidence_score="0.8")

        current = BusinessModelSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2022, 12, 31),
            source_document=self.source,
            status="PUBLISHED",
            summary="Streaming subscriptions and advertising.",
            confidence_score="0.900",
        )
        components = {}
        values = {
            "PAYER": "Streaming members",
            "USER": "Entertainment viewers",
            "OFFERING": "Ad-supported plan",
            "REVENUE": "Advertising revenue",
            "CHANNEL": "Internet-connected devices",
            "GEOGRAPHY": "Global markets",
            "PARTNER": "Advertising partners",
            "COST": "Content production",
            "ASSET": "Streaming platform",
        }
        for component_type, name in values.items():
            components[component_type] = BusinessModelComponent.objects.create(
                snapshot=current,
                component_type=component_type,
                name=name,
                confidence_score="0.9",
            )
        BusinessModelRelationship.objects.create(
            snapshot=current,
            from_component=components["PAYER"],
            to_component=components["OFFERING"],
            relationship_type="PAYS_FOR",
            confidence_score="0.9",
        )
        peer = Company.objects.create(name="StreamPeer", industry="Communication Services")
        peer_snapshot = BusinessModelSnapshot.objects.create(
            company=peer,
            effective_date=date(2022, 12, 31),
            status="REVIEWED",
            summary="Peer subscription streaming model.",
            confidence_score="0.800",
        )
        BusinessModelComponent.objects.create(
            snapshot=peer_snapshot,
            component_type="PAYER",
            name="Streaming members",
            confidence_score="0.8",
        )

        response = self.client.get("/companies/netflix/business-model?as_of=2022-12-31&compare_to=2011-12-31")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["coverage"]["completeness_percent"], 100)
        self.assertEqual(payload["snapshot"]["component_groups"]["PAYER"][0]["name"], "Streaming members")
        self.assertEqual(payload["snapshot"]["relationships"][0]["relationship_type"], "PAYS_FOR")
        self.assertIn("Ad-supported plan", [row["name"] for row in payload["changes"]["components_added"]])
        self.assertIn("DVD-by-mail", [row["name"] for row in payload["changes"]["components_removed"]])
        self.assertEqual(payload["peer_models"][0]["company"], "StreamPeer")
        self.assertEqual(payload["peer_models"][0]["shared_components"][0]["name"], "streaming members")

    def test_business_model_reports_unavailable_without_reviewed_snapshot(self):
        response = self.client.get("/companies/netflix/business-model")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertGreater(len(response.json()["source_gaps"]), 0)

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


class CompanyProfileCollectorTests(TestCase):
    def test_parse_official_profile_html_uses_structured_organization_data(self):
        html = """
        <html><head><title>ExampleCo</title>
        <script type="application/ld+json">
        {
          "@type": "Organization",
          "name": "ExampleCo",
          "description": "ExampleCo provides business software.",
          "brand": [{"name": "Example Cloud"}],
          "makesOffer": [{"itemOffered": {"name": "Analytics Platform"}}],
          "areaServed": [{"name": "United States"}]
        }
        </script></head><body></body></html>
        """

        data = parse_official_profile_html(html)

        self.assertEqual(data.summary, "ExampleCo provides business software.")
        self.assertEqual(data.brands, ("Example Cloud",))
        self.assertEqual(data.products, ("Analytics Platform",))
        self.assertEqual(data.geographies, ("United States",))

    def test_collect_official_company_profile_persists_draft_evidence(self):
        company = Company.objects.create(name="ExampleCo", website="https://example.com")
        session = FakeProfileSession()

        snapshot = collect_official_company_profile(company, session=session)

        self.assertEqual(snapshot.status, "DRAFT")
        self.assertEqual(snapshot.summary, "ExampleCo provides business software.")
        self.assertEqual(snapshot.products, ["Analytics Platform"])
        self.assertEqual(snapshot.source_document.source_api, "OFFICIAL_WEBSITE")
        self.assertEqual(session.calls, ["https://example.com/robots.txt", "https://example.com"])

    def test_build_business_model_from_profile_marks_relationships_inferred(self):
        company = Company.objects.create(name="ProfileCo")
        source = SourceDocument.objects.create(
            company=company,
            source_api="OFFICIAL_WEBSITE",
            url="https://example.com/profile",
            title="ProfileCo official profile",
        )
        CompanyProfileSnapshot.objects.create(
            company=company,
            effective_date=date(2025, 12, 31),
            source_document=source,
            status="REVIEWED",
            business_model="Subscription software.",
            products=["Analytics platform"],
            customer_groups=["Business teams"],
            revenue_sources=["Subscriptions"],
            evidence_text="ProfileCo sells analytics subscriptions to business teams.",
            confidence_score="0.850",
        )

        snapshot = build_business_model_from_profile(company)

        self.assertEqual(snapshot.status, "DRAFT")
        self.assertEqual(snapshot.components.count(), 3)
        self.assertEqual(snapshot.relationships.count(), 2)
        self.assertTrue(all(row.is_inferred for row in snapshot.relationships.all()))

    def test_collect_business_model_page_persists_draft_historical_source(self):
        company = Company.objects.create(name="ArchiveCo", website="https://example.com")
        session = FakeProfileSession()

        snapshot = collect_business_model_page(
            company,
            url="https://example.com",
            effective_date=date(2020, 12, 31),
            session=session,
        )

        self.assertEqual(snapshot.status, "DRAFT")
        self.assertEqual(snapshot.effective_date, date(2020, 12, 31))
        self.assertEqual(snapshot.source_document.source_api, "OFFICIAL_WEBSITE")


class FakeProfileResponse:
    def __init__(self, *, url: str, text: str, status_code: int = 200):
        self.url = url
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeProfileSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(url)
        if url.endswith("robots.txt"):
            return FakeProfileResponse(url=url, text="User-agent: *\nAllow: /")
        return FakeProfileResponse(
            url=url,
            text='''<html><head><title>ExampleCo</title><script type="application/ld+json">{
              "@type": "Organization",
              "description": "ExampleCo provides business software.",
              "makesOffer": [{"itemOffered": {"name": "Analytics Platform"}}]
            }</script></head></html>''',
        )


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

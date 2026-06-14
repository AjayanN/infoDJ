from __future__ import annotations

from datetime import date

from django.core.management import call_command
from django.test import Client, TestCase
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import (
    BusinessModelComponent,
    BusinessModelRelationship,
    BusinessModelSnapshot,
    Company,
    CompanyProfileSnapshot,
    KpiDefinition,
    KpiDefinitionVersion,
    KpiObservation,
    KpiTarget,
    ManagementPromise,
    ManagementPromiseUpdate,
)
from apps.curation.models import BusinessEvent, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import ArticleExtraction, FinancialFact, MarketPrice, SourceDocument, SourceGap
from apps.ingestion.services.event_extractor import EventSignal, actual_change_for, find_evidence_sentence
from apps.ingestion.services.company_profile_client import collect_official_company_profile, parse_official_profile_html
from apps.ingestion.services.company_profile_fallbacks import PROFILE_FALLBACKS
from apps.ingestion.services.company_profile_quality import company_profile_quality_issues
from apps.ingestion.services.business_model_builder import build_business_model_from_profile, collect_business_model_page
from apps.ingestion.services.kpi_collector import collect_kpi_csv, collect_kpi_html_table
from apps.ingestion.services.kpi_companyfacts_builder import build_companyfacts_kpis
from apps.ingestion.services.management_promise_builder import build_promise_candidates_from_kpi_targets
from apps.ingestion.services.reviewed_management_promises import (
    REVIEWED_PROMISE_SPECS,
    build_reviewed_management_promise,
    management_promise_quality_issues,
)
from apps.ingestion.services.market_price_client import (
    parse_alpha_vantage_daily_csv,
    parse_fmp_historical_prices,
)
from apps.ingestion.services.sec_profile_builder import SecProfileData, apply_profile_fallbacks, parse_sec_profile_text
from apps.ingestion.services.wikidata_client import normalize_company_entity


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

    def test_company_profile_prefers_dated_reviewed_business_model_summary(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 12, 31),
            source_document=self.source,
            status="PUBLISHED",
            summary="Netflix is a global entertainment service.",
            business_model="Stale profile business model.",
        )
        BusinessModelSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 6, 30),
            source_document=self.source,
            status="REVIEWED",
            summary="Subscriptions and advertising fund streaming entertainment.",
            confidence_score="0.900",
        )
        BusinessModelSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2025, 6, 30),
            source_document=self.source,
            status="REVIEWED",
            summary="Future business model summary.",
            confidence_score="0.900",
        )

        response = self.client.get("/companies/netflix/profile?as_of=2024-12-31")

        self.assertEqual(response.status_code, 200)
        section = response.json()["sections"]["business_model"]
        self.assertEqual(section["text"], "Subscriptions and advertising fund streaming entertainment.")
        self.assertEqual(section["source"], "business_model_map")

    def test_company_profile_combines_latest_non_empty_reviewed_source_fields(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            summary="Netflix is a global entertainment service.",
            subsidiaries=["Netflix Studios"],
            geographies=["United States", "International"],
            confidence_score="0.650",
        )
        official_source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="OFFICIAL_WEBSITE",
            url="https://example.com/netflix",
            title="Netflix official website",
            publisher="Netflix",
            language="en",
        )
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2025, 1, 31),
            source_document=official_source,
            status="REVIEWED",
            products=["Streaming plans", "Games"],
            brands=["Netflix"],
            confidence_score="0.600",
        )

        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        sections = response.json()["sections"]
        self.assertEqual(sections["summary"]["text"], "Netflix is a global entertainment service.")
        self.assertEqual(sections["subsidiaries"]["items"], ["Netflix Studios"])
        self.assertEqual(sections["products"]["items"], ["Streaming plans", "Games"])

    def test_company_profile_same_date_sources_do_not_create_false_changes(self):
        for source_api, summary, products in (
            ("WIKIDATA", "Example summary", []),
            ("OFFICIAL_WEBSITE", "", ["Example product"]),
        ):
            source = SourceDocument.objects.create(
                company=self.netflix,
                source_api=source_api,
                url=f"https://example.com/{source_api.lower()}",
                title=source_api,
                publisher=source_api,
                language="en",
            )
            CompanyProfileSnapshot.objects.create(
                company=self.netflix,
                effective_date=date(2025, 1, 31),
                source_document=source,
                status="REVIEWED",
                summary=summary,
                products=products,
                confidence_score="0.600",
            )

        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["changes"], [])

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

    def test_operating_kpis_returns_dictionary_series_formula_and_alerts(self):
        metric = KpiDefinition.objects.create(
            company=self.netflix, slug="paid-memberships", name="Paid memberships",
            description="Period-end paid memberships.", unit="million", cadence="QUARTERLY",
            value_type="REPORTED", scope="Global streaming",
        )
        KpiDefinitionVersion.objects.create(
            kpi=metric, effective_date=date(2022, 1, 1), definition="Paid memberships at period end.",
            source_document=self.source,
        )
        for period_end, fiscal_period, value in ((date(2022, 3, 31), "Q1", "220"), (date(2022, 6, 30), "Q2", "225")):
            KpiObservation.objects.create(
                kpi=metric, period_start=date(2022, period_end.month - 2, 1), period_end=period_end,
                fiscal_year=2022, fiscal_period=fiscal_period, value=value, segment="Streaming",
                source_document=self.source, confidence_score="0.9",
            )

        response = self.client.get("/companies/netflix/operating-kpis?metric=paid-memberships&segment=Streaming")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["selected_metric"]["slug"], "paid-memberships")
        self.assertEqual(len(payload["series"]), 2)
        self.assertEqual(payload["missing_periods"], [])
        self.assertEqual(payload["alerts"][0]["type"], "ACCELERATION")
        self.assertEqual(payload["export_rows"][0]["metric_slug"], "paid-memberships")

    def test_operating_kpis_does_not_treat_missing_data_as_zero(self):
        response = self.client.get("/companies/netflix/operating-kpis")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(response.json()["series"], [])

    def test_management_promises_returns_only_reviewed_published_records_with_history(self):
        metric = KpiDefinition.objects.create(
            company=self.netflix, slug="launch-markets", name="Launch markets", description="Markets launched.",
            unit="countries", cadence="EVENT", value_type="REPORTED", scope="Ad-supported plan",
        )
        promise = ManagementPromise.objects.create(
            company=self.netflix, slug="launch-basic-with-ads", title="Launch Basic with Ads in 12 countries",
            promise_type="COMMITMENT", original_statement="Launch in 12 countries in November 2022.",
            speaker="Netflix management", speaker_role="Company management", statement_date=date(2022, 10, 13),
            target_end_date=date(2022, 11, 30), metric_name="Launch markets", target_value="12", unit="countries",
            scope="Ad-supported plan", evaluation_rule="Available in all 12 announced countries.",
            current_status="ACHIEVED", source_document=self.source, evidence_text="Source-backed announcement.",
            linked_kpi=metric, confidence_score="0.9", review_status="REVIEWED", is_published=True,
        )
        ManagementPromiseUpdate.objects.create(
            promise=promise, update_date=date(2022, 11, 3), status="ACHIEVED",
            summary="The plan launched in the announced window.", source_document=self.source,
            evidence_text="Launch evidence.", confidence_score="0.9", review_status="REVIEWED",
        )
        ManagementPromise.objects.create(
            company=self.netflix, slug="unreviewed", title="Unreviewed claim", promise_type="ASPIRATION",
            original_statement="Grow over time.", statement_date=date(2022, 10, 13), current_status="UNVERIFIABLE",
            review_status="NEEDS_REVIEW", is_published=False,
        )

        response = self.client.get("/companies/netflix/management-promises?status=ACHIEVED&promise=launch-basic-with-ads")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(len(payload["promises"]), 1)
        self.assertEqual(payload["selected_promise"]["updates"][0]["status"], "ACHIEVED")
        self.assertFalse(payload["selected_promise"]["updates"][0]["is_contradiction_candidate"])
        self.assertIsNone(payload["selected_promise"]["baseline_value"])
        self.assertEqual(payload["selected_promise"]["linked_kpi"]["slug"], "launch-markets")
        self.assertEqual(payload["coverage"]["source_count"], 1)

    def test_management_promises_reports_unavailable_without_reviewed_records(self):
        response = self.client.get("/companies/netflix/management-promises")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(response.json()["promises"], [])
        self.assertTrue(response.json()["source_gaps"])

    def test_kpi_target_builder_creates_unpublished_review_candidate(self):
        metric = KpiDefinition.objects.create(
            company=self.netflix, slug="paid-memberships", name="Paid memberships", description="Members.",
            unit="million", cadence="ANNUAL", value_type="REPORTED", scope="Global streaming",
        )
        KpiTarget.objects.create(
            kpi=metric, target_date=date(2027, 12, 31), target_value="300",
            condition="Reach 300 million paid memberships.", status="IN_PROGRESS", source_document=self.source,
        )

        first = build_promise_candidates_from_kpi_targets(self.netflix)
        second = build_promise_candidates_from_kpi_targets(self.netflix)

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["updated"], 1)
        promise = ManagementPromise.objects.get(company=self.netflix)
        self.assertEqual(promise.review_status, "NEEDS_REVIEW")
        self.assertFalse(promise.is_published)
        self.assertEqual(promise.linked_kpi, metric)

    def test_reviewed_promise_catalog_covers_every_configured_company(self):
        expected = {slugify(seed.name) for seed in CROSS_SECTOR_COMPANIES}

        self.assertEqual(set(REVIEWED_PROMISE_SPECS), expected)

    def test_reviewed_promise_builder_preserves_exact_filing_sentence_and_is_idempotent(self):
        ArticleExtraction.objects.create(
            source_document=self.source,
            clean_text=(
                "Our core strategy is to grow globally. "
                "We aim to offer a range of pricing plans, including an ad-supported subscription plan, "
                "to meet a variety of consumer needs."
            ),
            word_count=28,
            extraction_status="SUCCEEDED",
        )

        first = build_reviewed_management_promise(self.netflix)
        second = build_reviewed_management_promise(self.netflix)

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["updated"], 1)
        promise = ManagementPromise.objects.get(company=self.netflix)
        self.assertEqual(promise.original_statement, promise.evidence_text)
        self.assertIn("ad-supported subscription plan", promise.original_statement)
        self.assertEqual(promise.source_document, self.source)
        self.assertEqual(promise.review_status, "REVIEWED")
        self.assertTrue(promise.is_published)
        self.assertEqual(management_promise_quality_issues(self.netflix), [])

    def test_reviewed_promise_builder_does_not_publish_when_reviewed_statement_is_absent(self):
        ArticleExtraction.objects.create(
            source_document=self.source,
            clean_text="The filing describes current operations without the reviewed strategic statement.",
            word_count=10,
            extraction_status="SUCCEEDED",
        )

        result = build_reviewed_management_promise(self.netflix)

        self.assertEqual(result["skipped"], 1)
        self.assertFalse(ManagementPromise.objects.filter(company=self.netflix).exists())
        self.assertEqual(management_promise_quality_issues(self.netflix), ["no reviewed published management promise"])

    def test_companyfacts_builder_creates_idempotent_annual_and_quarterly_series(self):
        for filed, accession, value in (
            (date(2024, 7, 20), "0001-24-000001", "100"),
            (date(2024, 8, 1), "0001-24-000002", "105"),
        ):
            FinancialFact.objects.create(
                company=self.netflix, taxonomy="us-gaap", concept="Revenues", label="Revenue", unit="USD",
                fy=2024, fp="Q2", filed=filed, frame="CY2024Q2", value=value,
                accession_number=accession, raw={"start": "2024-04-01", "end": "2024-06-30", "form": "10-Q"},
            )
        FinancialFact.objects.create(
            company=self.netflix, taxonomy="us-gaap", concept="Revenues", label="Revenue", unit="USD",
            fy=2023, fp="FY", filed=date(2024, 2, 1), frame="CY2023", value="400",
            accession_number="0001-24-000003", raw={"start": "2023-01-01", "end": "2023-12-31", "form": "10-K"},
        )

        first = build_companyfacts_kpis(self.netflix)
        second = build_companyfacts_kpis(self.netflix)

        self.assertEqual(first["definitions"], 2)
        self.assertEqual(second["definitions"], 2)
        quarterly = KpiDefinition.objects.get(company=self.netflix, cadence="QUARTERLY", aliases__contains=["Revenues"])
        self.assertEqual(quarterly.observations.count(), 1)
        observation = quarterly.observations.get()
        self.assertEqual(str(observation.value), "105.000000")
        self.assertTrue(observation.is_restatement)
        self.assertTrue(observation.is_non_comparable)

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

    def test_dashboard_data_preserves_company_scope_and_returns_sector_peers(self):
        peer = Company.objects.create(name="Disney", industry=self.netflix.industry, country="United States")
        peer_source = SourceDocument.objects.create(
            company=peer,
            source_api="SEC",
            url="https://example.com/disney-10k",
            title="Disney 10-K",
            publisher="SEC",
            language="en",
        )
        for company, source, change in (
            (self.netflix, self.source, "Netflix recorded a material performance decline in engagement."),
            (peer, peer_source, "Disney recorded a material performance decline in subscribers."),
        ):
            BusinessEvent.objects.create(
                company=company,
                source_document=source,
                event_type="PERFORMANCE_DECLINE",
                event_date="2024-10-01",
                decision_theme="PERFORMANCE_PRESSURE",
                actual_change=change,
                source_claim=change,
                evidence_text=change,
                confidence_score="0.850",
                review_status="NEEDS_REVIEW",
            )

        response = self.client.get("/dashboard-data?section=risk_signals&company=netflix")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["scope"]["company_slug"], "netflix")
        self.assertEqual({row["company_slug"] for row in payload["sections"]["latest_moves"]["items"]}, {"netflix"})
        self.assertEqual({row["company_slug"] for row in payload["sections"]["risk_signals"]["items"]}, {"netflix"})
        self.assertEqual([row["slug"] for row in payload["sections"]["company_situations"]["items"]], ["disney"])

    def test_rebuild_specific_turns_unlocks_pattern_scorecard_and_compare(self):
        peer = Company.objects.create(name="Example Streaming", industry=self.netflix.industry, country="United States")
        peer_source = SourceDocument.objects.create(
            company=peer, source_api="SEC", url="https://example.com/example-streaming-10k",
            title="Example Streaming 10-K", publisher="SEC", language="en",
        )
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
        BusinessEvent.objects.create(
            company=peer, source_document=peer_source, event_type="REVENUE_MODEL_EXPANSION",
            event_date="2023-04-01", decision_theme="AD_SUPPORTED_PLAN",
            actual_change="Example Streaming launched an ad-supported subscription plan.",
            source_claim="Example Streaming announced its advertising plan.",
            evidence_text="Example Streaming launched an ad-supported plan in April 2023.",
            confidence_score="0.850", review_status="NEEDS_REVIEW",
        )

        call_command("rebuild_specific_turns", company="netflix")
        call_command("rebuild_specific_turns", company=peer.slug)
        response = self.client.get("/dashboard-data")
        payload = response.json()

        self.assertEqual(payload["sections"]["strategic_turns"]["status"], "available")
        self.assertEqual(payload["sections"]["patterns"]["status"], "available")
        self.assertEqual(payload["sections"]["scorecards"]["status"], "available")
        self.assertEqual(payload["sections"]["compare"]["status"], "available")
        self.assertGreaterEqual(payload["sections"]["compare"]["items"][0]["sample_size"], 2)
        self.assertGreaterEqual(payload["sections"]["compare"]["items"][0]["company_count"], 2)
        self.assertEqual(
            {row["company"] for row in payload["sections"]["compare"]["items"][0]["turns"]},
            {"Netflix", "Example Streaming"},
        )


class WikidataCompanyProfileTests(TestCase):
    def test_normalize_company_entity_extracts_profile_claims(self):
        entity = {
            "id": "Q1",
            "labels": {"en": {"value": "Example Corp"}},
            "descriptions": {"en": {"value": "An example company."}},
            "aliases": {"en": [{"value": "Example"}]},
            "claims": {
                "P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}],
                "P452": [{"mainsnak": {"datavalue": {"value": {"id": "Q100"}}}}],
                "P355": [{"mainsnak": {"datavalue": {"value": {"id": "Q200"}}}}],
                "P1056": [{"mainsnak": {"datavalue": {"value": {"id": "Q300"}}}}],
                "P1716": [{"mainsnak": {"datavalue": {"value": {"id": "Q400"}}}}],
                "P169": [{"mainsnak": {"datavalue": {"value": {"id": "Q500"}}}}],
                "P571": [{"mainsnak": {"datavalue": {"value": {"time": "+1999-01-15T00:00:00Z"}}}}],
                "P856": [{"mainsnak": {"datavalue": {"value": "https://example.com"}}}],
            },
        }
        labels = {
            "Q30": "United States",
            "Q100": "Technology",
            "Q200": "Example Subsidiary",
            "Q300": "Example Product",
            "Q400": "Example Brand",
            "Q500": "Example CEO",
        }

        company = normalize_company_entity(entity, claim_labels=labels)

        self.assertEqual(company.founded_date, date(1999, 1, 15))
        self.assertEqual(company.subsidiaries, ("Example Subsidiary",))
        self.assertEqual(company.products, ("Example Product",))
        self.assertEqual(company.brands, ("Example Brand",))
        self.assertEqual(company.leadership, ("Example CEO",))


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
    def test_configured_universe_has_reviewed_core_profile_normalization(self):
        for seed in CROSS_SECTOR_COMPANIES:
            fallback = PROFILE_FALLBACKS[slugify(seed.name)]
            self.assertGreaterEqual(len(fallback["business_model"]), 80, seed.name)
            self.assertTrue(fallback["brands"], seed.name)
            self.assertTrue(fallback["products"], seed.name)

    def test_parse_sec_profile_text_extracts_functional_company_sections(self):
        text = """
        ITEM 1. Business Example Corp is a diversified services company with operations in three segments:
        Entertainment, Sports and Experiences. ENTERTAINMENT The Entertainment segment produces film and episodic content.
        •Direct-to-Consumer: Example+ offers subscription programming. •Content Sales/Licensing - Fees charged to
        television distributors and subscribers. The revenues of Entertainment are as follows:
        •Subscription fees - Fees charged to customers/subscribers for streaming services.
        •Advertising - Sales of advertising time and space. The company has a 50% equity investment in Example Media.
        Example Corp competes with television networks, streaming services and theatrical studios for audiences and talent.
        Jane Doe, Chief Executive Officer, leads the company. ITEM 1A. Risk Factors
        """

        data = parse_sec_profile_text(text, "Example Corp", priorities=("Expand direct-to-consumer services.",))

        self.assertEqual(data.segments, ("Entertainment", "Sports", "Experiences"))
        self.assertIn("Subscription fees", data.revenue_sources)
        self.assertIn("Advertising", data.revenue_sources)
        self.assertIn("Example Media", data.subsidiaries)
        self.assertIn("Jane Doe, Chief Executive Officer", data.leadership)
        self.assertEqual(data.strategic_priorities, ("Expand direct-to-consumer services.",))

    def test_reviewed_company_fallbacks_replace_unvalidated_parser_fields(self):
        empty = SecProfileData("", (), (), (), (), (), (), (), (), (), "filing evidence")

        data = apply_profile_fallbacks(empty, "microsoft")

        self.assertIn("Azure", data.brands)
        self.assertIn("Intelligent Cloud", data.segments)
        self.assertEqual(data.evidence_text, "filing evidence")

        malformed = SecProfileData("", (), ("The", "Our", "Company"), (), ("The", "Resource"), (), (), (), (), (), "filing evidence")
        caterpillar = apply_profile_fallbacks(malformed, "caterpillar")
        self.assertEqual(caterpillar.brands, ("Caterpillar", "Cat"))
        self.assertIn("Mining equipment", caterpillar.products)
        self.assertNotIn("The", caterpillar.products)

    def test_product_parser_does_not_publish_capitalized_prose_fragments(self):
        text = """
        ITEM 1. Business Products and Services The Resource Industries division
        competes with Deere Construction and Forestry Company, Epiroc, Hitachi
        Construction Machinery Ltd., Komatsu, Liebherr and Sandvik. Customers
        purchase equipment through independent dealers. ITEM 1A. Risk Factors
        """

        data = parse_sec_profile_text(text, "Example Corp")

        self.assertEqual(data.products, ())
        self.assertEqual(data.brands, ())

    def test_semantic_quality_rejects_filing_boilerplate_and_duplicate_labels(self):
        company = Company.objects.create(name="Quality Corp", description="A reviewed company summary.")
        source = SourceDocument.objects.create(
            company=company, source_api="SEC", url="https://example.com/10-k", title="Quality Corp 10-K"
        )
        CompanyProfileSnapshot.objects.create(
            company=company,
            effective_date=date(2025, 12, 31),
            source_document=source,
            status="REVIEWED",
            summary="A reviewed company summary.",
            business_model="Documents Incorporated By Reference and other filing boilerplate that is not a business model.",
            subsidiaries=["Quality Subsidiary"],
            brands=["Quality Brand"],
            segments=["Quality Segment"],
            products=["Product Product"],
            customer_groups=["Business customers"],
            revenue_sources=["Product sales"],
            geographies=["United States"],
            leadership=["Chief Executive Officer"],
            competitors=["Industry competitors"],
            strategic_priorities=["Expand the product portfolio"],
        )

        issues = company_profile_quality_issues(company)

        self.assertIn("business model summary contains filing boilerplate", issues)
        self.assertIn("products contains duplicated words: Product Product", issues)
        self.assertIn("reviewed Business Model Map unavailable", issues)

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

    def test_collect_official_company_profile_persists_reviewed_structured_evidence(self):
        company = Company.objects.create(name="ExampleCo", website="https://example.com")
        session = FakeProfileSession()

        snapshot = collect_official_company_profile(company, session=session)

        self.assertEqual(snapshot.status, "REVIEWED")
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

        self.assertEqual(snapshot.status, "REVIEWED")
        self.assertEqual(snapshot.components.count(), 4)
        self.assertEqual(snapshot.relationships.count(), 3)
        self.assertTrue(all(row.is_inferred for row in snapshot.relationships.all()))

    def test_business_model_builder_creates_complete_reviewed_sector_map(self):
        company = Company.objects.create(name="IndustrialCo", industry="Industrials")
        source = SourceDocument.objects.create(company=company, source_api="SEC", url="https://example.com/10-k", title="IndustrialCo 10-K")
        CompanyProfileSnapshot.objects.create(
            company=company, effective_date=date(2025, 12, 31), source_document=source, status="REVIEWED",
            business_model="IndustrialCo sells equipment and services.", products=["Equipment"],
            customer_groups=["Industrial customers"], revenue_sources=["Equipment sales"], geographies=["United States"],
            evidence_text="IndustrialCo 10-K business description.", confidence_score="0.800",
        )

        snapshot = build_business_model_from_profile(company)

        self.assertEqual(snapshot.status, "REVIEWED")
        self.assertEqual(set(snapshot.components.values_list("component_type", flat=True)), {
            "PAYER", "USER", "OFFERING", "REVENUE", "CHANNEL", "GEOGRAPHY", "PARTNER", "COST", "ASSET"
        })
        self.assertTrue(snapshot.relationships.exists())

    def test_business_model_builder_replaces_newer_boilerplate_with_reviewed_summary(self):
        company = Company.objects.create(name="Microsoft", industry="Information Technology")
        sec_source = SourceDocument.objects.create(
            company=company, source_api="SEC", url="https://example.com/10-k", title="Microsoft 10-K"
        )
        current_source = SourceDocument.objects.create(
            company=company, source_api="OFFICIAL_WEBSITE", url="https://example.com", title="Microsoft profile"
        )
        CompanyProfileSnapshot.objects.create(
            company=company, effective_date=date(2025, 12, 31), source_document=sec_source, status="REVIEWED",
            business_model="A valid older summary.", products=["Software"], customer_groups=["Businesses"],
            revenue_sources=["Subscriptions"], geographies=["Worldwide"], evidence_text="10-K evidence."
        )
        CompanyProfileSnapshot.objects.create(
            company=company, effective_date=date(2026, 1, 31), source_document=current_source, status="REVIEWED",
            business_model="Securities registered pursuant to Section 12(b).", evidence_text="Current source."
        )

        snapshot = build_business_model_from_profile(company)

        self.assertEqual(snapshot.effective_date, date(2026, 1, 31))
        self.assertTrue(snapshot.summary.startswith("Microsoft develops and licenses software"))
        self.assertIn("Microsoft 365", snapshot.components.filter(component_type="OFFERING").values_list("name", flat=True))

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

    def test_collect_kpi_structured_sources_require_review_before_publication(self):
        company = Company.objects.create(name="MetricCo")
        csv_kpi, csv_count = collect_kpi_csv(
            company, url="https://example.com/metrics.csv", metric_slug="users", metric_name="Users",
            unit="million", session=FakeKpiSession("csv"),
        )
        html_kpi, html_count = collect_kpi_html_table(
            company, url="https://example.com/metrics.html", metric_slug="accounts", metric_name="Accounts",
            unit="million", session=FakeKpiSession("html"),
        )

        self.assertEqual((csv_count, html_count), (2, 2))
        self.assertFalse(csv_kpi.is_active)
        self.assertFalse(html_kpi.is_active)
        self.assertTrue(all(row.is_non_comparable for row in csv_kpi.observations.all()))


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


class FakeKpiSession:
    def __init__(self, mode):
        self.mode = mode
        self.headers = {}

    def get(self, url, timeout):
        if url.endswith("robots.txt"):
            return FakeProfileResponse(url=url, text="User-agent: *\nAllow: /")
        if self.mode == "html":
            text = "<table><tr><th>period_end</th><th>value</th></tr><tr><td>2025-03-31</td><td>10</td></tr><tr><td>2025-06-30</td><td>12</td></tr></table>"
        else:
            text = "period_end,value\n2025-03-31,10\n2025-06-30,12\n"
        return FakeProfileResponse(url=url, text=text)


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

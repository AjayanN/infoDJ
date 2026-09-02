from __future__ import annotations

from datetime import date
import os
from unittest.mock import patch
from types import SimpleNamespace

from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.utils.text import slugify

from apps.companies.company_universe import CROSS_SECTOR_COMPANIES
from apps.companies.models import (
    AcquisitionLifecycleDeal,
    BusinessModelComponent,
    BusinessModelRelationship,
    BusinessModelSnapshot,
    CapitalAllocationItem,
    CapitalAllocationPeriod,
    Company,
    CompanyProfileSnapshot,
    CompetitivePeer,
    CompetitivePositionSnapshot,
    CustomerSupplierDependencySnapshot,
    EarningsGuidanceComparison,
    EarningsPeriod,
    EarningsPeriodDocument,
    GeographicExpansionSnapshot,
    KpiComparability,
    KpiDefinition,
    KpiDefinitionVersion,
    KpiObservation,
    KpiTarget,
    LeadershipDecisionSnapshot,
    ManagementPromise,
    ManagementPromiseUpdate,
    OwnershipInsiderSnapshot,
    ProductCatalogSnapshot,
    ProductOffering,
    MacroSensitivitySnapshot,
    RegulatoryLitigationSnapshot,
    SectorThemeSnapshot,
    StrategyMilestone,
    ValuationContextSnapshot,
    ValuationEventSnapshot,
)
from apps.curation.models import BusinessEvent, EventType, LifecycleEpisode, StrategicTurn, StrategicTurnSource
from apps.ingestion.models import (
    ArticleExtraction,
    EvidenceRecord,
    FinancialFact,
    MarketPrice,
    SourceDocument,
    SourceGap,
    SourceGapResolutionCandidate,
)
from apps.ingestion.services.dashboard_quality import event_eligibility, lifecycle_timing_eligibility
from apps.ingestion.services.lifecycle_timing import exact_action_date_from_evidence, lifecycle_context_from_financial_facts
from apps.ingestion.services.capital_allocation import (
    build_capital_allocation_periods,
    capital_allocation_quality_issues,
)
from apps.ingestion.services.competitive_position import (
    build_competitive_position,
    competitive_position_quality_issues,
)
from apps.ingestion.services.product_pricing_history import (
    build_product_pricing_history,
    product_pricing_quality_issues,
)
from apps.ingestion.services.acquisition_lifecycle import (
    build_acquisition_lifecycle,
    acquisition_lifecycle_quality_issues,
)
from apps.ingestion.services.customer_supplier_dependency import (
    build_customer_supplier_dependency,
    customer_supplier_dependency_quality_issues,
)
from apps.ingestion.services.geographic_expansion import (
    build_geographic_expansion,
    geographic_expansion_quality_issues,
)
from apps.ingestion.services.ownership_insider_activity import (
    build_ownership_insider_activity,
    ownership_insider_quality_issues,
)
from apps.ingestion.services.leadership_decision_record import (
    build_leadership_decision_record,
    leadership_decision_quality_issues,
)
from apps.ingestion.services.valuation_context import build_valuation_context, valuation_quality_issues
from apps.ingestion.services.regulatory_litigation import build_regulatory_litigation_calendar, regulatory_litigation_quality_issues
from apps.ingestion.services.sector_theme_intelligence import build_sector_theme_intelligence, sector_theme_quality_issues
from apps.ingestion.services.macro_sensitivity_profile import build_macro_sensitivity_profile, macro_sensitivity_quality_issues
from apps.ingestion.services.source_gap_resolver import SOURCE_RULES, resolve_source_gaps
from apps.ingestion.services.source_gap_source_collector import forms_for_gap, ticker_for
from apps.ingestion.services.source_gap_candidate_extractor import extract_source_gap_candidates, full_text_excerpt, lifecycle_timing_excerpt
from apps.ingestion.services.source_gap_candidate_promoter import (
    parse_dependency_contract_terms,
    parse_dependency_concentrations,
    parse_ownership_rows,
    promote_source_gap_candidates,
)
from apps.ingestion.services.event_extractor import EventSignal, actual_change_for, find_evidence_sentence
from apps.ingestion.services.earnings_intelligence import (
    build_earnings_periods,
    earnings_quality_issues,
    is_earnings_release,
    is_exhibit_99,
    management_driver_excerpt,
    publish_reviewed_earnings_excerpt,
)
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
from apps.ingestion.services.reviewed_strategy_milestones import (
    REVIEWED_MILESTONE_SPECS,
    build_reviewed_strategy_milestone,
    strategy_milestone_quality_issues,
)
from apps.ingestion.services.market_price_client import (
    parse_alpha_vantage_daily_csv,
    parse_fmp_historical_prices,
)
from apps.ingestion.services.fmp_fundamentals import FUNDAMENTAL_SERIES, parse_fmp_fundamental_facts
from apps.ingestion.services.sec_form4 import (
    form4_sources,
    ingest_form4_sources,
    ownership_xml_candidates,
    ownership_xml_url,
    parse_ownership_holdings,
    parse_ownership_xml,
)
from apps.ingestion.management.commands.ingest_market_prices import build_market_client
from apps.ingestion.management.commands.daily_company_update import Command as DailyCompanyUpdateCommand
from apps.ingestion.management.commands.ingest_sec_form4 import Command as SecForm4Command
from apps.ingestion.services.official_product_price import parse_official_prices
from apps.ingestion.services.energy_source_quality import is_promotable_energy_candidate
from apps.ingestion.services.energy_sector_enrichment import enrich_energy_disclosures
from apps.ingestion.services.sec_profile_builder import (
    SecProfileData,
    apply_profile_fallbacks,
    build_sec_company_profile,
    parse_sec_profile_text,
)
from apps.ingestion.services.sec_edgar_client import discover_sec_filings_for_company
from apps.ingestion.services.wikidata_client import WikidataCompany, _apply_company_details, normalize_company_entity


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

    def test_company_universe_activation_is_idempotent(self):
        self.netflix.is_active = False
        self.netflix.save(update_fields=["is_active"])

        call_command("activate_company_universe")
        call_command("activate_company_universe")

        self.assertEqual(Company.objects.filter(is_active=True).count(), len(CROSS_SECTOR_COMPANIES))
        self.assertTrue(Company.objects.get(slug="netflix").is_active)
        self.assertEqual(Company.objects.get(slug="exxonmobil").sec_cik, "0000034088")

    def test_sec_discovery_prefers_a_configured_cik_over_ticker_lookup(self):
        company = Company.objects.create(name="Configured CIK Corp", sec_cik="34088")

        class ConfiguredCikClient:
            def all_filings(self, cik, **kwargs):
                self.cik = cik
                return []

        client = ConfiguredCikClient()
        discover_sec_filings_for_company(
            company=company,
            source_document_model=SourceDocument,
            ticker="XOM",
            forms=("10-K",),
            full_history=True,
            client=client,
        )

        self.assertEqual(client.cik, "0000034088")
        company.refresh_from_db()
        self.assertEqual(company.sec_cik, "0000034088")

    def test_evidence_ledger_indexes_existing_curated_records_idempotently(self):
        call_command("build_evidence_ledger", company="netflix")
        call_command("build_evidence_ledger", company="netflix")

        records = EvidenceRecord.objects.filter(company=self.netflix)
        self.assertEqual(records.filter(record_type="BUSINESS_EVENT").count(), 1)
        self.assertEqual(records.filter(record_type="STRATEGIC_TURN").count(), 2)
        self.assertEqual(records.filter(record_type="FINANCIAL_FACT").count(), 1)
        self.assertTrue(records.filter(source_document=self.source).exists())

    def test_strategy_milestone_build_treats_missing_reviewed_evidence_as_a_skip(self):
        call_command("build_strategy_milestones")

        with self.assertRaises(CommandError):
            call_command("build_strategy_milestones", strict=True)

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
            operating_regions=["UCAN", "EMEA", "LATAM", "APAC"],
            revenue_geographies=["UCAN", "EMEA", "LATAM", "APAC"],
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

    def test_company_profile_coverage_reports_its_current_snapshot_contract(self):
        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        coverage = response.json()["coverage"]
        self.assertEqual(coverage["scoring_contract"]["snapshot_limit"], 20)
        self.assertEqual(coverage["scoring_contract"]["eligible_snapshot_count"], 0)
        self.assertIn("business_model", coverage["missing_sections"])
        self.assertEqual(coverage["section_statuses"]["business_model"], "unavailable")

    def test_company_coverage_separates_headquarters_from_operating_regions(self):
        self.netflix.headquarters_country = "United States"
        self.netflix.save(update_fields=["headquarters_country"])
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            operating_regions=["UCAN", "EMEA", "LATAM", "APAC"],
            revenue_geographies=["UCAN", "EMEA", "LATAM", "APAC"],
        )

        response = self.client.get("/companies/netflix/coverage")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["company"]["headquarters_country"], "United States")
        dimensions = {item["key"]: item for item in payload["coverage"]["dimensions"]}
        self.assertEqual(dimensions["headquarters_country"]["status"], "available")
        self.assertEqual(dimensions["operating_regions"]["status"], "available")
        self.assertEqual(dimensions["revenue_geographies"]["status"], "available")

    def test_company_profile_reports_partial_section_gaps(self):
        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["sections"]["geographies"]["status"], "unavailable")
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

    def test_company_profile_ignores_empty_snapshots_when_selecting_current_sections(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            summary="Netflix is a global entertainment service.",
            products=["Streaming plans"],
            revenue_sources=["Subscriptions"],
        )
        for index in range(25):
            CompanyProfileSnapshot.objects.create(
                company=self.netflix,
                effective_date=date(2025 + (index // 12), (index % 12) + 1, 1),
                source_document=self.source,
                status="REVIEWED",
            )

        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sections"]["products"]["items"], ["Streaming plans"])
        self.assertEqual(response.json()["coverage"]["scoring_contract"]["eligible_snapshot_count"], 1)

    def test_company_profile_combines_latest_meaningful_snapshot_per_source_type(self):
        sec_source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="SEC",
            url="https://example.com/netflix-2024-10k",
            title="Netflix 2024 10-K",
        )
        official_source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="OFFICIAL_WEBSITE",
            url="https://example.com/netflix-about",
            title="Netflix about",
        )
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2024, 12, 31),
            source_document=sec_source,
            status="REVIEWED",
            summary="Netflix is a global entertainment service.",
            products=["Streaming plans"],
            revenue_sources=["Subscriptions"],
        )
        for index in range(25):
            CompanyProfileSnapshot.objects.create(
                company=self.netflix,
                effective_date=date(2025 + (index // 12), (index % 12) + 1, 1),
                source_document=official_source,
                status="REVIEWED",
                summary=f"Official profile refresh {index}.",
            )

        response = self.client.get("/companies/netflix/profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sections"]["products"]["items"], ["Streaming plans"])
        self.assertEqual(response.json()["sections"]["revenue_sources"]["items"], ["Subscriptions"])
        self.assertEqual(response.json()["coverage"]["scoring_contract"]["eligible_snapshot_count"], 2)

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
        ProductCatalogSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2022, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            summary="Reviewed product and pricing history.",
            confidence_score="0.800",
        )
        CustomerSupplierDependencySnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2022, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            summary="Reviewed customer and supplier dependency map.",
            confidence_score="0.800",
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
        self.assertTrue(payload["changes"]["has_material_change"])
        self.assertEqual(payload["changes"]["comparison_status"], "material_change")
        self.assertEqual(payload["changes"]["last_material_change_date"], "2011-12-31")
        self.assertEqual(payload["peer_models"][0]["company"], "StreamPeer")
        self.assertEqual(payload["peer_models"][0]["shared_components"][0]["name"], "streaming members")
        self.assertEqual(payload["peer_models"][0]["compatibility_status"], "incompatible")
        self.assertIn("same-sector context only", payload["peer_models"][0]["comparison_warning"])
        self.assertEqual(payload["peer_models"][0]["shared_component_type_count"], 1)
        self.assertLess(payload["peer_models"][0]["component_type_overlap_percent"], 50)
        related = {row["key"]: row for row in payload["related_surfaces"]}
        self.assertEqual(related["pricing_history"]["status"], "available")
        self.assertEqual(related["pricing_history"]["destination"], "product_pricing")
        self.assertEqual(related["pricing_history"]["action_label"], "Open product and pricing")
        self.assertEqual(related["supplier_dependency"]["status"], "available")
        self.assertEqual(related["supplier_dependency"]["destination"], "customer_supplier_dependency")
        self.assertEqual(related["supplier_dependency"]["action_label"], "Open dependency map")
        self.assertFalse(any(str(row["destination"]).startswith("phase2_requirement_") for row in payload["related_surfaces"]))

    def test_business_model_marks_repeated_refresh_without_fake_changes(self):
        older = BusinessModelSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2011, 12, 31),
            source_document=self.source,
            status="REVIEWED",
            summary="DVD subscriptions.",
            confidence_score="0.800",
        )
        BusinessModelComponent.objects.create(snapshot=older, component_type="OFFERING", name="DVD-by-mail", confidence_score="0.8")

        first_refresh = BusinessModelSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 6, 15),
            source_document=self.source,
            status="REVIEWED",
            summary="Streaming subscriptions and advertising.",
            confidence_score="0.900",
        )
        second_refresh = BusinessModelSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 6, 22),
            source_document=self.source,
            status="REVIEWED",
            summary="Streaming subscriptions and advertising.",
            confidence_score="0.900",
        )
        for snapshot in (first_refresh, second_refresh):
            payer = BusinessModelComponent.objects.create(snapshot=snapshot, component_type="PAYER", name="Streaming members", confidence_score="0.9")
            offering = BusinessModelComponent.objects.create(snapshot=snapshot, component_type="OFFERING", name="Streaming service", confidence_score="0.9")
            BusinessModelRelationship.objects.create(snapshot=snapshot, from_component=payer, to_component=offering, relationship_type="USES", confidence_score="0.9")

        response = self.client.get("/companies/netflix/business-model?as_of=2026-06-22&compare_to=2026-06-15")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        changes = payload["changes"]
        self.assertFalse(changes["has_material_change"])
        self.assertEqual(changes["comparison_status"], "no_structural_change")
        self.assertEqual(changes["last_material_change_date"], "2011-12-31")
        self.assertEqual(changes["components_added"], [])
        self.assertEqual(changes["components_removed"], [])
        self.assertEqual(changes["relationships_added"], [])
        self.assertEqual(changes["relationships_removed"], [])
        self.assertIn("identical component and relationship sets", changes["comparison_message"])
        self.assertEqual(len(payload["evidence"]), 1)
        self.assertEqual(payload["evidence"][0]["id"], self.source.id)
        self.assertEqual(payload["evidence"][0]["evidence_context"], ["Current map", "Comparison map", "Last material baseline"])
        self.assertEqual(payload["evidence"][0]["snapshot_dates"], ["2026-06-22", "2026-06-15", "2011-12-31"])

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

    def test_operating_kpis_blocks_unreviewed_same_sector_peer_metrics(self):
        metric = KpiDefinition.objects.create(
            company=self.netflix, slug="paid-memberships", name="Paid memberships",
            description="Period-end paid memberships.", unit="million", cadence="QUARTERLY",
            value_type="REPORTED", scope="Global streaming", peer_comparable=True,
        )
        KpiObservation.objects.create(
            kpi=metric, period_start=date(2022, 1, 1), period_end=date(2022, 3, 31),
            fiscal_year=2022, fiscal_period="Q1", value="220", source_document=self.source,
            confidence_score="0.9",
        )
        peer = Company.objects.create(name="StreamPeer", industry=self.netflix.industry)
        KpiDefinition.objects.create(
            company=peer, slug="paid-memberships", name="Paid memberships",
            description="Similar label without reviewed definition mapping.", unit="million",
            cadence="QUARTERLY", value_type="REPORTED", scope="Streaming", peer_comparable=True,
        )

        response = self.client.get("/companies/netflix/operating-kpis?metric=paid-memberships")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["peer_comparisons"], [])
        self.assertEqual(payload["blocked_peer_metrics"][0]["company"], "StreamPeer")
        self.assertIn("no reviewed comparability record", payload["blocked_peer_metrics"][0]["reason"])
        self.assertIn("peer normalization is blocked", payload["peer_comparison_warning"])

    def test_operating_kpis_shows_only_reviewed_comparable_peer_metrics(self):
        metric = KpiDefinition.objects.create(
            company=self.netflix, slug="paid-memberships", name="Paid memberships",
            description="Period-end paid memberships.", unit="million", cadence="QUARTERLY",
            value_type="REPORTED", scope="Global streaming", peer_comparable=True,
        )
        KpiObservation.objects.create(
            kpi=metric, period_start=date(2022, 1, 1), period_end=date(2022, 3, 31),
            fiscal_year=2022, fiscal_period="Q1", value="220", source_document=self.source,
            confidence_score="0.9",
        )
        peer = Company.objects.create(name="StreamPeer", industry=self.netflix.industry)
        peer_metric = KpiDefinition.objects.create(
            company=peer, slug="paid-memberships", name="Paid memberships",
            description="Period-end paid memberships.", unit="million", cadence="QUARTERLY",
            value_type="REPORTED", scope="Global streaming", peer_comparable=True,
        )
        KpiComparability.objects.create(
            kpi=metric, comparable_kpi=peer_metric, is_comparable=True,
            rationale="Both definitions measure period-end paid memberships in millions.",
            reviewed_at=date(2026, 7, 4),
        )

        response = self.client.get("/companies/netflix/operating-kpis?metric=paid-memberships")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["peer_comparisons"][0]["company"], "StreamPeer")
        self.assertEqual(payload["peer_comparisons"][0]["reviewed_at"], "2026-07-04")
        self.assertEqual(payload["blocked_peer_metrics"], [])
        self.assertIn("matching definition", payload["peer_comparison_warning"])

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
        self.assertEqual(payload["selected_promise"]["linked_kpi"]["dependency_label"], "Promise evaluation metric")
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

    def test_sec_form4_command_discovers_ownership_forms_before_parsing(self):
        with patch(
            "apps.ingestion.management.commands.ingest_sec_form4.discover_sec_filings_for_company",
            return_value={"sources_found": 2, "sources_inserted": 2, "duplicates_skipped": 0},
        ) as discover, patch(
            "apps.ingestion.management.commands.ingest_sec_form4.form4_sources", return_value=[]
        ), patch(
            "apps.ingestion.management.commands.ingest_sec_form4.ingest_form4_sources",
            return_value={
                "sources_seen": 0,
                "sources_parsed": 0,
                "sources_failed": 0,
                "transactions_found": 0,
                "transactions_inserted": 0,
                "transactions_updated": 0,
                "holdings_found": 1,
                "holdings_inserted": 1,
                "holdings_updated": 0,
            },
        ):
            SecForm4Command().handle(company="netflix", all=False, limit=10, offset=0, company_limit=0)

        self.assertEqual(discover.call_args.kwargs["forms"], ("3", "3/A", "4", "4/A", "5", "5/A"))
        self.assertEqual(discover.call_args.kwargs["ticker"], "NFLX")

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

    def test_reviewed_promise_builder_matches_updated_general_electric_filing_language(self):
        company = Company.objects.create(name="General Electric", slug="general-electric")
        source = SourceDocument.objects.create(
            company=company,
            source_api="SEC_EDGAR",
            url="https://example.com/general-electric-10k",
            title="General Electric 10-K filing",
            publisher="SEC EDGAR",
        )
        ArticleExtraction.objects.create(
            source_document=source,
            clean_text=(
                "We are committed to investing and developing technologies that improve safety, durability, "
                "reliability and efficiency for our current engine products over their lifecycle and for the future of flight."
            ),
            word_count=24,
            extraction_status="SUCCEEDED",
        )

        result = build_reviewed_management_promise(company)

        self.assertEqual(result["created"], 1)
        self.assertTrue(ManagementPromise.objects.filter(company=company, is_published=True).exists())

    def test_reviewed_milestone_catalog_covers_every_configured_company(self):
        expected = {slugify(seed.name) for seed in CROSS_SECTOR_COMPANIES}

        self.assertEqual(set(REVIEWED_MILESTONE_SPECS), expected)

    def test_reviewed_milestone_builder_preserves_unknown_date_and_status_history(self):
        promise = ManagementPromise.objects.create(
            company=self.netflix, slug="offer-ad-plan", title="Offer an ad-supported plan",
            promise_type="COMMITMENT", original_statement="We aim to offer an ad-supported plan.",
            statement_date=date(2026, 1, 1), current_status="IN_PROGRESS", source_document=self.source,
            evidence_text="We aim to offer an ad-supported plan.", review_status="REVIEWED", is_published=True,
        )

        first = build_reviewed_strategy_milestone(self.netflix)
        second = build_reviewed_strategy_milestone(self.netflix)
        milestone = StrategyMilestone.objects.get(company=self.netflix)

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertEqual(milestone.current_status, "STARTED")
        self.assertIsNone(milestone.expected_end_date)
        self.assertEqual(milestone.date_precision, "UNKNOWN")
        self.assertEqual(milestone.linked_promise, promise)
        self.assertEqual(milestone.status_updates.count(), 1)
        self.assertEqual(strategy_milestone_quality_issues(self.netflix), [])

    def test_reviewed_milestone_builder_carries_reviewed_promise_updates(self):
        promise = ManagementPromise.objects.create(
            company=self.netflix, slug="launch-basic-with-ads", title="Launch Basic with Ads in 12 countries",
            promise_type="COMMITMENT", original_statement="We will launch Basic with Ads in 12 countries.",
            statement_date=date(2022, 10, 13), target_end_date=date(2022, 11, 30),
            current_status="ACHIEVED", source_document=self.source, evidence_text="We will launch Basic with Ads in 12 countries.",
            review_status="REVIEWED", is_published=True,
        )
        ManagementPromiseUpdate.objects.create(
            promise=promise, update_date=date(2022, 11, 3), status="ACHIEVED",
            summary="Netflix launched Basic with Ads during the announced window.", source_document=self.source,
            evidence_text="Netflix launched Basic with Ads on November 3, 2022.", confidence_score="0.900",
            review_status="REVIEWED",
        )

        build_reviewed_strategy_milestone(self.netflix)
        milestone = StrategyMilestone.objects.get(company=self.netflix)

        self.assertEqual(milestone.current_status, "COMPLETED")
        self.assertEqual(list(milestone.status_updates.values_list("status", flat=True)), ["EXPECTED", "COMPLETED"])
        self.assertEqual(milestone.status_updates.last().status_date, date(2022, 11, 3))

    def test_strategy_milestone_api_exposes_history_and_does_not_mark_unknown_date_overdue(self):
        ManagementPromise.objects.create(
            company=self.netflix, slug="offer-ad-plan", title="Offer an ad-supported plan",
            promise_type="COMMITMENT", original_statement="We aim to offer an ad-supported plan.",
            statement_date=date(2026, 1, 1), current_status="IN_PROGRESS", source_document=self.source,
            evidence_text="We aim to offer an ad-supported plan.", review_status="REVIEWED", is_published=True,
        )
        build_reviewed_strategy_milestone(self.netflix)

        payload = self.client.get("/companies/netflix/strategy-milestones").json()
        overdue = self.client.get("/companies/netflix/strategy-milestones?view=overdue").json()

        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["coverage"]["unknown_date_count"], 1)
        self.assertEqual(payload["coverage"]["overdue_count"], 0)
        self.assertEqual(payload["selected_milestone"]["origin"], "MANAGEMENT_ANNOUNCED")
        self.assertEqual(len(payload["selected_milestone"]["status_history"]), 1)
        self.assertEqual(overdue["status"], "unavailable")

    def test_earnings_builder_creates_source_backed_period_and_api_separates_evidence_types(self):
        quarterly_source = SourceDocument.objects.create(
            company=self.netflix, source_api="SEC_EDGAR", url="https://example.com/000106528026000001",
            title="Netflix 10-Q filing 2026-04-20 - 10-Q", publisher="SEC",
            published_date="2026-04-20T00:00:00Z", language="en",
        )
        for concept, label, value in (("Revenues", "Revenue", "120"), ("NetIncomeLoss", "Net income", "25")):
            FinancialFact.objects.create(
                company=self.netflix, taxonomy="us-gaap", concept=concept, label=label, unit="USD",
                fy=2026, fp="Q1", filed=date(2026, 4, 20), frame="CY2026Q1", value=value,
                accession_number="0001065280-26-000001",
                raw={"start": "2026-01-01", "end": "2026-03-31", "form": "10-Q", "fp": "Q1", "fy": 2026},
            )
        kpi = KpiDefinition.objects.create(
            company=self.netflix, slug="paid-memberships", name="Paid memberships",
            description="Period-end paid memberships.", unit="million", cadence="QUARTERLY",
            value_type="REPORTED", scope="Global streaming",
        )
        KpiObservation.objects.create(
            kpi=kpi, period_start=date(2026, 1, 1), period_end=date(2026, 3, 31),
            fiscal_year=2026, fiscal_period="Q1", value="270", source_document=quarterly_source,
            confidence_score="0.9",
        )

        first = build_earnings_periods(self.netflix)
        second = build_earnings_periods(self.netflix)
        response = self.client.get("/companies/netflix/earnings")

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertTrue(any("reviewed management explanation unavailable" in issue for issue in earnings_quality_issues(self.netflix)))
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["selected_period"]["fiscal_period"], "Q1")
        self.assertEqual(len(payload["selected_period"]["measured_results"]), 2)
        self.assertEqual(payload["selected_period"]["operating_kpis"][0]["dependency_label"], "Operating KPI movement for this earnings period")
        self.assertIsNone(payload["selected_period"]["management_explanation"])
        self.assertIsNone(payload["selected_period"]["infodj_interpretation"])
        self.assertEqual(len(payload["selected_period"]["unanswered_questions"]), 2)
        self.assertIn("disclosure_changes", payload["selected_period"])
        self.assertEqual(payload["selected_period"]["document_set"][0]["source"]["id"], quarterly_source.id)
        self.assertTrue(any(gap["key"] == "management_explanation" for gap in payload["source_gaps"]))

    def test_earnings_api_exposes_pending_official_management_excerpt(self):
        period = EarningsPeriod.objects.create(
            company=self.netflix, fiscal_year=2026, fiscal_period="Q1", period_end=date(2026, 3, 31),
            filed_date=date(2026, 4, 20), accession_number="0001065280-26-000001",
            headline="Netflix reported Q1 results.", source_document=self.source,
            review_status="REVIEWED", is_published=True,
        )
        pending_source = SourceDocument.objects.create(
            company=self.netflix, source_api="SEC_EDGAR_EXHIBIT", url="https://example.com/q1-release",
            title="Netflix Q1 earnings release", publisher="SEC",
        )
        EarningsPeriodDocument.objects.create(
            period=period, source_document=pending_source, document_type="EARNINGS_EXHIBIT",
            evidence_text="Revenue grew, driven by higher membership and pricing.", review_status="NEEDS_REVIEW",
        )

        payload = self.client.get("/companies/netflix/earnings").json()

        self.assertIsNone(payload["selected_period"]["management_explanation"])
        self.assertEqual(
            payload["selected_period"]["pending_management_excerpt"]["evidence_text"],
            "Revenue grew, driven by higher membership and pricing.",
        )
        self.assertEqual(payload["selected_period"]["pending_management_excerpt"]["source"]["url"], pending_source.url)

    def test_earnings_api_reports_unavailable_without_reviewed_periods(self):
        response = self.client.get("/companies/netflix/earnings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(response.json()["periods"], [])

    def test_management_driver_excerpt_keeps_driver_language_and_excludes_risk_boilerplate(self):
        text = (
            "Revenue increased primarily due to higher subscription volume and pricing across our core markets. "
            "Operating income benefited from lower delivery costs and improved utilization during the quarter. "
            "Forward-looking results may be adversely affected by competition and regulatory risk factors."
        )

        excerpt = management_driver_excerpt(text)

        self.assertIn("primarily due to", excerpt)
        self.assertIn("benefited from", excerpt)
        self.assertNotIn("risk factors", excerpt)

    def test_management_driver_excerpt_rejects_non_operating_boilerplate(self):
        text = (
            "The tax benefit was driven by the resolution of certain tax audits and tax regulations. "
            "Dollar and percentage changes may not recalculate due to rounding. "
            "Revenue increased 17% year over year, driven by customer demand and higher pricing."
        )

        excerpt = management_driver_excerpt(text)

        self.assertEqual(excerpt, "Revenue increased 17% year over year, driven by customer demand and higher pricing.")

    def test_earnings_exhibit_validation_rejects_non_earnings_exhibits(self):
        extraction = ArticleExtraction(
            extraction_status="SUCCEEDED",
            word_count=150,
            clean_text="The issuer discusses an offering and its effect on future earnings. " * 20,
        )

        self.assertTrue(is_exhibit_99("company-ex99_1.htm"))
        self.assertFalse(is_exhibit_99("underwriting-ex1-1.htm"))
        self.assertFalse(is_earnings_release(extraction))

    def test_management_driver_excerpt_separates_guidance_and_reconciliation_text(self):
        text = (
            "Revenue grew 12%, driven by higher transaction volume and improved pricing. "
            "We expect revenue growth next quarter to be driven by new products. "
            "We calculate adjusted EBITDA by beginning with net earnings and reconciling non-GAAP items."
        )

        self.assertEqual(
            management_driver_excerpt(text),
            "Revenue grew 12%, driven by higher transaction volume and improved pricing.",
        )

    def test_review_catalog_publishes_exact_official_exhibit_text(self):
        period = EarningsPeriod.objects.create(
            company=self.netflix,
            fiscal_year=2026,
            fiscal_period="Q1",
            period_end=date(2026, 3, 31),
            filed_date=date(2026, 4, 20),
            accession_number="0001065280-26-000001",
            headline="Netflix reported first-quarter results.",
            source_document=self.source,
            review_status="REVIEWED",
            is_published=True,
        )
        exhibit_source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="SEC_EDGAR_EXHIBIT",
            url="https://example.com/netflix-ex991",
            title="Netflix earnings release",
            publisher="SEC",
        )
        evidence = "Revenue in Q1 grew 16% year over year, driven primarily by membership growth, higher pricing, and increased ad revenue."
        ArticleExtraction.objects.create(
            source_document=exhibit_source,
            clean_text=evidence,
            word_count=120,
            extraction_status="SUCCEEDED",
        )
        link = EarningsPeriodDocument.objects.create(period=period, source_document=exhibit_source)

        result = publish_reviewed_earnings_excerpt(self.netflix)

        link.refresh_from_db()
        self.assertEqual(result["reviewed"], 1)
        self.assertEqual(link.review_status, "REVIEWED")
        self.assertEqual(link.evidence_text, evidence)

    def test_earnings_api_keeps_forecast_and_actual_sources_separate(self):
        period = EarningsPeriod.objects.create(
            company=self.netflix, fiscal_year=2026, fiscal_period="Q1", period_end=date(2026, 3, 31),
            filed_date=date(2026, 4, 20), accession_number="0001065280-26-000001",
            headline="Netflix reported Q1 results.", source_document=self.source,
            review_status="REVIEWED", is_published=True,
        )
        forecast_source = SourceDocument.objects.create(
            company=self.netflix, source_api="SEC_EDGAR_EXHIBIT", url="https://example.com/q4-letter",
            title="Prior shareholder letter", publisher="SEC",
        )
        actual_source = SourceDocument.objects.create(
            company=self.netflix, source_api="SEC_EDGAR_EXHIBIT", url="https://example.com/q1-letter",
            title="Current shareholder letter", publisher="SEC",
        )
        EarningsGuidanceComparison.objects.create(
            period=period, metric_name="Revenue", forecast_value="12157", actual_value="12250",
            unit="USD millions", comparison_status="ABOVE", forecast_source=forecast_source,
            actual_source=actual_source, forecast_evidence="Forecast revenue was $12,157 million.",
            actual_evidence="Reported revenue was $12,250 million.", confidence_score="0.950",
            review_status="REVIEWED",
        )

        payload = self.client.get("/companies/netflix/earnings").json()["selected_period"]["guidance_comparison"]

        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["items"][0]["comparison_status"], "ABOVE")
        self.assertEqual(payload["items"][0]["forecast_source"]["url"], forecast_source.url)
        self.assertEqual(payload["items"][0]["actual_source"]["url"], actual_source.url)

    def test_capital_allocation_builder_creates_source_backed_period_and_free_cash_flow(self):
        filing_source = SourceDocument.objects.create(
            company=self.netflix, source_api="SEC_EDGAR", url="https://example.com/000106528026000001",
            title="Netflix 10-Q filing 2026-04-20 - 10-Q", publisher="SEC",
            published_date="2026-04-20T00:00:00Z", language="en",
        )
        for concept, label, value in (
            ("NetCashProvidedByUsedInOperatingActivities", "Net cash provided by operating activities", "280"),
            ("PaymentsToAcquirePropertyPlantAndEquipment", "Purchases of property and equipment", "40"),
            ("ResearchAndDevelopmentExpense", "Technology and development", "75"),
            ("CashAndCashEquivalentsAtCarryingValue", "Cash and cash equivalents", "900"),
        ):
            FinancialFact.objects.create(
                company=self.netflix, taxonomy="us-gaap", concept=concept, label=label, unit="USD",
                fy=2026, fp="Q1", filed=date(2026, 4, 20), frame="CY2026Q1", value=value,
                accession_number="0001065280-26-000001",
                raw={"start": "2026-01-01", "end": "2026-03-31", "form": "10-Q", "fp": "Q1", "fy": 2026},
            )

        first = build_capital_allocation_periods(self.netflix)
        second = build_capital_allocation_periods(self.netflix)
        period = CapitalAllocationPeriod.objects.get(company=self.netflix)

        self.assertEqual(first["periods_created"], 1)
        self.assertEqual(second["periods_updated"], 1)
        self.assertEqual(period.source_documents.count() if hasattr(period, "source_documents") else 0, 0)
        self.assertEqual(period.items.filter(category="CAPEX").count(), 1)
        self.assertEqual(period.items.filter(category="FREE_CASH_FLOW", is_calculated=True).count(), 1)
        self.assertEqual(str(period.free_cash_flow), "240.000000")
        self.assertEqual(str(period.total_deployment), "115.000000")
        self.assertEqual(CapitalAllocationItem.objects.get(category="CAPEX").source_document, filing_source)
        self.assertEqual(capital_allocation_quality_issues(self.netflix), [])
        payload = self.client.get("/companies/netflix/capital-allocation").json()
        context = payload["selected_period"]["validation_context"]
        self.assertEqual(context["reported_figure_status"], "available")
        self.assertEqual(context["adjusted_figure_status"], "unavailable")
        self.assertEqual(context["currency_conversion_status"], "not_required")
        self.assertIn("Reported SEC Company Facts", context["reported_figure_label"])
        self.assertTrue(any(gap["key"] == "capital_allocation_adjusted_figures" for gap in payload["source_gaps"]))
        call_command("validate_capital_allocation_context", "--company", "netflix")

    def test_capital_allocation_validator_blocks_mixed_currency_deployment_totals(self):
        fact_usd = FinancialFact.objects.create(
            company=self.netflix, taxonomy="us-gaap", concept="PaymentsToAcquirePropertyPlantAndEquipment",
            label="Purchases of property and equipment", unit="USD", fy=2026, fp="Q1",
            filed=date(2026, 4, 20), frame="CY2026Q1", value="40",
            accession_number="0001065280-26-000001",
            raw={"start": "2026-01-01", "end": "2026-03-31", "form": "10-Q", "fp": "Q1", "fy": 2026},
        )
        fact_eur = FinancialFact.objects.create(
            company=self.netflix, taxonomy="ifrs", concept="ResearchAndDevelopmentExpense",
            label="Research and development", unit="EUR", fy=2026, fp="Q1",
            filed=date(2026, 4, 20), frame="CY2026Q1", value="75",
            accession_number="0001065280-26-000001",
            raw={"start": "2026-01-01", "end": "2026-03-31", "form": "10-Q", "fp": "Q1", "fy": 2026},
        )
        period = CapitalAllocationPeriod.objects.create(
            company=self.netflix, fiscal_year=2026, fiscal_period="Q1", period_end=date(2026, 3, 31),
            filed_date=date(2026, 4, 20), accession_number="0001065280-26-000001",
            cadence="QUARTERLY", headline="Mixed currency period.", review_status="REVIEWED", is_published=True,
        )
        CapitalAllocationItem.objects.create(
            period=period, category="CAPEX", label="Capex", value="40", unit="USD", concept=fact_usd.concept,
            source_fact=fact_usd, evidence_text="Reported capex.", confidence_score="0.950", review_status="REVIEWED",
        )
        CapitalAllocationItem.objects.create(
            period=period, category="R_AND_D", label="R&D", value="75", unit="EUR", concept=fact_eur.concept,
            source_fact=fact_eur, evidence_text="Reported R&D.", confidence_score="0.950", review_status="REVIEWED",
        )

        payload = self.client.get("/companies/netflix/capital-allocation").json()

        self.assertEqual(payload["selected_period"]["validation_context"]["currency_conversion_status"], "blocked")
        self.assertTrue(any(gap["key"] == "capital_allocation_currency_conversion" for gap in payload["source_gaps"]))
        with self.assertRaisesMessage(Exception, "mixed deployment units"):
            call_command("validate_capital_allocation_context", "--company", "netflix")

    def test_capital_allocation_api_marks_missing_categories_as_gaps_not_zero(self):
        FinancialFact.objects.create(
            company=self.netflix, taxonomy="us-gaap", concept="NetCashProvidedByUsedInOperatingActivities",
            label="Net cash provided by operating activities", unit="USD", fy=2026, fp="Q1",
            filed=date(2026, 4, 20), frame="CY2026Q1", value="280",
            accession_number="0001065280-26-000001",
            raw={"start": "2026-01-01", "end": "2026-03-31", "form": "10-Q", "fp": "Q1", "fy": 2026},
        )
        build_capital_allocation_periods(self.netflix)

        payload = self.client.get("/companies/netflix/capital-allocation").json()

        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["selected_period"]["deployment_items"], [])
        self.assertIsNone(payload["selected_period"]["cash_flow_context"]["total_deployment"])
        self.assertTrue(any(gap["key"] == "capital_deployment_items" for gap in payload["source_gaps"]))

    def test_competitive_position_builder_creates_peer_map_and_dimensions(self):
        disney = Company.objects.create(name="Disney", industry="Communication Services", country="United States")
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            summary="Netflix distributes entertainment.",
            products=["Subscription video streaming", "Advertising-supported streaming"],
            customer_groups=["Streaming members", "Advertisers"],
            geographies=["United States", "International markets"],
            competitors=["Disney", "Prime Video"],
            confidence_score="0.900",
        )

        first = build_competitive_position(self.netflix)
        second = build_competitive_position(self.netflix)
        snapshot = CompetitivePositionSnapshot.objects.get(company=self.netflix)

        self.assertEqual(first["snapshots_created"], 1)
        self.assertEqual(second["snapshots_updated"], 1)
        self.assertTrue(CompetitivePeer.objects.filter(snapshot=snapshot, peer_company=disney, relationship_type="DIRECT").exists())
        self.assertTrue(snapshot.dimensions.filter(dimension_type="PRODUCT_OVERLAP").exists())
        self.assertEqual(competitive_position_quality_issues(self.netflix), [])

    def test_competitive_position_api_exposes_market_share_gap_without_causation_claim(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            summary="Netflix distributes entertainment.",
            products=["Subscription video streaming"],
            customer_groups=["Streaming members"],
            geographies=["United States"],
            competitors=["Disney+"],
            confidence_score="0.900",
        )
        build_competitive_position(self.netflix)

        payload = self.client.get("/companies/netflix/competitive-position").json()

        self.assertEqual(payload["status"], "available")
        self.assertGreaterEqual(payload["coverage"]["peer_count"], 1)
        self.assertEqual(payload["market_share"]["status"], "unavailable")
        self.assertTrue(any(gap["key"] == "competitive_market_share" for gap in payload["source_gaps"]))
        self.assertIn("does not imply causation", payload["snapshot"]["methodology"])

    def test_product_pricing_builder_creates_catalog_and_timeline(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            summary="Netflix distributes entertainment.",
            brands=["Netflix"],
            products=["Subscription video streaming", "Advertising-supported plan"],
            customer_groups=["Streaming members", "Advertisers"],
            geographies=["United States"],
            confidence_score="0.900",
        )
        BusinessEvent.objects.create(
            company=self.netflix,
            source_document=self.source,
            event_type="PRICING_CHANGE",
            event_date=date(2022, 11, 3),
            actual_change="Netflix launched its advertising-supported plan.",
            before_state="Netflix had subscription streaming plans without an ad-supported tier.",
            after_state="Netflix added an advertising-supported plan.",
            source_claim="Netflix launched Basic with Ads.",
            evidence_text="Netflix launched Basic with Ads.",
            confidence_score="0.900",
        )

        first = build_product_pricing_history(self.netflix)
        second = build_product_pricing_history(self.netflix)
        snapshot = ProductCatalogSnapshot.objects.get(company=self.netflix)

        self.assertEqual(first["snapshots_created"], 1)
        self.assertEqual(second["snapshots_updated"], 1)
        self.assertTrue(ProductOffering.objects.filter(snapshot=snapshot, name="Advertising-supported plan").exists())
        self.assertTrue(snapshot.changes.filter(change_type="PRICE_CHANGE").exists())
        self.assertEqual(product_pricing_quality_issues(self.netflix), [])

    def test_product_pricing_api_keeps_missing_prices_unavailable(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            products=["Subscription video streaming"],
            customer_groups=["Streaming members"],
            geographies=["United States"],
            confidence_score="0.900",
        )
        build_product_pricing_history(self.netflix)

        payload = self.client.get("/companies/netflix/product-pricing").json()

        self.assertEqual(payload["status"], "available")
        self.assertGreaterEqual(payload["coverage"]["offering_count"], 1)
        self.assertEqual(payload["price_context"]["status"], "unavailable")
        self.assertTrue(any(gap["key"] == "product_list_prices" for gap in payload["source_gaps"]))
        self.assertIn("Announcement dates and effective dates are stored separately", payload["snapshot"]["chronology_note"])

    def test_acquisition_lifecycle_builder_creates_deal_from_event(self):
        BusinessEvent.objects.create(
            company=self.netflix,
            source_document=self.source,
            event_type="ACQUISITION",
            event_date=date(2024, 2, 1),
            decision="Acquire Spry Fox to expand internal game development.",
            actual_change="Netflix acquired Spry Fox and began integrating game development capabilities.",
            outcome="Integration remains under review.",
            source_claim="Netflix acquired Spry Fox.",
            evidence_text="Netflix acquired Spry Fox.",
            confidence_score="0.900",
        )

        first = build_acquisition_lifecycle(self.netflix)
        second = build_acquisition_lifecycle(self.netflix)
        deal = AcquisitionLifecycleDeal.objects.get(company=self.netflix, target_name="Spry Fox")

        self.assertEqual(first["deals_created"], 1)
        self.assertEqual(second["deals_updated"], 1)
        self.assertEqual(deal.current_stage, "INTEGRATING")
        self.assertTrue(deal.stage_events.exists())
        self.assertNotIn("no reviewed acquisition lifecycle deals", acquisition_lifecycle_quality_issues(self.netflix))

    def test_acquisition_lifecycle_api_exposes_source_gaps(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            brands=["Netflix"],
            confidence_score="0.900",
        )
        build_acquisition_lifecycle(self.netflix)

        payload = self.client.get("/companies/netflix/acquisition-lifecycle").json()

        self.assertIn(payload["status"], {"available", "partial"})
        self.assertGreaterEqual(payload["coverage"]["deal_count"], 0)
        if payload["selected_deal"]:
            self.assertTrue(any(gap["key"] == "acquisition_deal_terms" for gap in payload["source_gaps"]))
        else:
            self.assertTrue(any(gap["key"] == "acquisition_deals" for gap in payload["source_gaps"]))

    def test_customer_supplier_dependency_builder_creates_category_only_map(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            products=["Subscription video streaming"],
            customer_groups=["Streaming members", "Advertisers"],
            geographies=["United States"],
            confidence_score="0.900",
        )

        first = build_customer_supplier_dependency(self.netflix)
        second = build_customer_supplier_dependency(self.netflix)
        snapshot = CustomerSupplierDependencySnapshot.objects.get(company=self.netflix)

        self.assertEqual(first["snapshots_created"], 1)
        self.assertEqual(second["snapshots_updated"], 1)
        self.assertTrue(snapshot.dependencies.filter(dependency_type="CUSTOMER_SEGMENT", counterparty_name="Streaming members").exists())
        self.assertTrue(snapshot.dependencies.filter(disclosure_confidence="CATEGORY_ONLY").exists())
        self.assertNotIn("no reviewed dependency snapshot", customer_supplier_dependency_quality_issues(self.netflix))

    def test_customer_supplier_dependency_api_keeps_named_counterparties_unavailable(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            customer_groups=["Streaming members"],
            confidence_score="0.900",
        )
        build_customer_supplier_dependency(self.netflix)

        payload = self.client.get("/companies/netflix/customer-supplier-dependency").json()

        self.assertEqual(payload["status"], "available")
        self.assertGreaterEqual(payload["coverage"]["dependency_count"], 1)
        self.assertEqual(payload["coverage"]["named_counterparty_count"], 0)
        self.assertTrue(any(gap["key"] == "named_counterparties" for gap in payload["source_gaps"]))
        self.assertTrue(any(gap["key"] == "dependency_contract_terms" for gap in payload["source_gaps"]))

    def test_source_gap_promotion_adds_customer_concentration_to_dependency_dashboard(self):
        gap = SourceGap.objects.create(
            company=self.netflix,
            dashboard="customer_supplier_dependency",
            gap_type="concentration_percentages",
            provider="customer-supplier-dependency",
            reason="Need disclosed concentration percentages.",
            next_ingestion_task="Extract customer concentration.",
        )
        SourceGapResolutionCandidate.objects.create(
            company=self.netflix,
            source_gap=gap,
            dashboard="customer_supplier_dependency",
            gap_type="concentration_percentages",
            candidate_type="dependency_concentration_source",
            source_document=self.source,
            evidence_text="Customer Alpha accounted for 12.5% of revenue during the fiscal year.",
            confidence_score="0.900",
            extraction_status="EXTRACTED",
            review_status="NEEDS_REVIEW",
        )

        result = promote_source_gap_candidates(dashboard="customer_supplier_dependency", gap_type="concentration_percentages")

        self.assertEqual(result.candidates_promoted, 1)
        response = self.client.get("/companies/netflix/customer-supplier-dependency")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["coverage"]["named_counterparty_count"], 1)
        self.assertEqual(payload["coverage"]["contract_term_count"], 1)
        self.assertEqual(payload["dependencies"][0]["counterparty_name"], "Customer Alpha")
        self.assertEqual(payload["dependencies"][0]["concentration_percent"], 12.5)

    def test_source_gap_promotion_adds_named_contract_terms_to_dependency_dashboard(self):
        evidence = (
            "Pursuant to an agreement, the Company is the exclusive distributor of the Live TV service "
            "for five years (renewable for an additional five-year term by mutual agreement) and pays "
            "a wholesale fee to Fubo based on programming costs."
        )
        gap = SourceGap.objects.create(
            company=self.netflix,
            dashboard="customer_supplier_dependency",
            gap_type="dependency_contract_terms",
            provider="customer-supplier-dependency",
            reason="Need source-linked contract terms.",
            next_ingestion_task="Extract named commercial agreements.",
        )
        SourceGapResolutionCandidate.objects.create(
            company=self.netflix,
            source_gap=gap,
            dashboard="customer_supplier_dependency",
            gap_type="dependency_contract_terms",
            candidate_type="dependency_contract_source",
            source_document=self.source,
            evidence_text=evidence,
            confidence_score="0.900",
            extraction_status="EXTRACTED",
            review_status="NEEDS_REVIEW",
        )

        self.assertEqual(parse_dependency_contract_terms(evidence)[0]["counterparty_name"], "Fubo")
        result = promote_source_gap_candidates(dashboard="customer_supplier_dependency", gap_type="dependency_contract_terms")

        self.assertEqual(result.candidates_promoted, 1)
        payload = self.client.get("/companies/netflix/customer-supplier-dependency").json()
        dependency = next(item for item in payload["dependencies"] if item["counterparty_name"] == "Fubo")
        self.assertEqual(dependency["dependency_type"], "DISTRIBUTOR")
        self.assertEqual(
            {term["term_type"] for term in payload["contract_terms"] if term["counterparty_name"] == "Fubo"},
            {"EXCLUSIVITY", "RENEWAL"},
        )

    def test_contract_term_parser_rejects_unnamed_or_generic_contract_language(self):
        self.assertEqual(parse_dependency_contract_terms("Our agreements may expire, renew, or terminate."), [])
        self.assertEqual(parse_dependency_contract_terms("The agreement with a counterparty terminates next year."), [])
        self.assertEqual(parse_dependency_contract_terms("The agreement with Residual holder terminates next year."), [])

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
        payload = self.client.get("/companies/netflix/operating-kpis").json()
        self.assertEqual(payload["coverage"]["baseline"]["status"], "available")
        self.assertGreaterEqual(payload["coverage"]["baseline"]["definition_count"], 2)
        self.assertGreaterEqual(payload["coverage"]["baseline"]["observation_count"], 2)
        self.assertGreaterEqual(payload["coverage"]["baseline"]["annual_observation_count"], 1)
        self.assertGreaterEqual(payload["coverage"]["baseline"]["quarterly_observation_count"], 1)
        self.assertIn("SEC-backed baseline definitions", payload["coverage"]["baseline"]["coverage_label"])
        call_command("validate_operating_kpi_baselines", "--company", "netflix")

    def test_operating_kpi_baseline_validator_fails_when_company_lacks_baseline(self):
        with self.assertRaisesMessage(Exception, "only 0 baseline definitions"):
            call_command("validate_operating_kpi_baselines", "--company", "netflix")

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

    def test_dashboard_company_situations_falls_back_to_reviewed_competitive_peers(self):
        exxon = Company.objects.create(name="ExxonMobil", industry="Energy", country="United States")
        exxon_source = SourceDocument.objects.create(
            company=exxon,
            source_api="SEC",
            url="https://example.com/exxon-10k",
            title="ExxonMobil 10-K",
            publisher="SEC",
            language="en",
        )
        snapshot = CompetitivePositionSnapshot.objects.create(
            company=exxon,
            source_document=exxon_source,
            effective_date=date(2026, 1, 1),
            status="REVIEWED",
            summary="ExxonMobil competes with global integrated energy companies.",
            confidence_score="0.850",
        )
        CompetitivePeer.objects.create(
            snapshot=snapshot,
            peer_name="Chevron",
            relationship_type="DIRECT",
            scope="Integrated energy",
            geography="United States",
            evidence_text="ExxonMobil profile identifies Chevron as a direct competitor.",
            confidence_score="0.850",
        )

        response = self.client.get("/dashboard-data?company=exxonmobil&section=company_situations")

        self.assertEqual(response.status_code, 200)
        rows = response.json()["sections"]["company_situations"]["items"]
        self.assertEqual(rows[0]["name"], "Chevron")
        self.assertEqual(rows[0]["peer_source"], "competitive_position")
        self.assertEqual(rows[0]["is_in_universe"], False)

    def test_source_gap_resolver_creates_real_source_candidates(self):
        source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="SEC_EDGAR_EXHIBIT",
            url="https://example.com/netflix-acquires-example-studio",
            title="Netflix announces acquisition of Example Studio",
            publisher="SEC",
            language="en",
            snippet="Netflix announced the acquisition of Example Studio for cash consideration and described integration plans.",
        )
        gap = SourceGap.objects.create(
            company=self.netflix,
            dashboard="acquisition_lifecycle",
            gap_type="acquisition_deals",
            provider="acquisition-lifecycle",
            reason="Reviewed acquisition deals are unavailable.",
            next_ingestion_task="Collect SEC 8-K and company press release sources.",
        )

        result = resolve_source_gaps(company=self.netflix)

        self.assertEqual(result.gaps_checked, 1)
        self.assertEqual(result.candidates_created, 1)
        candidate = SourceGapResolutionCandidate.objects.get(source_gap=gap)
        self.assertEqual(candidate.source_document, source)
        self.assertEqual(candidate.review_status, "NEEDS_REVIEW")
        self.assertIn("Example Studio", candidate.evidence_text)
        gap.refresh_from_db()
        self.assertEqual(gap.status, "IN_PROGRESS")
        self.assertEqual(gap.metadata["resolution_candidate_count"], 1)

    def test_source_gap_collector_maps_gaps_to_golden_sec_forms(self):
        self.assertIn("DEF 14A", forms_for_gap("ownership_insider_activity", "ownership_percentages"))
        self.assertIn("4", forms_for_gap("ownership_insider_activity", "insider_transactions"))
        self.assertIn("8-K", forms_for_gap("leadership_decision_record", "transition_events"))
        self.assertIn("10-Q", forms_for_gap("geographic_expansion", "revenue_contribution"))
        self.assertIn("S-4", forms_for_gap("FOUNDER_DECISION", "LIFECYCLE_TIMING"))
        self.assertIn(("FOUNDER_DECISION", "LIFECYCLE_TIMING"), SOURCE_RULES)
        self.assertEqual(forms_for_gap("unknown", "missing"), ("10-K", "10-Q", "8-K"))

    def test_source_gap_collector_uses_company_ticker_alias(self):
        self.assertEqual(ticker_for(self.netflix), "NFLX")
        ford = Company.objects.create(name="Ford Motor Company", slug="ford-motor-company", aliases=["FOMOCO"])
        self.assertEqual(ticker_for(ford), "F")
        company = Company.objects.create(name="Tickerless Example", slug="tickerless-example", aliases=["Long Name"])
        self.assertEqual(ticker_for(company), "")

    def test_source_gap_candidate_extractor_updates_evidence_from_full_text(self):
        source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="SEC_EDGAR",
            url="https://example.com/netflix-proxy",
            title="Netflix DEF 14A filing",
            publisher="SEC",
            language="en",
            snippet="Proxy statement.",
        )
        ArticleExtraction.objects.create(
            source_document=source,
            clean_text="Intro text. The proxy statement includes beneficial ownership and voting power by named holders. Closing text.",
            word_count=15,
            extraction_status="SUCCEEDED",
            extractor_name="test",
        )
        gap = SourceGap.objects.create(
            company=self.netflix,
            dashboard="ownership_insider_activity",
            gap_type="ownership_percentages",
            provider="ownership-insider-activity",
            reason="Ownership percentages unavailable.",
            next_ingestion_task="Review proxy.",
        )
        SourceGapResolutionCandidate.objects.create(
            company=self.netflix,
            source_gap=gap,
            dashboard=gap.dashboard,
            gap_type=gap.gap_type,
            source_document=source,
            candidate_type="ownership_percentage_source",
            evidence_text="Proxy statement.",
            confidence_score="0.500",
            extraction_status="CANDIDATE",
            review_status="NEEDS_REVIEW",
        )

        result = extract_source_gap_candidates(limit=10)

        self.assertEqual(result.candidates_checked, 1)
        self.assertEqual(result.candidates_updated, 1)
        candidate = SourceGapResolutionCandidate.objects.get(source_gap=gap)
        self.assertEqual(candidate.extraction_status, "EXTRACTED")
        self.assertIn("beneficial ownership", candidate.evidence_text)
        self.assertTrue(candidate.metadata["full_text_evidence"])

    def test_lifecycle_timing_excerpt_returns_the_dated_action_sentence(self):
        text = (
            "Introductory filing text. On August 4, 2026, the Company entered into a co-operation agreement "
            "with SEGRO. Unrelated financial statement text."
        )
        self.assertEqual(
            lifecycle_timing_excerpt(text),
            "On August 4, 2026, the Company entered into a co-operation agreement with SEGRO.",
        )

    def test_full_text_excerpt_prefers_keyword_window(self):
        text = "A " * 200 + "Form 4 shows an insider transaction sale under a trading plan." + " Z" * 200

        excerpt = full_text_excerpt(text, ("insider transaction",))

        self.assertIn("insider transaction", excerpt)
        self.assertLess(len(excerpt), len(text))

    def test_source_gap_candidate_extractor_reuses_recorded_failure(self):
        source = SourceDocument.objects.create(
            company=self.netflix,
            source_api="OFFICIAL_WEBSITE",
            url="https://example.com/blocked-store",
            title="Blocked store page",
            publisher="Example",
            language="en",
        )
        ArticleExtraction.objects.create(
            source_document=source,
            extraction_status="FAILED",
            extraction_error="403 Client Error",
            extractor_name="none",
        )
        gap = SourceGap.objects.create(
            company=self.netflix,
            dashboard="product_pricing_history",
            gap_type="product_list_prices",
            provider="product-pricing-history",
            reason="Product pricing unavailable.",
            next_ingestion_task="Review official pricing.",
        )
        candidate = SourceGapResolutionCandidate.objects.create(
            company=self.netflix,
            source_gap=gap,
            dashboard=gap.dashboard,
            gap_type=gap.gap_type,
            source_document=source,
            candidate_type="official_product_price_source",
            evidence_text="Store page.",
            confidence_score="0.500",
            extraction_status="CANDIDATE",
            review_status="NEEDS_REVIEW",
        )

        result = extract_source_gap_candidates(limit=10)

        self.assertEqual(result.candidates_checked, 1)
        self.assertEqual(result.documents_extracted, 0)
        self.assertEqual(result.candidates_failed, 1)
        candidate.refresh_from_db()
        self.assertEqual(candidate.metadata["extraction_error"], "403 Client Error")

    def test_source_gaps_api_exposes_resolution_candidates(self):
        gap = SourceGap.objects.create(
            company=self.netflix,
            dashboard="acquisition_lifecycle",
            gap_type="acquisition_deals",
            provider="acquisition-lifecycle",
            reason="Reviewed acquisition deals are unavailable.",
            next_ingestion_task="Collect SEC 8-K and company press release sources.",
        )
        SourceGapResolutionCandidate.objects.create(
            source_gap=gap,
            company=self.netflix,
            source_document=self.source,
            dashboard="acquisition_lifecycle",
            gap_type="acquisition_deals",
            candidate_type="acquisition_source",
            evidence_text="Netflix acquisition evidence.",
            confidence_score="0.700",
            next_action="Extract named target before creating reviewed lifecycle rows.",
        )

        response = self.client.get("/source-gaps?dashboard=acquisition_lifecycle")

        self.assertEqual(response.status_code, 200)
        candidate = response.json()["source_gaps"][0]["resolution_candidates"][0]
        self.assertEqual(candidate["candidate_type"], "acquisition_source")
        self.assertEqual(candidate["source"]["title"], "Netflix 10-K")

    def test_geographic_expansion_builder_creates_reviewed_market_rows(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            source_document=self.source,
            effective_date=date(2026, 1, 1),
            status="REVIEWED",
            summary="Netflix operates globally.",
            geographies=["United States", "International markets"],
            confidence_score="0.850",
        )

        first = build_geographic_expansion(self.netflix)
        second = build_geographic_expansion(self.netflix)

        self.assertEqual(first["markets_created"], 2)
        self.assertEqual(second["markets_updated"], 2)
        snapshot = GeographicExpansionSnapshot.objects.get(company=self.netflix)
        self.assertEqual(snapshot.status, "REVIEWED")
        self.assertEqual(snapshot.markets.count(), 2)
        self.assertNotIn("no reviewed geographic markets", geographic_expansion_quality_issues(self.netflix))
        call_command("validate_geographic_expansion", "--company", "netflix")

    def test_geographic_expansion_api_exposes_gaps_without_estimating_revenue(self):
        build_geographic_expansion(self.netflix)

        response = self.client.get("/companies/netflix/geographic-expansion")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertGreaterEqual(payload["coverage"]["market_count"], 1)
        self.assertEqual(payload["coverage"]["revenue_contribution_count"], 0)
        self.assertIn("geography_levels", payload["definitions"])
        self.assertEqual(payload["validation_context"]["geography_validation_status"], "available")
        self.assertEqual(payload["validation_context"]["currency_validation_status"], "available")
        self.assertIn("event_dates", payload["markets"][0])
        self.assertIn("products", payload["markets"][0])
        self.assertIn("outcome_metrics", payload["markets"][0])
        self.assertTrue(any(gap["key"] == "revenue_contribution" for gap in payload["source_gaps"]))

    def test_geographic_expansion_validator_blocks_revenue_without_currency(self):
        snapshot = GeographicExpansionSnapshot.objects.create(
            company=self.netflix,
            effective_date=date(2026, 1, 1),
            source_document=self.source,
            status="REVIEWED",
            summary="Reviewed expansion.",
            methodology="Test methodology.",
            confidence_score="0.850",
        )
        snapshot.markets.create(
            geography="United States",
            market_type="COUNTRY_OR_MARKET",
            current_status="ACTIVE",
            revenue_contribution="100",
            revenue_currency="",
            revenue_period="FY2026",
            expansion_rationale="Reviewed market.",
            outcome_summary="Reviewed outcome.",
            evidence_text="Reviewed market evidence.",
            source_document=self.source,
            confidence_score="0.850",
            review_status="REVIEWED",
        )

        payload = self.client.get("/companies/netflix/geographic-expansion").json()

        self.assertEqual(payload["validation_context"]["currency_validation_status"], "blocked")
        self.assertTrue(any(gap["key"] == "market_revenue_currency" for gap in payload["source_gaps"]))
        with self.assertRaisesMessage(Exception, "revenue contribution without currency"):
            call_command("validate_geographic_expansion", "--company", "netflix")

    def test_ownership_insider_builder_creates_reviewed_insider_context(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            source_document=self.source,
            effective_date=date(2026, 1, 1),
            status="REVIEWED",
            summary="Netflix reviewed profile.",
            leadership=["Greg Peters - Co-CEO", "Ted Sarandos - Co-CEO"],
            confidence_score="0.850",
        )

        first = build_ownership_insider_activity(self.netflix)
        second = build_ownership_insider_activity(self.netflix)

        self.assertEqual(first["positions_created"], 2)
        self.assertEqual(second["positions_updated"], 2)
        snapshot = OwnershipInsiderSnapshot.objects.get(company=self.netflix)
        self.assertEqual(snapshot.status, "REVIEWED")
        self.assertEqual(snapshot.positions.count(), 2)
        self.assertNotIn("no reviewed insider context or ownership positions", ownership_insider_quality_issues(self.netflix))

    def test_ownership_insider_api_exposes_gaps_without_estimating_control(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            source_document=self.source,
            effective_date=date(2026, 1, 1),
            status="REVIEWED",
            summary="Netflix reviewed profile.",
            leadership=["Greg Peters - Co-CEO"],
            confidence_score="0.850",
        )
        build_ownership_insider_activity(self.netflix)

        response = self.client.get("/companies/netflix/ownership-insider")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"available", "partial"})
        self.assertEqual(payload["coverage"]["ownership_percent_count"], 0)
        self.assertEqual(payload["coverage"]["voting_control_count"], 0)
        self.assertEqual(payload["coverage"]["transaction_count"], 0)
        self.assertTrue(any(gap["key"] == "ownership_percentages" for gap in payload["source_gaps"]))
        self.assertTrue(any(gap["key"] == "insider_transactions" for gap in payload["source_gaps"]))

    def test_source_gap_promotion_adds_ownership_percentage_to_dashboard(self):
        OwnershipInsiderSnapshot.objects.create(
            company=self.netflix,
            source_document=self.source,
            effective_date=date(2026, 1, 1),
            status="REVIEWED",
            summary="Current ownership dashboard snapshot.",
            confidence_score="0.800",
        )
        gap = SourceGap.objects.create(
            company=self.netflix,
            dashboard="ownership_insider_activity",
            gap_type="ownership_percentages",
            provider="ownership-insider-activity",
            reason="Need disclosed ownership percentages.",
            next_ingestion_task="Extract proxy ownership table.",
        )
        SourceGapResolutionCandidate.objects.create(
            company=self.netflix,
            source_gap=gap,
            dashboard="ownership_insider_activity",
            gap_type="ownership_percentages",
            candidate_type="institutional_position_source",
            source_document=self.source,
            evidence_text="Schedule 13G ownership candidate.",
            confidence_score="0.900",
            extraction_status="EXTRACTED",
            review_status="NEEDS_REVIEW",
            metadata={"article_extraction_id": 1},
        )
        extraction = ArticleExtraction.objects.create(
            source_document=self.source,
            clean_text=(
                "Item 2(a) - Name of Person Filing: The Vanguard Group - 23-1945930 "
                "Item 2(b) Address. Aggregate Amount Beneficially Owned by Each Reporting Person 229,805,491 "
                "Percent of Class Represented by Amount in Row 9 7.23%"
            ),
            word_count=24,
            extraction_status="SUCCEEDED",
            extractor_name="test",
        )
        SourceGapResolutionCandidate.objects.update(metadata={"article_extraction_id": extraction.id})

        result = promote_source_gap_candidates(dashboard="ownership_insider_activity", gap_type="ownership_percentages")

        self.assertEqual(result.candidates_promoted, 1)
        response = self.client.get("/companies/netflix/ownership-insider")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["coverage"]["ownership_percent_count"], 1)
        self.assertEqual(payload["positions"][0]["holder_name"], "Vanguard Group")
        self.assertEqual(payload["positions"][0]["economic_ownership_pct"], 7.23)

    def test_source_gap_promotion_parsers_require_explicit_percentages(self):
        self.assertEqual(parse_dependency_concentrations("No single customer accounted for 10% or more of revenue."), [])
        self.assertEqual(parse_ownership_rows("Ownership information is discussed in the proxy.", gap_type="ownership_percentages"), [])
        self.assertEqual(
            parse_ownership_rows(
                "Item 2(a) - Name of Person Filing: The Vanguard Group - 23-1945930 "
                "Item 2(b) Address. Percent of Class Represented by Amount in Row 9 7.23%",
                gap_type="institutional_positions",
            )[0]["holder_name"],
            "Vanguard Group",
        )

    def test_valuation_context_builder_creates_reproducible_observations(self):
        MarketPrice.objects.create(
            company=self.netflix,
            ticker="NFLX",
            provider="TEST",
            price_date=date(2026, 1, 31),
            close_price="100.000000",
        )
        FinancialFact.objects.create(company=self.netflix, taxonomy="us-gaap", concept="EntityCommonStockSharesOutstanding", label="Shares", unit="shares", fy=2025, fp="FY", filed=date(2026, 1, 30), frame="CY2025", value="1000")
        FinancialFact.objects.create(company=self.netflix, taxonomy="us-gaap", concept="Revenues", label="Revenue", unit="USD", fy=2025, fp="FY", filed=date(2026, 1, 30), frame="CY2025", value="50000")
        FinancialFact.objects.create(company=self.netflix, taxonomy="us-gaap", concept="NetIncomeLoss", label="Net income", unit="USD", fy=2025, fp="FY", filed=date(2026, 1, 30), frame="CY2025", value="10000")

        result = build_valuation_context(self.netflix)

        self.assertEqual(result["snapshots_created"], 1)
        snapshot = ValuationContextSnapshot.objects.get(company=self.netflix)
        self.assertIn("not investment advice", snapshot.disclaimer)
        market_cap = snapshot.observations.get(measure="MARKET_CAP")
        self.assertEqual(str(market_cap.value), "100000.000000")
        price_to_sales = snapshot.observations.get(measure="PRICE_TO_SALES")
        self.assertEqual(str(price_to_sales.value), "2.000000")
        self.assertNotIn("market capitalization unavailable", valuation_quality_issues(self.netflix))

    def test_valuation_context_builder_deduplicates_same_labeled_event_snapshot(self):
        for price_date, price in (
            (date(2026, 1, 9), "95.000000"),
            (date(2026, 1, 11), "105.000000"),
            (date(2026, 1, 31), "100.000000"),
        ):
            MarketPrice.objects.create(
                company=self.netflix,
                ticker="NFLX",
                provider="TEST",
                price_date=price_date,
                close_price=price,
            )
        FinancialFact.objects.create(company=self.netflix, taxonomy="us-gaap", concept="EntityCommonStockSharesOutstanding", label="Shares", unit="shares", fy=2025, fp="FY", filed=date(2026, 1, 30), frame="CY2025", value="1000")
        FinancialFact.objects.create(company=self.netflix, taxonomy="us-gaap", concept="Revenues", label="Revenue", unit="USD", fy=2025, fp="FY", filed=date(2026, 1, 30), frame="CY2025", value="50000")

        for event_type in ("PRODUCT_EXPANSION", "COMPETITIVE_RESPONSE"):
            BusinessEvent.objects.create(
                company=self.netflix,
                source_document=self.source,
                event_date=date(2026, 1, 10),
                event_type=event_type,
                actual_change="Netflix changed its operating strategy.",
                source_claim="Netflix changed its operating strategy.",
                review_status="APPROVED",
            )

        build_valuation_context(self.netflix)

        snapshot = ValuationContextSnapshot.objects.get(company=self.netflix)
        self.assertEqual(ValuationEventSnapshot.objects.filter(snapshot=snapshot).count(), 1)

    def test_valuation_context_api_exposes_source_gaps_without_recommendations(self):
        build_valuation_context(self.netflix)

        response = self.client.get("/companies/netflix/valuation-context")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"available", "partial"})
        self.assertIn("not investment advice", payload["snapshot"]["disclaimer"])
        self.assertTrue(any(gap["key"] in {"market_value", "valuation_inputs"} for gap in payload["source_gaps"]))
        rendered = str(payload).lower()
        self.assertNotIn("buy", rendered)
        self.assertNotIn("sell", rendered)
        self.assertNotIn("price target", rendered)

    def test_regulatory_litigation_builder_creates_reviewed_matter_from_event(self):
        BusinessEvent.objects.create(
            company=self.netflix,
            source_document=self.source,
            event_date=date(2026, 1, 20),
            event_type="REGULATORY_RESPONSE",
            source_claim="The FTC investigation remains pending and could require compliance remedies.",
            actual_change="Netflix disclosed it is responding to the FTC investigation.",
            outcome="The investigation remains pending.",
            evidence_text="FTC investigation remains pending and could require compliance remedies.",
            confidence_score="0.820",
            review_status="APPROVED",
        )

        result = build_regulatory_litigation_calendar(self.netflix)

        self.assertEqual(result["snapshots_created"], 1)
        snapshot = RegulatoryLitigationSnapshot.objects.get(company=self.netflix)
        matter = snapshot.matters.get()
        self.assertEqual(matter.matter_type, "INVESTIGATION")
        self.assertEqual(matter.authority, "FTC")
        self.assertEqual(matter.matter_status, "PENDING")
        self.assertIn("does not make legal conclusions", snapshot.legal_guardrail)
        self.assertIn("no sourced future deadlines", regulatory_litigation_quality_issues(self.netflix))

    def test_regulatory_litigation_api_exposes_gaps_without_legal_conclusions(self):
        build_regulatory_litigation_calendar(self.netflix)

        response = self.client.get("/companies/netflix/regulatory-litigation")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "partial")
        self.assertIn("does not make legal conclusions", payload["snapshot"]["legal_guardrail"])
        self.assertTrue(any(gap["key"] == "matter_list" for gap in payload["source_gaps"]))
        self.assertNotIn("liable", str(payload).lower())
        self.assertNotIn("guilty", str(payload).lower())

    def test_sector_theme_builder_creates_event_and_kpi_exposures(self):
        KpiDefinition.objects.create(
            company=self.netflix,
            slug="advertising-revenue",
            name="Advertising revenue",
            description="Revenue from advertising products.",
            unit="USD",
            cadence="QUARTERLY",
            scope="Advertising",
            peer_comparable=True,
        )

        result = build_sector_theme_intelligence(self.netflix)

        self.assertEqual(result["snapshots_created"], 1)
        snapshot = SectorThemeSnapshot.objects.get(company=self.netflix)
        self.assertGreaterEqual(snapshot.exposures.count(), 3)
        event_exposure = snapshot.exposures.get(source_key__startswith="event:")
        self.assertEqual(event_exposure.theme.name, "Advertising Cycle")
        self.assertEqual(event_exposure.exposure_type, "REVENUE")
        self.assertEqual(event_exposure.materiality, "OPERATING")
        self.assertNotIn("no event-linked theme exposure", sector_theme_quality_issues(self.netflix))

    def test_sector_theme_api_distinguishes_narrative_only_context(self):
        company = Company.objects.create(name="Theme Only Co", industry="Utilities", country="United States")
        build_sector_theme_intelligence(company)

        response = self.client.get(f"/companies/{company.slug}/sector-themes")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["coverage"]["operating_exposure_count"], 0)
        self.assertTrue(any(gap["key"] == "operating_exposure" for gap in payload["source_gaps"]))
        self.assertTrue(any(row["materiality"] == "NARRATIVE_ONLY" for row in payload["exposures"]))

    def test_macro_sensitivity_builder_creates_disclosed_and_placeholder_rows(self):
        build_sector_theme_intelligence(self.netflix)

        result = build_macro_sensitivity_profile(self.netflix)

        self.assertEqual(result["snapshots_created"], 1)
        snapshot = MacroSensitivitySnapshot.objects.get(company=self.netflix)
        self.assertGreaterEqual(snapshot.sensitivities.count(), 2)
        self.assertTrue(snapshot.sensitivities.filter(evidence_type="MANAGEMENT_DISCLOSED").exists())
        self.assertTrue(snapshot.sensitivities.filter(evidence_type="CALCULATED_PLACEHOLDER", sample_size=0).exists())
        self.assertNotIn("no reviewed macro sensitivities", macro_sensitivity_quality_issues(self.netflix))
        self.assertIn("does not claim causation", snapshot.limitation_note)

    def test_macro_sensitivity_api_exposes_limitations_and_gaps(self):
        build_macro_sensitivity_profile(self.netflix)

        response = self.client.get("/companies/netflix/macro-sensitivity")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"available", "partial"})
        self.assertGreaterEqual(payload["coverage"]["calculated_placeholder_count"], 1)
        self.assertTrue(any(gap["key"] == "macro_series_alignment" for gap in payload["source_gaps"]))
        rendered = str(payload).lower()
        self.assertNotIn("causes revenue", rendered)
        self.assertNotIn("will increase", rendered)

    def test_leadership_decision_builder_creates_roles_and_decisions(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            source_document=self.source,
            effective_date=date(2026, 1, 1),
            status="REVIEWED",
            summary="Netflix reviewed profile.",
            leadership=["Greg Peters - Co-CEO", "Ted Sarandos - Co-CEO"],
            strategic_priorities=["Scale advertising business"],
            confidence_score="0.850",
        )

        first = build_leadership_decision_record(self.netflix)
        second = build_leadership_decision_record(self.netflix)

        self.assertEqual(first["roles_created"], 2)
        self.assertGreaterEqual(first["decisions_created"], 1)
        self.assertEqual(second["roles_updated"], 2)
        snapshot = LeadershipDecisionSnapshot.objects.get(company=self.netflix)
        self.assertEqual(snapshot.status, "REVIEWED")
        self.assertEqual(snapshot.roles.count(), 2)
        self.assertNotIn("no reviewed leadership roles", leadership_decision_quality_issues(self.netflix))

    def test_leadership_decision_api_exposes_non_causation_and_gaps(self):
        CompanyProfileSnapshot.objects.create(
            company=self.netflix,
            source_document=self.source,
            effective_date=date(2026, 1, 1),
            status="REVIEWED",
            summary="Netflix reviewed profile.",
            leadership=["Greg Peters - Co-CEO"],
            confidence_score="0.850",
        )
        build_leadership_decision_record(self.netflix)

        response = self.client.get("/companies/netflix/leadership-decisions")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"available", "partial"})
        self.assertGreaterEqual(payload["coverage"]["role_count"], 1)
        self.assertEqual(payload["performance_context"]["status"], "unavailable")
        self.assertIn("does not claim", payload["performance_context"]["non_causation_note"])
        self.assertTrue(any(gap["key"] == "tenure_dates" for gap in payload["source_gaps"]))

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


class DailyCompanyUpdateTests(TestCase):
    def test_uses_current_annual_quarterly_and_current_report_filings_for_events(self):
        options = {
            "limit": 20,
            "offset": 0,
            "batch_size": 0,
            "sec_limit": 30,
            "wikipedia_limit": 10,
            "gdelt_records_per_query": 5,
            "gdelt_query_limit": 3,
            "skip_gdelt": True,
            "skip_event_extraction": False,
            "event_filing_limit": 8,
            "retry_failed_only": False,
            "include_market_data": False,
            "include_financial_facts": False,
            "include_insider_transactions": False,
            "include_official_product_prices": False,
            "insider_form_limit": 5,
            "include_macro_context": False,
            "include_quality_scoring": False,
            "include_company_profiles": False,
        }
        with patch("apps.ingestion.management.commands.daily_company_update.call_command") as call:
            DailyCompanyUpdateCommand().handle(**options)

        event_call = next(call_args for call_args in call.call_args_list if call_args.args[0] == "extract_sector_events")
        self.assertEqual(event_call.kwargs["forms"], "10-K,10-Q,8-K")
        self.assertTrue(event_call.kwargs["reuse_extractions"])

    def test_extracts_reports_and_enriches_energy_before_dashboard_builders(self):
        options = {
            "limit": 20,
            "offset": 0,
            "batch_size": 0,
            "sec_limit": 30,
            "wikipedia_limit": 10,
            "gdelt_records_per_query": 5,
            "gdelt_query_limit": 3,
            "skip_gdelt": True,
            "skip_event_extraction": True,
            "event_filing_limit": 8,
            "retry_failed_only": False,
            "include_market_data": False,
            "include_financial_facts": False,
            "include_insider_transactions": False,
            "include_official_product_prices": False,
            "insider_form_limit": 5,
            "include_macro_context": False,
            "include_quality_scoring": False,
            "include_company_profiles": True,
        }
        with patch("apps.ingestion.management.commands.daily_company_update.call_command") as call:
            DailyCompanyUpdateCommand().handle(**options)

        command_names = [call_args.args[0] for call_args in call.call_args_list]
        report_extraction = command_names.index("extract_report_filings")
        profile_refresh = command_names.index("refresh_company_profiles")
        energy_enrichment = command_names.index("enrich_energy_disclosures")
        self.assertLess(report_extraction, energy_enrichment)
        self.assertLess(report_extraction, profile_refresh)
        self.assertLess(profile_refresh, command_names.index("build_earnings_intelligence"))
        self.assertLess(energy_enrichment, command_names.index("build_product_pricing_history"))
        self.assertLess(energy_enrichment, command_names.index("build_geographic_expansions"))


class EnergySourceQualityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Energy Test Co", industry="Energy", country="United States")
        self.gap = SourceGap.objects.create(
            company=self.company,
            dashboard="product_pricing_history",
            gap_type="product_list_prices",
            provider="test",
            reason="Need verified product prices.",
            next_ingestion_task="Review first-party evidence.",
        )

    def candidate(self, *, source_api: str, evidence_text: str):
        source = SourceDocument.objects.create(
            company=self.company,
            source_api=source_api,
            url=f"https://example.com/{source_api.lower()}",
            title="Energy source",
            publisher="Test",
            language="en",
        )
        return SourceGapResolutionCandidate.objects.create(
            company=self.company,
            source_gap=self.gap,
            dashboard="product_pricing_history",
            gap_type="product_list_prices",
            candidate_type="product_price_source",
            source_document=source,
            evidence_text=evidence_text,
            confidence_score="0.800",
            extraction_status="EXTRACTED",
            review_status="NEEDS_REVIEW",
        )

    def test_energy_candidates_require_first_party_explicit_price_evidence(self):
        commodity_commentary = self.candidate(
            source_api="GDELT_DOC_2",
            evidence_text="Oil prices rose after market commentary.",
        )
        official_product_page = self.candidate(
            source_api="OFFICIAL_WEBSITE",
            evidence_text="Mobil lubricant product price is USD 12.00 per litre.",
        )

        self.assertFalse(is_promotable_energy_candidate(commodity_commentary))
        self.assertTrue(is_promotable_energy_candidate(official_product_page))


class EnergySectorEnrichmentTests(TestCase):
    def test_first_party_disclosure_creates_source_linked_energy_records(self):
        company = Company.objects.create(name="Energy Test Co", industry="Energy", country="United States")
        source = SourceDocument.objects.create(
            company=company,
            source_api="SEC_EDGAR",
            url="https://example.com/energy-10q",
            title="Energy Test Co 10-Q",
            publisher="SEC",
            language="en",
            published_date="2026-06-30",
        )
        ArticleExtraction.objects.create(
            source_document=source,
            clean_text=(
                "Advantaged assets include Guyana, Permian and LNG. "
                "High-value products include performance chemicals, performance lubricants, and lower-emission fuels."
            ),
            word_count=18,
            extraction_status="SUCCEEDED",
            extractor_name="test",
        )

        result = enrich_energy_disclosures(company)

        self.assertEqual(result["events_created"], 3)
        self.assertEqual(result["offerings_created"], 3)
        self.assertEqual(
            set(BusinessEvent.objects.filter(company=company).values_list("decision_theme", flat=True)),
            {"ENERGY_ASSET_GUYANA", "ENERGY_ASSET_PERMIAN", "ENERGY_ASSET_LNG"},
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
                "P571": [{"mainsnak": {"datavalue": {"value": {"time": "+1999-01-15T00:00:00Z", "precision": 11}}}}],
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
        self.assertEqual(company.founded_date_precision, "DAY")
        self.assertEqual(company.subsidiaries, ("Example Subsidiary",))
        self.assertEqual(company.products, ("Example Product",))
        self.assertEqual(company.brands, ("Example Brand",))
        self.assertEqual(company.leadership, ("Example CEO",))

    def test_verified_primary_founding_anchor_survives_wikidata_refresh(self):
        company = Company.objects.create(
            name="Anchor Guard Corp",
            founded_date=date(2000, 1, 1),
            founded_date_precision="DAY",
            founded_date_evidence="Official charter records January 1, 2000.",
            founded_date_source_url="https://example.com/charter",
            founding_anchor_status="VERIFIED",
        )

        _apply_company_details(
            company,
            WikidataCompany(
                wikidata_id="Q1",
                name="Anchor Guard Corp",
                founded_date=date(1999, 1, 15),
                founded_date_precision="DAY",
            ),
            save=True,
        )
        company.refresh_from_db()

        self.assertEqual(company.founded_date, date(2000, 1, 1))
        self.assertEqual(company.founded_date_source_url, "https://example.com/charter")
        self.assertEqual(company.founding_anchor_status, "VERIFIED")


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

    def test_sec_profile_builder_prefers_the_latest_filing_over_the_longest_extraction(self):
        company = Company.objects.create(name="ExxonMobil", slug="exxonmobil", country="United States")
        older_source = SourceDocument.objects.create(
            company=company,
            source_api="SEC_EDGAR",
            url="https://example.com/exxon-2024-10k",
            title="ExxonMobil 2024 10-K",
            published_date="2025-02-19T00:00:00Z",
        )
        latest_source = SourceDocument.objects.create(
            company=company,
            source_api="SEC_EDGAR",
            url="https://example.com/exxon-2025-10k",
            title="ExxonMobil 2025 10-K",
            published_date="2026-02-18T00:00:00Z",
        )
        ArticleExtraction.objects.create(
            source_document=older_source,
            clean_text="ITEM 1. Business Older filing content. ITEM 1A. Risk Factors",
            word_count=1000,
            extraction_status="SUCCEEDED",
        )
        ArticleExtraction.objects.create(
            source_document=latest_source,
            clean_text="ITEM 1. Business Latest filing content. ITEM 1A. Risk Factors",
            word_count=100,
            extraction_status="SUCCEEDED",
        )

        snapshot = build_sec_company_profile(company)

        self.assertEqual(snapshot.source_document, latest_source)
        self.assertEqual(snapshot.segments, ["Upstream", "Energy Products", "Chemical Products", "Specialty Products"])
        self.assertIn("Fuel and lubricant distributors", snapshot.customer_groups)
        self.assertIn("Fuel and lubricant sales", snapshot.revenue_sources)

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

    def test_parse_sec_profile_text_extracts_explicit_operating_and_revenue_regions(self):
        text = """
        ITEM 1. Business Netflix operates through UCAN, EMEA, LATAM, and APAC regions.
        Revenue is reported for UCAN, EMEA, LATAM, and APAC. ITEM 1A. Risk Factors
        """

        data = parse_sec_profile_text(text, "Netflix")

        expected_regions = ("UCAN", "EMEA", "LATAM", "APAC")
        self.assertEqual(data.operating_regions, expected_regions)
        self.assertEqual(data.revenue_geographies, expected_regions)

    def test_parse_sec_profile_text_reads_geographic_tables_outside_item_one(self):
        text = """
        ITEM 1. Business Example Energy produces energy products. ITEM 1A. Risk Factors
        Geographic area reserves include the United States, Canada/Other Americas,
        Europe, Africa, Asia, and Australia/Oceania. Net sales by geographic area
        include the United States, Europe, and Asia.
        """

        data = parse_sec_profile_text(text, "Example Energy")

        self.assertEqual(
            data.operating_regions,
            ("United States", "Canada/Other Americas", "Europe", "Africa", "Asia", "Australia/Oceania"),
        )
        self.assertEqual(data.revenue_geographies, ("United States", "Europe", "Asia"))

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

    def test_profile_quality_uses_the_same_snapshot_window_as_company_360(self):
        company = Company.objects.create(name="Window Corp", description="A company with a current profile gap.")
        source = SourceDocument.objects.create(
            company=company,
            source_api="SEC",
            url="https://example.com/window-corp-10k",
            title="Window Corp 10-K",
        )
        CompanyProfileSnapshot.objects.create(
            company=company,
            effective_date=date(2020, 1, 1),
            source_document=source,
            status="REVIEWED",
            summary="A complete historical company profile.",
            business_model="A sufficiently long historical business model description that should not satisfy current coverage.",
            subsidiaries=["Window Holdings"],
            brands=["Window"],
            segments=["Software"],
            products=["Window platform"],
            customer_groups=["Business customers"],
            revenue_sources=["Subscriptions"],
            geographies=["United States"],
            leadership=["Chief Executive Officer"],
            competitors=["Example competitor"],
            strategic_priorities=["Expand the platform"],
        )
        for index in range(20):
            CompanyProfileSnapshot.objects.create(
                company=company,
                effective_date=date(2025 + (index // 12), (index % 12) + 1, 1),
                source_document=source,
                status="REVIEWED",
                summary=f"Current profile refresh {index}.",
            )

        issues = company_profile_quality_issues(company)

        self.assertIn("products unavailable", issues)
        self.assertIn("revenue_sources unavailable", issues)

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

    def test_auto_provider_falls_back_to_stooq_without_api_keys(self):
        with patch.dict(os.environ, {"FMP_API_KEY": "", "ALPHA_VANTAGE_API_KEY": ""}, clear=False):
            client = build_market_client({"provider": "auto", "fmp_api_key": "", "alpha_vantage_api_key": ""})

        self.assertEqual(client.provider, "STOOQ")


class FmpFundamentalsTests(TestCase):
    def test_parses_only_curated_numeric_fields_with_a_period(self):
        facts = parse_fmp_fundamental_facts(
            [
                {"date": "2025-12-31", "calendarYear": "2025", "period": "FY", "revenue": 1000, "netIncome": "125", "eps": "2.5"},
                {"date": "not-a-date", "calendarYear": "2024", "period": "FY", "revenue": 900},
            ],
            endpoint="income-statement",
            concepts=FUNDAMENTAL_SERIES["income-statement"],
        )

        self.assertEqual([(fact.concept, str(fact.value)) for fact in facts], [
            ("income-statement:revenue", "1000"),
            ("income-statement:netIncome", "125"),
            ("income-statement:eps", "2.5"),
        ])
        self.assertEqual(facts[0].period_end.isoformat(), "2025-12-31")
        self.assertEqual(facts[0].fiscal_year, 2025)

    def test_ignores_non_list_payloads_and_invalid_values(self):
        facts = parse_fmp_fundamental_facts(
            {"error": "not entitled"},
            endpoint="ratios",
            concepts=FUNDAMENTAL_SERIES["ratios"],
        )

        self.assertEqual(facts, [])


class OfficialProductPriceTests(TestCase):
    def test_parses_only_explicit_json_ld_offers(self):
        prices = parse_official_prices(
            '''<script type="application/ld+json">{
                "@type": "Product", "name": "Example Pro", "offers": {
                  "@type": "Offer", "price": "19.99", "priceCurrency": "USD"
                }
            }</script><p>Prices may change.</p>'''
        )

        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0].name, "Example Pro")
        self.assertEqual(str(prices[0].amount), "19.99")
        self.assertEqual(prices[0].currency, "USD")

    def test_parses_explicit_price_specification(self):
        prices = parse_official_prices(
            '''<script type="application/ld+json">{
                "@type": "Product", "name": "Example Team", "offers": {
                  "@type": "Offer", "priceSpecification": {"price": "49", "priceCurrency": "USD"}
                }
            }</script>'''
        )

        self.assertEqual([(price.name, str(price.amount), price.currency) for price in prices], [("Example Team", "49", "USD")])

    def test_parses_explicit_schema_org_offer_microdata(self):
        prices = parse_official_prices(
            '''<article itemscope itemtype="https://schema.org/Product">
                <meta itemprop="name" content="Example Pro" />
                <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
                  <meta itemprop="price" content="29.00" />
                  <meta itemprop="priceCurrency" content="USD" />
                </div>
            </article>'''
        )

        self.assertEqual([(price.name, str(price.amount), price.currency) for price in prices], [("Example Pro", "29.00", "USD")])


class SecForm4IngestionTests(TestCase):
    xml = """<?xml version=\"1.0\"?>
    <ownershipDocument>
      <reportingOwner><reportingOwnerId><rptOwnerName>Jane Example</rptOwnerName></reportingOwnerId>
      <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>1</isOfficer><officerTitle>Chief Executive Officer</officerTitle></reportingOwnerRelationship></reportingOwner>
      <footnotes><footnote id=\"F1\">Sale pursuant to a Rule 10b5-1 plan.</footnote></footnotes>
      <nonDerivativeTable><nonDerivativeTransaction>
        <transactionDate><value>2026-07-21</value></transactionDate>
        <transactionCoding><transactionCode>S</transactionCode><footnoteId id=\"F1\" /></transactionCoding>
        <transactionAmounts><transactionShares><value>1250</value></transactionShares><transactionPricePerShare><value>99.50</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts>
        <postTransactionAmounts><sharesOwnedFollowingTransaction><value>5000</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
      </nonDerivativeTransaction></nonDerivativeTable>
      <nonDerivativeTable><nonDerivativeHolding>
        <securityTitle><value>Common Stock</value></securityTitle>
        <postTransactionAmounts><sharesOwnedFollowingTransaction><value>5000</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
      </nonDerivativeHolding></nonDerivativeTable>
      <derivativeTable><derivativeTransaction>
        <transactionDate><value>2026-07-21</value></transactionDate>
        <transactionCoding><transactionCode>M</transactionCode></transactionCoding>
        <transactionAmounts><transactionShares><value>300</value></transactionShares><transactionPricePerShare><value>2.50</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
      </derivativeTransaction></derivativeTable>
    </ownershipDocument>"""

    def setUp(self):
        self.company = Company.objects.create(name="Example Corp", aliases=["EXM"], country="United States")
        self.source = SourceDocument.objects.create(
            company=self.company,
            source_api="SEC_EDGAR",
            url="https://www.sec.gov/Archives/edgar/data/1/000012345626000001/form4.xml",
            title="Example Corp 4 filing 2026-07-22",
            publisher="SEC EDGAR",
            published_date="2026-07-22T00:00:00Z",
        )

    def test_parser_keeps_form4_code_and_10b5_1_evidence(self):
        rows = parse_ownership_xml(self.xml)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].insider_name, "Jane Example")
        self.assertEqual(rows[0].transaction_type, "SALE")
        self.assertEqual(rows[0].transaction_code, "S")
        self.assertTrue(rows[0].planned_sale)
        self.assertEqual(str(rows[0].value), "124375.00")
        self.assertEqual(rows[1].transaction_type, "EXERCISE")

    def test_parser_keeps_explicit_non_derivative_holdings(self):
        holdings = parse_ownership_holdings(self.xml)

        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0].holder_name, "Jane Example")
        self.assertEqual(holdings[0].holder_type, "EXECUTIVE")
        self.assertEqual(str(holdings[0].shares_owned), "5000")
        self.assertEqual(holdings[0].share_class, "Common Stock")

    def test_normalizes_edgar_xsl_url_to_the_original_xml(self):
        self.assertEqual(
            ownership_xml_url("https://www.sec.gov/Archives/edgar/data/1/000012345626000001/xslF345X06/form4.xml"),
            "https://www.sec.gov/Archives/edgar/data/1/000012345626000001/form4.xml",
        )

    def test_fallback_candidates_use_the_accession_index_xml_files(self):
        source_url = "https://www.sec.gov/Archives/edgar/data/1/000012345626000001/xslF345X06/presentation.xml"

        candidates = ownership_xml_candidates(
            source_url,
            {"directory": {"item": [{"name": "presentation.xml"}, {"name": "ownership.xml"}, {"name": "primary.htm"}]}},
        )

        self.assertEqual(candidates, ["https://www.sec.gov/Archives/edgar/data/1/000012345626000001/ownership.xml"])

    def test_ingestion_falls_back_to_accession_index_for_presentation_html(self):
        presentation_url = self.source.url
        index_url = "https://www.sec.gov/Archives/edgar/data/1/000012345626000001/index.json"
        ownership_url = "https://www.sec.gov/Archives/edgar/data/1/000012345626000001/ownership.xml"
        session = FakeForm4FallbackSession(self.xml, presentation_url, index_url, ownership_url)

        result = ingest_form4_sources(company=self.company, sources=form4_sources(self.company), session=session)

        self.assertEqual(result["sources_parsed"], 1)
        self.assertEqual(result["transactions_inserted"], 2)
        self.assertEqual(session.calls, [presentation_url, index_url, ownership_url])

    def test_ingestion_uses_existing_form4_source_and_is_idempotent(self):
        session = FakeForm4Session(self.xml)

        first = ingest_form4_sources(company=self.company, sources=form4_sources(self.company), session=session)
        second = ingest_form4_sources(company=self.company, sources=form4_sources(self.company), session=session)
        snapshot = OwnershipInsiderSnapshot.objects.get(company=self.company, effective_date=date(2026, 7, 22))
        row = snapshot.insider_transactions.get(transaction_code="S")

        self.assertEqual(first["transactions_inserted"], 2)
        self.assertEqual(second["transactions_updated"], 2)
        self.assertEqual(first["holdings_inserted"], 1)
        self.assertEqual(second["holdings_updated"], 1)
        self.assertEqual(row.filing_accession_number, "0000123456-26-000001")
        self.assertEqual(row.insider_role, "Director; Chief Executive Officer")
        self.assertEqual(row.source_document, self.source)
        position = snapshot.positions.get(position_type="BENEFICIAL_OWNERSHIP")
        self.assertEqual(str(position.shares_owned), "5000.000000")
        self.assertEqual(position.share_class, "Common Stock")


class FakeForm4Session:
    def __init__(self, xml):
        self.xml = xml
        self.headers = {}

    def get(self, url, timeout):
        return FakeProfileResponse(url=url, text=self.xml)


class FakeForm4FallbackSession:
    def __init__(self, xml, presentation_url, index_url, ownership_url):
        self.xml = xml
        self.presentation_url = presentation_url
        self.index_url = index_url
        self.ownership_url = ownership_url
        self.headers = {}
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(url)
        if url == self.presentation_url:
            return FakeProfileResponse(url=url, text="<html><body>Presentation page</body></html>")
        if url == self.index_url:
            return FakeForm4IndexResponse(url=url, text='{"directory": {"item": [{"name": "ownership.xml"}]}}')
        if url == self.ownership_url:
            return FakeProfileResponse(url=url, text=self.xml)
        raise AssertionError(f"Unexpected URL: {url}")


class FakeForm4IndexResponse(FakeProfileResponse):
    def json(self):
        return {"directory": {"item": [{"name": "ownership.xml"}]}}

class EventTypeChoiceTests(TestCase):
    def test_company_formation_is_available_for_historical_founder_evidence(self):
        self.assertIn(("COMPANY_FORMATION", "Company formation"), EventType.choices)


class LifecycleTimingEligibilityTests(TestCase):
    def valid_event(self):
        return SimpleNamespace(
            lifecycle_timing_status="VERIFIED",
            action_date=date(2014, 4, 3),
            action_date_precision="DAY",
            action_date_evidence="The company announced the action on April 3, 2014.",
            lifecycle_context_json={"as_of_date": "2014-12-31", "source_url": "https://example.com/primary", "metrics": [{"label": "Revenue", "value": "$394bn"}], "company_lifecycle_stage": "MATURITY", "company_lifecycle_stage_evidence": "The company was an established operator.", "company_lifecycle_stage_source_url": "https://example.com/primary"},
            company=SimpleNamespace(
                founded_date=date(1882, 8, 5),
                id=1,
                founded_date_precision="DAY",
                founded_date_evidence="Official founding record.",
                founded_date_source_url="https://example.com/founding",
                founding_anchor_status="VERIFIED",
            ),
            lifecycle_episode=SimpleNamespace(verification_status="VERIFIED", company_id=1, contains=lambda action_date: True),
        )

    def test_verified_lifecycle_timing_requires_an_auditable_evidence_chain(self):
        result = lifecycle_timing_eligibility(self.valid_event())
        self.assertTrue(result.eligible)
        self.assertEqual(result.status, "ELIGIBLE")

    def test_historical_primary_source_can_replace_sec_era_scale_context(self):
        event = self.valid_event()
        event.lifecycle_context_json = {
            "evidence_mode": "HISTORICAL_PRIMARY_SOURCE",
            "source_url": "https://example.com/archival-primary-source",
        }
        self.assertTrue(lifecycle_timing_eligibility(event).eligible)

    def test_source_publication_date_cannot_substitute_for_actual_action_timing(self):
        event = self.valid_event()
        event.action_date = None
        event.lifecycle_timing_status = "PENDING"
        result = lifecycle_timing_eligibility(event)
        self.assertFalse(result.eligible)
        self.assertIn("missing_actual_action_date", result.reasons)
        self.assertIn("lifecycle_timing_not_verified", result.reasons)

class HistoricalPrimaryEventEligibilityTests(TestCase):
    def test_verified_historical_primary_action_uses_exact_action_date(self):
        event = SimpleNamespace(
            event_date=None,
            action_date=date(1977, 4, 16),
            actual_change="Apple debuted the Apple II at the first West Coast Computer Faire.",
            source_claim="Apple’s official historical record dates this action to April 16, 1977.",
            evidence_text="Apple debuted the Apple II at the first West Coast Computer Faire on April 16, 1977.",
            confidence_score="1.000",
            source_document_id=1,
            raw_extraction_json={"provenance": "HISTORICAL_PRIMARY_SOURCE"},
            lifecycle_context_json={"evidence_mode": "HISTORICAL_PRIMARY_SOURCE", "source_url": "https://example.com/apple-history"},
        )

        result = event_eligibility(event)

        self.assertTrue(result.eligible)
        self.assertNotIn("missing_event_date", result.reasons)
        self.assertNotIn("missing_specific_company_action", result.reasons)


class LifecycleTimingBackfillTests(TestCase):
    def test_extracts_only_explicit_action_day_not_publication_day(self):
        extracted = exact_action_date_from_evidence(
            "The company announced on March 14, 2019 that the platform would launch."
        )
        self.assertEqual(extracted[0].isoformat(), "2019-03-14")
        self.assertEqual(
            exact_action_date_from_evidence("The acquisition closed August 5, 2019.")[0].isoformat(),
            "2019-08-05",
        )
        self.assertIsNone(exact_action_date_from_evidence("On March 14, 2019, the company received a notice."))
        self.assertIsNone(exact_action_date_from_evidence("The company announced a platform launch in 2019."))

    def test_backfill_recovers_event_evidence_date_before_full_lifecycle_eligibility(self):
        from apps.ingestion.management.commands.backfill_lifecycle_timing import Command

        company = Company.objects.create(name="Exact Date Recovery Co")
        event = BusinessEvent.objects.create(
            company=company,
            event_type="PRODUCT_EXPANSION",
            evidence_text="On April 3, 2014, Exact Date Recovery Co launched its first product.",
        )

        Command().handle(company=[company.name], dry_run=False, limit=0)

        event.refresh_from_db()
        self.assertEqual(event.action_date, date(2014, 4, 3))
        self.assertEqual(event.action_date_precision, "DAY")
        self.assertEqual(event.action_date_evidence, "On April 3, 2014, Exact Date Recovery Co launched its first product.")
        self.assertEqual(event.lifecycle_timing_status, "PENDING")

    def test_uses_only_financial_fact_known_at_the_action_date(self):
        company = SimpleNamespace(sec_cik="0000320193")
        fact = SimpleNamespace(
            concept="Revenues", label="Revenue", value="1000000000", unit="USD",
            accession_number="0000320193-19-000010", filed=date(2019, 2, 1), raw={"end": "2018-12-31"},
        )
        context = lifecycle_context_from_financial_facts(
            company=company, action_date=date(2019, 3, 14), financial_facts=[fact]
        )
        self.assertEqual(context["as_of_date"], "2018-12-31")
        self.assertIn("sec.gov/Archives/edgar/data/320193/", context["source_url"])

class FoundingAnchorEligibilityTests(TestCase):
    def test_rejects_structured_but_accepts_precisely_disclosed_year_anchor(self):
        event = SimpleNamespace(
            lifecycle_timing_status="VERIFIED",
            action_date=date(2014, 4, 3),
            action_date_precision="DAY",
            action_date_evidence="The project began on April 3, 2014.",
            lifecycle_context_json={"as_of_date": "2014-03-31", "source_url": "https://sec.gov/example", "metrics": [{"label": "Revenue", "value": "$1B"}], "company_lifecycle_stage": "MATURITY", "company_lifecycle_stage_evidence": "The company was an established operator.", "company_lifecycle_stage_source_url": "https://sec.gov/example"},
            company=SimpleNamespace(
                founded_date=date(1990, 1, 1), founded_date_precision="YEAR",
                founded_date_evidence="Structured source", founded_date_source_url="https://wikidata.org/wiki/Q1",
                founding_anchor_status="STRUCTURED",
            ),
        )
        result = lifecycle_timing_eligibility(event)
        self.assertFalse(result.eligible)
        self.assertIn("founding_anchor_not_verified", result.reasons)

class FoundingAnchorPrecisionTests(TestCase):
    def test_accepts_verified_year_precision_without_fabricating_a_day(self):
        event = SimpleNamespace(
            lifecycle_timing_status="VERIFIED", action_date=date(2014, 4, 3), action_date_precision="DAY",
            action_date_evidence="The project began on April 3, 2014.",
            lifecycle_context_json={"as_of_date": "2014-03-31", "source_url": "https://sec.gov/example", "metrics": [{"label": "Revenue", "value": "$1B"}], "company_lifecycle_stage": "MATURITY", "company_lifecycle_stage_evidence": "The company was an established operator.", "company_lifecycle_stage_source_url": "https://sec.gov/example"},
            company=SimpleNamespace(
                id=1,
                founded_date=date(1849, 1, 1), founded_date_precision="YEAR",
                founded_date_evidence="Company history says it was founded in 1849.",
                founded_date_source_url="https://example.com/history", founding_anchor_status="VERIFIED",
            ),
            lifecycle_episode=SimpleNamespace(verification_status="VERIFIED", company_id=1, contains=lambda action_date: True),
        )
        self.assertTrue(lifecycle_timing_eligibility(event).eligible)

class LifecycleTimingSourceGapTests(TestCase):
    def test_records_a_company_level_gap_when_founding_anchor_is_missing(self):
        from apps.ingestion.management.commands.backfill_lifecycle_timing import Command

        company = Company.objects.create(name="Lifecycle Gap Co")
        Command()._reconcile_company_source_gaps({company}, dry_run=False)

        gap = SourceGap.objects.get(
            company=company, dashboard="FOUNDER_DECISION", gap_type="LIFECYCLE_TIMING", provider="PRIMARY_SOURCE"
        )
        self.assertEqual(gap.status, "OPEN")
        self.assertEqual(gap.metadata["missing"], ["founding_anchor"])

class LifecycleBackfillAdmissionTests(TestCase):
    def test_backfill_requires_a_verified_founding_anchor(self):
        from apps.ingestion.management.commands.backfill_lifecycle_timing import Command

        pending = SimpleNamespace(
            founded_date=date(1994, 7, 5), founded_date_precision="DAY",
            founded_date_evidence="Candidate source", founded_date_source_url="https://example.com",
            founding_anchor_status="PENDING",
        )
        verified = SimpleNamespace(
            founded_date=date(1994, 7, 5), founded_date_precision="DAY",
            founded_date_evidence="Official history", founded_date_source_url="https://example.com",
            founding_anchor_status="VERIFIED",
        )
        self.assertFalse(Command._has_verified_founding_anchor(pending))
        self.assertTrue(Command._has_verified_founding_anchor(verified))

class LifecycleEpisodeModelGuardTests(TestCase):
    def test_verified_episode_requires_primary_source_evidence(self):
        company = Company.objects.create(name="Episode Guard Co")
        episode = LifecycleEpisode(
            company=company,
            scope="COMPANY",
            stage="LAUNCH",
            start_date=date(2014, 4, 3),
            start_date_precision="DAY",
            verification_status="VERIFIED",
        )

        with self.assertRaises(ValidationError):
            episode.save()

    def test_verified_event_requires_a_verified_episode_for_its_company(self):
        company = Company.objects.create(
            name="Episode Event Co", founded_date=date(2013, 1, 1),
            founded_date_precision="DAY", founded_date_evidence="Official record.",
            founded_date_source_url="https://example.com/founding", founding_anchor_status="VERIFIED",
        )
        event = BusinessEvent(
            company=company, event_type="PRODUCT_EXPANSION", event_date=date(2014, 4, 3),
            action_date=date(2014, 4, 3), action_date_precision="DAY",
            action_date_evidence="On April 3, 2014, the company launched the product.",
            lifecycle_context_json={"as_of_date": "2014-03-31", "source_url": "https://example.com/filing", "metrics": [{"label": "Revenue", "value": "$1M"}]},
            lifecycle_timing_status="VERIFIED",
        )

        with self.assertRaises(ValidationError):
            event.save()

    def test_verified_event_cannot_bypass_lifecycle_validation(self):
        from django.core.exceptions import ValidationError

        company = Company.objects.create(name="Guarded Lifecycle Co")
        event = BusinessEvent(
            company=company, event_type="ACQUISITION", lifecycle_timing_status="VERIFIED",
        )
        with self.assertRaises(ValidationError):
            event.save()

    def test_complete_verified_event_saves(self):
        company = Company.objects.create(
            name="Verified Lifecycle Co", founded_date=date(2000, 1, 1),
            founded_date_precision="DAY", founded_date_evidence="Official record.",
            founded_date_source_url="https://example.com/founding", founding_anchor_status="VERIFIED",
        )
        episode = LifecycleEpisode.objects.create(
            company=company, scope="COMPANY", stage="SCALE", start_date=date(2020, 1, 2),
            start_date_precision="DAY", evidence_text="The company had repeated multi-market operations.",
            source_url="https://example.com/lifecycle", verification_status="VERIFIED",
        )
        event = BusinessEvent(
            company=company, event_type="ACQUISITION", event_date=date(2020, 1, 2),
            action_date=date(2020, 1, 2), action_date_precision="DAY",
            action_date_evidence="On January 2, 2020, the company acquired Example Co.",
            lifecycle_context_json={"as_of_date": "2019-12-31", "source_url": "https://sec.gov/example", "metrics": [{"label": "Revenue", "value": "$1B"}], "company_lifecycle_stage": "SCALE", "company_lifecycle_stage_evidence": "The company had repeated multi-market operations.", "company_lifecycle_stage_source_url": "https://sec.gov/example"},
            lifecycle_episode=episode,
            lifecycle_timing_status="VERIFIED",
        )
        event.save()
        self.assertEqual(event.lifecycle_timing_status, "VERIFIED")



class FoundingAnchorImportTests(TestCase):
    def test_imports_verified_source_backed_anchor(self):
        import json
        import tempfile

        company = Company.objects.create(name="Anchor Import Co")
        record = [{
            "company_slug": company.slug,
            "founded_date": "2001-02-03",
            "precision": "DAY",
            "evidence_text": "The issuer charter records incorporation on February 3, 2001.",
            "source_url": "https://example.com/charter",
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as payload:
            json.dump(record, payload)
            payload.flush()
            call_command("import_founding_anchors", input=payload.name)

        company.refresh_from_db()
        self.assertEqual(company.founded_date, date(2001, 2, 3))
        self.assertEqual(company.founded_date_precision, "DAY")
        self.assertEqual(company.founding_anchor_status, "VERIFIED")
        self.assertEqual(company.founded_date_source_url, "https://example.com/charter")

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


NETFLIX_COMPANY = {
    "name": "Netflix",
    "slug": "netflix",
    "aliases": ["Netflix", "Netflix Inc.", "Netflix.com"],
    "country": "United States",
    "wikidata_id": "Q907311",
    "website": "https://www.netflix.com",
    "industry": "Entertainment",
    "description": "American subscription streaming service and production company.",
    "is_active": True,
}

SAMPLE_SOURCE = {
    "source_api": "MANUAL",
    "url": "https://about.netflix.com/en/news/announcing-basic-with-ads-us",
    "canonical_url": "https://about.netflix.com/en/news/announcing-basic-with-ads-us",
    "title": "Netflix announces Basic with Ads",
    "publisher": "Netflix",
    "published_date": datetime(2022, 10, 13, tzinfo=timezone.utc),
    "snippet": "Netflix announced a lower-priced ad-supported plan for launch in November 2022.",
    "language": "en",
    "status": "APPROVED",
}

SAMPLE_EVENT = {
    "event_date": date(2022, 10, 13),
    "event_type": "REVENUE_MODEL_EXPANSION",
    "lifecycle_stage": "MATURITY",
    "before_state": "Subscription-only streaming revenue model",
    "after_state": "Subscription plus advertising-supported tier",
    "trigger": "Subscriber growth pressure and market saturation",
    "decision": "Introduce a lower-priced ad-supported plan",
    "outcome": "Opened advertising as a new revenue channel",
    "evidence_text": "Netflix announced Basic with Ads as a lower-priced ad-supported plan.",
    "confidence_score": Decimal("0.85"),
    "review_status": "NEEDS_REVIEW",
}

SAMPLE_PROFILE_SOURCE = {
    "source_api": "SEC_EDGAR",
    "url": "https://www.sec.gov/Archives/edgar/data/1065280/000106528023000017/nflx-20221231.htm",
    "canonical_url": "https://www.sec.gov/Archives/edgar/data/1065280/000106528023000017/nflx-20221231.htm",
    "title": "Netflix 2022 Form 10-K",
    "publisher": "SEC",
    "published_date": datetime(2023, 1, 27, tzinfo=timezone.utc),
    "snippet": "Netflix describes its streaming business, members, revenue, international operations, competition, leadership, and strategy.",
    "language": "en",
    "status": "APPROVED",
}

SAMPLE_HISTORICAL_MODEL_SOURCE = {
    "source_api": "SEC_EDGAR",
    "url": "https://www.sec.gov/Archives/edgar/data/1065280/000119312512071228/d260853d10k.htm",
    "canonical_url": "https://www.sec.gov/Archives/edgar/data/1065280/000119312512071228/d260853d10k.htm",
    "title": "Netflix 2011 Form 10-K",
    "publisher": "SEC",
    "published_date": datetime(2012, 2, 10, tzinfo=timezone.utc),
    "snippet": "Netflix reported domestic streaming, international streaming, and domestic DVD operations.",
    "language": "en",
    "status": "APPROVED",
}

SAMPLE_TURN = {
    "title": "Netflix launches ad-supported subscription tier",
    "turn_type": "REVENUE_MODEL_EXPANSION",
    "start_date": date(2022, 4, 1),
    "end_date": date(2022, 11, 30),
    "lifecycle_stage": "MATURITY",
    "summary": "Netflix expanded from pure subscription streaming into an advertising-supported plan.",
    "before_state": "Subscription-only streaming revenue model",
    "after_state": "Subscription plus advertising-supported tier",
    "trigger": "Subscriber growth pressure and market saturation",
    "decision": "Introduce a lower-priced ad-supported plan",
    "outcome": "Opened advertising as a new revenue channel",
    "founder_lesson": (
        "When the core model matures, add a complementary revenue model without "
        "abandoning the main one."
    ),
    "confidence_score": Decimal("0.85"),
    "review_status": "NEEDS_REVIEW",
    "is_published": False,
}

SAMPLE_PROFILE = {
    "effective_date": date(2022, 10, 13),
    "status": "REVIEWED",
    "summary": "Netflix is a global entertainment service offering streaming plans and producing content.",
    "business_model": "Netflix earns subscription revenue and expanded into advertising through an ad-supported plan.",
    "subsidiaries": ["Netflix Studios"],
    "brands": ["Netflix"],
    "segments": ["Streaming entertainment"],
    "products": ["Streaming plans", "Ad-supported streaming plan", "Original films and series"],
    "customer_groups": ["Streaming members", "Advertisers"],
    "revenue_sources": ["Subscriptions", "Advertising"],
    "geographies": ["United States", "International markets"],
    "leadership": [{"name": "Netflix executive team", "role": "Company leadership"}],
    "competitors": ["Disney+", "Prime Video", "YouTube", "Traditional entertainment providers"],
    "strategic_priorities": ["Grow advertising", "Improve member value", "Expand global entertainment reach"],
    "evidence_text": "Netflix announced Basic with Ads as a lower-priced ad-supported streaming plan.",
    "confidence_score": Decimal("0.85"),
}


class Command(BaseCommand):
    help = "Seed Netflix and a manually curated sample strategic turn for admin review."

    def handle(self, *args, **options):
        company_model = self._required_model("companies", "Company")
        source_model = self._optional_model("ingestion", "SourceDocument")
        event_model = self._optional_model("curation", "BusinessEvent")
        turn_model = self._optional_model("curation", "StrategicTurn")
        turn_source_model = self._optional_model("curation", "StrategicTurnSource")
        profile_model = self._optional_model("companies", "CompanyProfileSnapshot")
        business_model_snapshot = self._optional_model("companies", "BusinessModelSnapshot")
        business_model_component = self._optional_model("companies", "BusinessModelComponent")
        business_model_relationship = self._optional_model("companies", "BusinessModelRelationship")
        kpi_definition = self._optional_model("companies", "KpiDefinition")
        kpi_definition_version = self._optional_model("companies", "KpiDefinitionVersion")
        kpi_observation = self._optional_model("companies", "KpiObservation")

        with transaction.atomic():
            company = self._upsert_company(company_model)
            source = self._upsert_source(source_model, company) if source_model else None
            profile_source = self._upsert_source(source_model, company, values=SAMPLE_PROFILE_SOURCE) if source_model else None
            historical_model_source = self._upsert_source(source_model, company, values=SAMPLE_HISTORICAL_MODEL_SOURCE) if source_model else None
            event = self._upsert_event(event_model, company, source) if event_model else None
            turn = self._upsert_turn(turn_model, company) if turn_model else None
            if turn_source_model and turn and source:
                self._upsert_turn_source(turn_source_model, turn, source, event)
            if profile_model and profile_source:
                self._upsert_profile(profile_model, company, profile_source)
            if all((business_model_snapshot, business_model_component, business_model_relationship, profile_source, historical_model_source)):
                self._upsert_business_model_maps(
                    business_model_snapshot,
                    business_model_component,
                    business_model_relationship,
                    company,
                    historical_model_source,
                    profile_source,
                )
            if all((kpi_definition, kpi_definition_version, kpi_observation, profile_source)):
                self._upsert_operating_kpis(
                    kpi_definition, kpi_definition_version, kpi_observation, company, profile_source
                )

        self.stdout.write(self.style.SUCCESS("Seeded Netflix admin review data."))
        if source_model is None:
            self.stdout.write(self.style.WARNING("Skipped SourceDocument sample; model is not available."))
        if event_model is None:
            self.stdout.write(self.style.WARNING("Skipped BusinessEvent sample; model is not available."))
        if turn_model is None:
            self.stdout.write(self.style.WARNING("Skipped StrategicTurn sample; model is not available."))

    def _required_model(self, app_label, model_name):
        model = self._optional_model(app_label, model_name)
        if model is None:
            raise CommandError(f"Required model {app_label}.{model_name} is not available yet.")
        return model

    def _optional_model(self, app_label, model_name):
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            return None

    def _upsert_company(self, model):
        defaults = self._filter_model_values(model, NETFLIX_COMPANY)
        aliases = defaults.get("aliases")
        if aliases is not None:
            defaults["aliases"] = self._coerce_aliases(model, aliases)
        company, _created = model.objects.update_or_create(slug="netflix", defaults=defaults)
        return company

    def _upsert_source(self, model, company, *, values=None):
        values = dict(values or SAMPLE_SOURCE)
        values["company"] = company
        values["url_hash"] = self._sha256(values["canonical_url"])
        values["title_hash"] = self._sha256(values["title"].lower())
        defaults = self._filter_model_values(model, values)
        lookup = {"url_hash": values["url_hash"]} if self._has_field(model, "url_hash") else {"url": values["url"]}
        source, _created = model.objects.update_or_create(**lookup, defaults=defaults)
        return source

    def _upsert_event(self, model, company, source):
        values = dict(SAMPLE_EVENT)
        values["company"] = company
        if source is not None and self._has_field(model, "source_document"):
            values["source_document"] = source
        defaults = self._filter_model_values(model, values)
        lookup = {
            "company": company,
            "event_type": SAMPLE_EVENT["event_type"],
            "event_date": SAMPLE_EVENT["event_date"],
            "decision": SAMPLE_EVENT["decision"],
        }
        lookup = {key: value for key, value in lookup.items() if self._has_field(model, key)}
        event, _created = model.objects.update_or_create(**lookup, defaults=defaults)
        return event

    def _upsert_turn(self, model, company):
        values = dict(SAMPLE_TURN)
        values["company"] = company
        defaults = self._filter_model_values(model, values)
        lookup = {"company": company, "title": SAMPLE_TURN["title"]}
        turn, _created = model.objects.update_or_create(**lookup, defaults=defaults)
        return turn

    def _upsert_turn_source(self, model, turn, source, event):
        values = {
            "strategic_turn": turn,
            "source_document": source,
            "business_event": event,
            "evidence_text": SAMPLE_EVENT["evidence_text"],
        }
        defaults = self._filter_model_values(model, values)
        lookup = {
            "strategic_turn": turn,
            "source_document": source,
        }
        if event is not None and self._has_field(model, "business_event"):
            lookup["business_event"] = event
        model.objects.update_or_create(**lookup, defaults=defaults)

    def _upsert_profile(self, model, company, source):
        values = dict(SAMPLE_PROFILE)
        values["company"] = company
        values["source_document"] = source
        defaults = self._filter_model_values(model, values)
        model.objects.update_or_create(
            company=company,
            effective_date=SAMPLE_PROFILE["effective_date"],
            source_document=source,
            defaults=defaults,
        )

    def _upsert_business_model_maps(self, snapshot_model, component_model, relationship_model, company, historical_source, current_source):
        maps = [
            {
                "effective_date": date(2011, 12, 31),
                "source": historical_source,
                "summary": "Netflix combined streaming subscriptions with a declining DVD-by-mail service.",
                "components": [
                    ("PAYER", "Streaming members"),
                    ("PAYER", "DVD members"),
                    ("USER", "Entertainment viewers"),
                    ("OFFERING", "Streaming plans"),
                    ("OFFERING", "DVD-by-mail plans"),
                    ("REVENUE", "Subscription fees"),
                    ("CHANNEL", "Internet streaming"),
                    ("CHANNEL", "Postal delivery"),
                    ("GEOGRAPHY", "United States"),
                    ("GEOGRAPHY", "International markets"),
                    ("COST", "Content licensing"),
                    ("ASSET", "Recommendation and streaming platform"),
                ],
                "relationships": [
                    ("Streaming members", "PAYS_FOR", "Streaming plans"),
                    ("DVD members", "PAYS_FOR", "DVD-by-mail plans"),
                    ("Entertainment viewers", "USES", "Streaming plans"),
                    ("Streaming plans", "DELIVERED_THROUGH", "Internet streaming"),
                    ("DVD-by-mail plans", "DELIVERED_THROUGH", "Postal delivery"),
                    ("Streaming plans", "MONETIZED_BY", "Subscription fees"),
                ],
            },
            {
                "effective_date": date(2022, 12, 31),
                "source": current_source,
                "summary": "Netflix combined global streaming subscriptions with a new advertising-supported plan.",
                "components": [
                    ("PAYER", "Streaming members"),
                    ("PAYER", "Advertisers"),
                    ("USER", "Entertainment viewers"),
                    ("OFFERING", "Streaming plans"),
                    ("OFFERING", "Ad-supported plan"),
                    ("REVENUE", "Subscription fees"),
                    ("REVENUE", "Advertising revenue"),
                    ("CHANNEL", "Internet-connected devices"),
                    ("GEOGRAPHY", "Global markets"),
                    ("PARTNER", "Advertising technology partners"),
                    ("COST", "Content production and licensing"),
                    ("ASSET", "Global streaming and recommendation platform"),
                ],
                "relationships": [
                    ("Streaming members", "PAYS_FOR", "Streaming plans"),
                    ("Advertisers", "BUYS_ACCESS_TO", "Ad-supported plan"),
                    ("Entertainment viewers", "USES", "Streaming plans"),
                    ("Entertainment viewers", "USES", "Ad-supported plan"),
                    ("Streaming plans", "MONETIZED_BY", "Subscription fees"),
                    ("Ad-supported plan", "MONETIZED_BY", "Advertising revenue"),
                    ("Streaming plans", "DELIVERED_THROUGH", "Internet-connected devices"),
                ],
            },
        ]
        for map_data in maps:
            snapshot, _created = snapshot_model.objects.update_or_create(
                company=company,
                effective_date=map_data["effective_date"],
                source_document=map_data["source"],
                defaults={"status": "REVIEWED", "summary": map_data["summary"], "confidence_score": Decimal("0.85")},
            )
            snapshot.components.all().delete()
            components = {}
            for component_type, name in map_data["components"]:
                components[name] = component_model.objects.create(
                    snapshot=snapshot,
                    component_type=component_type,
                    name=name,
                    evidence_text=map_data["source"].snippet,
                    confidence_score=Decimal("0.85"),
                )
            for from_name, relationship_type, to_name in map_data["relationships"]:
                relationship_model.objects.create(
                    snapshot=snapshot,
                    from_component=components[from_name],
                    to_component=components[to_name],
                    relationship_type=relationship_type,
                    evidence_text=map_data["source"].snippet,
                    confidence_score=Decimal("0.80"),
                )

    def _upsert_operating_kpis(self, definition_model, version_model, observation_model, company, source):
        memberships, _created = definition_model.objects.update_or_create(
            company=company,
            slug="paid-memberships",
            defaults={
                "name": "Paid memberships",
                "description": "Paid streaming memberships at the end of the reporting period.",
                "unit": "million memberships",
                "cadence": "QUARTERLY",
                "value_type": "REPORTED",
                "scope": "Global streaming",
                "aliases": ["paid subscribers", "paid streaming memberships"],
                "peer_comparable": False,
            },
        )
        version_model.objects.update_or_create(
            kpi=memberships,
            effective_date=date(2022, 1, 1),
            defaults={
                "definition": "Paid memberships are memberships with the right to receive Netflix service following sign-up and payment.",
                "scope": "Global streaming",
                "change_note": "Company terminology preserved; comparison is blocked against peers without a reviewed matching definition.",
                "source_document": source,
            },
        )
        reported = [
            (date(2022, 3, 31), "Q1", Decimal("221.641"), ""),
            (date(2022, 6, 30), "Q2", Decimal("220.672"), ""),
            (date(2022, 9, 30), "Q3", Decimal("223.085"), ""),
            (date(2022, 12, 31), "Q4", Decimal("230.747"), ""),
            (date(2022, 12, 31), "Q4", Decimal("74.296"), "UCAN"),
            (date(2022, 12, 31), "Q4", Decimal("76.729"), "EMEA"),
            (date(2022, 12, 31), "Q4", Decimal("41.699"), "LATAM"),
            (date(2022, 12, 31), "Q4", Decimal("38.023"), "APAC"),
        ]
        for period_end, fiscal_period, value, geography in reported:
            observation_model.objects.update_or_create(
                kpi=memberships,
                period_end=period_end,
                segment="Streaming",
                geography=geography,
                defaults={
                    "period_start": date(period_end.year, ((period_end.month - 1) // 3) * 3 + 1, 1),
                    "fiscal_year": period_end.year,
                    "fiscal_period": fiscal_period,
                    "value": value,
                    "source_document": source,
                    "evidence_text": "Netflix 2022 Form 10-K paid membership table.",
                    "confidence_score": Decimal("0.95"),
                },
            )
        growth, _created = definition_model.objects.update_or_create(
            company=company,
            slug="paid-membership-qoq-growth",
            defaults={
                "name": "Paid membership quarter-over-quarter growth",
                "description": "Sequential percentage change in global paid streaming memberships.",
                "unit": "%",
                "cadence": "QUARTERLY",
                "value_type": "CALCULATED",
                "scope": "Global streaming",
                "aliases": ["subscriber growth"],
                "formula": "((current paid memberships / prior-quarter paid memberships) - 1) * 100",
                "peer_comparable": False,
            },
        )
        globals_only = [row for row in reported if not row[3]]
        for previous, current in zip(globals_only, globals_only[1:]):
            value = ((current[2] / previous[2]) - Decimal("1")) * Decimal("100")
            observation_model.objects.update_or_create(
                kpi=growth,
                period_end=current[0],
                segment="Streaming",
                geography="",
                defaults={
                    "period_start": date(current[0].year, ((current[0].month - 1) // 3) * 3 + 1, 1),
                    "fiscal_year": current[0].year,
                    "fiscal_period": current[1],
                    "value": value.quantize(Decimal("0.001")),
                    "source_document": source,
                    "evidence_text": "Calculated by InfoDJ from consecutive reported paid membership observations.",
                    "confidence_score": Decimal("0.95"),
                },
            )

    def _filter_model_values(self, model, values):
        return {key: value for key, value in values.items() if self._has_field(model, key)}

    def _has_field(self, model, field_name):
        try:
            model._meta.get_field(field_name)
        except Exception:
            return False
        return True

    def _coerce_aliases(self, model, aliases):
        field = model._meta.get_field("aliases")
        if field.get_internal_type() == "JSONField":
            return aliases
        return "\n".join(aliases)

    def _sha256(self, value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

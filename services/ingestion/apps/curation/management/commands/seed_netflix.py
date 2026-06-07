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

        with transaction.atomic():
            company = self._upsert_company(company_model)
            source = self._upsert_source(source_model, company) if source_model else None
            profile_source = self._upsert_source(source_model, company, values=SAMPLE_PROFILE_SOURCE) if source_model else None
            event = self._upsert_event(event_model, company, source) if event_model else None
            turn = self._upsert_turn(turn_model, company) if turn_model else None
            if turn_source_model and turn and source:
                self._upsert_turn_source(turn_source_model, turn, source, event)
            if profile_model and profile_source:
                self._upsert_profile(profile_model, company, profile_source)

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

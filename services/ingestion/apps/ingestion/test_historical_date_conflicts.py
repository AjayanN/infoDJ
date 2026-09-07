"""Historical date conflicts must survive importer replay."""
import json
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.companies.models import Company
from apps.curation.models import BusinessEvent, LifecycleEpisode
from apps.ingestion.services.dashboard_quality import event_eligibility, lifecycle_timing_eligibility


class HistoricalDateConflictTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Date Conflict Co", founded_date=date(2000, 1, 1),
            founded_date_precision="DAY", founded_date_evidence="Company charter.",
            founded_date_source_url="https://example.com/charter", founding_anchor_status="VERIFIED",
        )
        LifecycleEpisode.objects.create(
            company=self.company, scope="COMPANY", stage="LAUNCH",
            start_date=date(2001, 1, 1), start_date_precision="DAY",
            evidence_text="The company launched its first product in 2001.",
            source_url="https://example.com/launch", verification_status="VERIFIED",
        )
        self.row = {
            "company_slug": self.company.slug, "event_type": "PRODUCT_EXPANSION",
            "action_date": "2001-02-03", "episode_scope": "COMPANY",
            "episode_start_date": "2001-01-01", "source_url": "https://example.com/launch",
            "source_title": "First product launch", "evidence_text": "Product launched February 3, 2001.",
            "decision": "Launch the first product.", "actual_change": "The company launched its first product.",
        }
        self.conflicts = [
            {"action_date": "2001-02-03", "source_url": "https://example.com/launch",
             "evidence_text": "Source dates launch to February 3, 2001."},
            {"action_date": "2001-02-05", "source_url": "https://example.com/history",
             "evidence_text": "Company history dates launch to February 5, 2001."},
        ]

    def import_rows(self, rows):
        with patch("pathlib.Path.is_file", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(rows)
        ):
            call_command("import_historical_founder_events", input="review.json", stdout=StringIO())

    def test_dispute_is_preserved_on_omitted_or_empty_replay(self):
        self.import_rows([{**self.row, "date_conflicts": self.conflicts}])
        event = BusinessEvent.objects.get(company=self.company)
        event_id = event.pk
        for row in [self.row, {**self.row, "date_conflicts": []}]:
            self.import_rows([row])
            event.refresh_from_db()
            self.assertEqual(event.pk, event_id)
            self.assertEqual(event.review_status, "NEEDS_REVIEW")
            self.assertEqual(event.lifecycle_timing_status, "PENDING")
            self.assertEqual(event.lifecycle_context_json["date_conflicts"], self.conflicts)
            self.assertFalse(event_eligibility(event).eligible)
            self.assertFalse(lifecycle_timing_eligibility(event).eligible)
        self.assertEqual(BusinessEvent.objects.filter(company=self.company).count(), 1)
        profile = self.client.get(f"/companies/{self.company.slug}/profile").json()
        self.assertEqual(profile["highlights"]["historical_events"], [])

    def test_quality_gates_reject_conflict_even_with_stale_verified_status(self):
        self.import_rows([self.row])
        event = BusinessEvent.objects.get(company=self.company)
        event.lifecycle_context_json["date_conflicts"] = self.conflicts
        self.assertIn("conflicting_action_dates", event_eligibility(event).reasons)
        self.assertIn("conflicting_action_dates", lifecycle_timing_eligibility(event).reasons)

    def test_invalid_conflict_rolls_back_entire_batch(self):
        bad = {**self.row, "action_date": "2001-02-06", "date_conflicts": [{"action_date": "not-a-date"}]}
        with self.assertRaises(CommandError):
            self.import_rows([self.row, bad])
        self.assertFalse(BusinessEvent.objects.filter(company=self.company).exists())

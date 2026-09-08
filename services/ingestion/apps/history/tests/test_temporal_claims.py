from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.history.models import HistoricalClaim, Precision, ResearchSubject, SubjectKind


class TemporalClaimTests(TestCase):
    def setUp(self):
        self.subject = ResearchSubject.objects.create(kind=SubjectKind.PRODUCT, canonical_name="Temporal product")

    def claim(self, **kwargs):
        values = {"subject": self.subject, "track": "product", "claim_type": "launch", "event_kind": "launch", "statement": "Source says launch.", "value": {"fixture": True}}
        values.update(kwargs)
        return HistoricalClaim(**values)

    def test_day_month_year_range_and_unknown_preserve_uncertainty(self):
        self.claim(date_precision=Precision.DAY, date_min=date(2020, 1, 2), date_max=date(2020, 1, 2)).full_clean()
        self.claim(date_precision=Precision.MONTH, date_min=date(2020, 1, 1), date_max=date(2020, 1, 31)).full_clean()
        self.claim(date_precision=Precision.YEAR, date_min=date(2020, 1, 1), date_max=date(2020, 12, 31)).full_clean()
        self.claim(date_precision=Precision.RANGE, date_min=date(2020, 1, 1), date_max=date(2021, 1, 1)).full_clean()
        self.claim(date_precision=Precision.UNKNOWN).full_clean()

    def test_unknown_and_reversed_dates_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.claim(date_precision=Precision.UNKNOWN, date_min=date(2020, 1, 1)).full_clean()
        with self.assertRaises(ValidationError):
            self.claim(date_precision=Precision.RANGE, date_min=date(2021, 1, 1), date_max=date(2020, 1, 1)).full_clean()

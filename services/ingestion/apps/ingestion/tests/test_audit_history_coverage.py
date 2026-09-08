import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from apps.companies.models import Company


class AuditHistoryCoverageCommandTests(TestCase):
    def test_audits_every_company_without_mutating_data(self):
        first = Company.objects.create(name="Private company", slug="private-company")
        second = Company.objects.create(name="Public company", slug="public-company", sec_cik="0000000001")
        before = list(Company.objects.values_list("id", "name", "updated_at"))
        with TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "coverage.json"
            call_command("audit_history_coverage", output=str(output))
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(report["read_only"])
        self.assertEqual(report["company_count"], 2)
        self.assertEqual(report["company_ids"], [first.id, second.id])
        self.assertEqual(before, list(Company.objects.values_list("id", "name", "updated_at")))
        private_row = next(row for row in report["companies"] if row["company_id"] == first.id)
        self.assertIsNone(private_row["identifiers"]["sec_cik"])

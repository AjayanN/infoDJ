from datetime import datetime, timezone

from django.db import IntegrityError
from django.test import TestCase

from apps.companies.models import Company
from apps.history.models import SourceConnectorConfig
from apps.ingestion.models import EvidenceSpan, SourceDocument, SourceRevision


class SourceRevisionTests(TestCase):
    def test_connector_endpoint_must_match_allowlist(self):
        with self.assertRaises(Exception):
            SourceConnectorConfig.objects.create(connector_key="bad", schema_version="1", endpoint="https://evil.test/api", allowed_domain="example.test")
        SourceConnectorConfig.objects.create(connector_key="good", schema_version="1", endpoint="https://api.example.test/v1", allowed_domain="example.test")

    def test_same_document_changed_bytes_are_separate_revisions(self):
        company = Company.objects.create(name="Revision Co")
        source = SourceDocument.objects.create(company=company, source_api="test", url="https://example.test/source", title="Source")
        first = SourceRevision.objects.create(source_document=source, content_sha256="a" * 64, retrieved_at=datetime.now(timezone.utc), media_type="text/html", storage_key="revisions/a", parser_version="test")
        second = SourceRevision.objects.create(source_document=source, content_sha256="b" * 64, retrieved_at=datetime.now(timezone.utc), media_type="text/html", storage_key="revisions/b", parser_version="test")
        EvidenceSpan.objects.create(revision=first, locator="p1", excerpt="before", excerpt_sha256="c" * 64)
        self.assertEqual(SourceRevision.objects.filter(source_document=source).count(), 2)
        with self.assertRaises(IntegrityError):
            SourceRevision.objects.create(source_document=source, content_sha256="a" * 64, retrieved_at=datetime.now(timezone.utc), media_type="text/html", storage_key="revisions/a2", parser_version="test")

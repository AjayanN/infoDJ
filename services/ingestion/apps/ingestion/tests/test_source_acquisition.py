from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from django.test import TestCase

from apps.companies.models import Company
from apps.ingestion.models import SourceDocument, SourceRevision
from apps.ingestion.services.source_acquisition import AcquiredDocument, AcquisitionError, FilesystemBlobStore, fetch_authorized_document, persist_source_revision, validate_public_http_url


class SourceAcquisitionTests(TestCase):
    def setUp(self):
        company = Company.objects.create(name="P02 source company")
        self.source = SourceDocument.objects.create(company=company, source_api="test", url="https://example.test/source", title="Source")

    def test_changed_bytes_create_revisions_and_identical_replay_deduplicates(self):
        with TemporaryDirectory() as root:
            store = FilesystemBlobStore(root)
            first = AcquiredDocument("https://example.test/source", b"first", "text/plain", "first.txt", "", "")
            second = AcquiredDocument("https://example.test/source", b"second", "text/plain", "second.txt", "", "")
            first_revision, created = persist_source_revision(self.source, first, blob_store=store, revision_model=SourceRevision)
            replay, replay_created = persist_source_revision(self.source, first, blob_store=store, revision_model=SourceRevision)
            second_revision, second_created = persist_source_revision(self.source, second, blob_store=store, revision_model=SourceRevision)
            self.assertTrue(created)
            self.assertFalse(replay_created)
            self.assertTrue(second_created)
            self.assertEqual(first_revision.id, replay.id)
            self.assertNotEqual(first_revision.id, second_revision.id)
            self.assertEqual(store.read_bytes(first_revision.storage_key), b"first")

    def test_private_hosts_and_oversized_responses_are_rejected(self):
        with self.assertRaises(AcquisitionError):
            validate_public_http_url("http://127.0.0.1/internal")
        response = Mock()
        response.is_redirect = False
        response.headers = {"Content-Length": "999"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        with self.assertRaises(AcquisitionError):
            fetch_authorized_document("https://example.com/a", session=session, max_bytes=10)

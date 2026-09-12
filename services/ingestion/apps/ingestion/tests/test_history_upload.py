from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.companies.models import Company
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.source_acquisition import FilesystemBlobStore


class InternalHistoryUploadTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Upload target", slug="upload-target")

    @override_settings(INGESTION_INTERNAL_WRITE_TOKEN="test-writer-token")
    def test_internal_writer_rejects_missing_token_and_persists_tenant_scope(self):
        denied = self.client.post("/internal/history/documents", {})
        self.assertEqual(denied.status_code, 403)
        uploaded = SimpleUploadedFile("history.txt", b"private history evidence", content_type="text/plain")
        with TemporaryDirectory() as root, patch("apps.ingestion.api.FilesystemBlobStore", return_value=FilesystemBlobStore(root)):
            response = self.client.post("/internal/history/documents", {"file": uploaded, "company_slug": self.company.slug, "rights_scope": "licensed", "access_scope": "private", "tenant_key": "user:42"}, HTTP_X_INFODJ_INTERNAL_TOKEN="test-writer-token")
        self.assertEqual(response.status_code, 202)
        source = SourceDocument.objects.get(company=self.company, source_api="PRIVATE_UPLOAD")
        self.assertEqual(source.tenant_key, "user:42")
        self.assertEqual(source.access_scope, "private")

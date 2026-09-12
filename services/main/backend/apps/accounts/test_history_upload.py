from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import HistoryDocumentUpload


class BackendHistoryUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="uploader", password="StrongPass123!")
        token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    @override_settings(INGESTION_INTERNAL_WRITE_TOKEN="test-writer-token", INGESTION_API_URL="http://ingestion.test/api/ingestion")
    @patch("apps.accounts.api.requests.post")
    def test_authenticated_upload_forwards_only_to_internal_writer(self, post):
        response = Mock(status_code=202)
        response.json.return_value = {"job_id": 123, "status": "accepted"}
        post.return_value = response
        uploaded = SimpleUploadedFile("history.txt", b"private history", content_type="text/plain")
        result = self.client.post("/api/app/history/documents", {"file": uploaded, "company_slug": "target", "rights_scope": "licensed", "access_scope": "private"}, format="multipart")
        self.assertEqual(result.status_code, 202)
        record = HistoryDocumentUpload.objects.get(owner=self.user)
        self.assertEqual(record.ingestion_job_id, 123)
        self.assertEqual(record.status, "ACCEPTED")
        self.assertEqual(post.call_args.kwargs["headers"]["X-InfoDJ-Internal-Token"], "test-writer-token")

    def test_unauthenticated_upload_is_rejected(self):
        client = APIClient()
        result = client.post("/api/app/history/documents", {"company_slug": "target", "rights_scope": "licensed"}, format="multipart")
        self.assertEqual(result.status_code, 401)

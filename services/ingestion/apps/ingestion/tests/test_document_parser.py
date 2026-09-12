from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase

from apps.companies.models import Company
from apps.ingestion.models import ArticleExtraction, EvidenceSpan, SourceDocument, SourceRevision
from apps.ingestion.services.article_extractor import ArticleExtractor, extract_source_document
from apps.ingestion.services.document_parser import parse_document
from apps.ingestion.services.source_acquisition import AcquiredDocument, AcquisitionError, FilesystemBlobStore


class DocumentParserTests(TestCase):
    def text_pdf(self):
        from io import BytesIO
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 72 720 Td (PDF fixture text) Tj ET")
        font = writer._add_object(DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")}))
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()

    def test_html_text_and_unsupported_media_have_explicit_paths(self):
        html = parse_document(b"<html><body><h1>Title</h1><table><tr><td>Value</td></tr></table></body></html>", "text/html")
        plain = parse_document(b"hello\nworld", "text/plain")
        self.assertIn("Title", html.text)
        self.assertEqual(plain.spans[0][0], "char:0")
        with self.assertRaises(ValueError):
            parse_document(b"bytes", "application/zip")

    def test_text_pdf_has_page_locator_and_scanned_pdf_requires_ocr(self):
        parsed = parse_document(self.text_pdf(), "application/pdf")
        self.assertIn("PDF fixture text", parsed.text)
        self.assertEqual(parsed.spans[0][0], "page:1")
        from io import BytesIO
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        scanned = BytesIO()
        writer.write(scanned)
        with self.assertRaises(ValueError):
            parse_document(scanned.getvalue(), "application/pdf")

    def test_failed_retry_preserves_last_successful_legacy_text(self):
        company = Company.objects.create(name="P02 parser company")
        source = SourceDocument.objects.create(company=company, source_api="test", url="https://example.test/article", title="Article")
        existing = ArticleExtraction.objects.create(source_document=source, clean_text="last good text", word_count=3, extraction_status="SUCCEEDED", extractor_name="legacy")
        with TemporaryDirectory() as root, patch("apps.ingestion.services.article_extractor.fetch_authorized_document", side_effect=AcquisitionError("network down")):
            result = extract_source_document(source, article_extraction_model=ArticleExtraction, extractor=ArticleExtractor(), blob_store=FilesystemBlobStore(root))
        result.refresh_from_db()
        self.assertEqual(result.id, existing.id)
        self.assertEqual(result.clean_text, "last good text")
        self.assertEqual(result.extraction_status, "SUCCEEDED")
        self.assertIn("network down", result.extraction_error)

    def test_successful_pipeline_persists_original_parsed_bytes_and_spans(self):
        company = Company.objects.create(name="P02 persistence company")
        source = SourceDocument.objects.create(company=company, source_api="test", url="https://example.test/persist", title="Persist")
        acquired = AcquiredDocument("https://example.test/persist", b"<html><body>persistent evidence</body></html>", "text/html", "evidence.html", "etag", "")
        with TemporaryDirectory() as root, patch("apps.ingestion.services.article_extractor.fetch_authorized_document", return_value=acquired):
            store = FilesystemBlobStore(root)
            result = extract_source_document(source, article_extraction_model=ArticleExtraction, extractor=ArticleExtractor(), blob_store=store)
            revision = SourceRevision.objects.get(source_document=source)
            recreated_store = FilesystemBlobStore(root)
            self.assertEqual(recreated_store.read_bytes(revision.storage_key), acquired.content)
            self.assertIn("persistent evidence", recreated_store.read_bytes(revision.parsed_storage_key).decode())
        self.assertEqual(result.extraction_status, "SUCCEEDED")
        self.assertEqual(EvidenceSpan.objects.filter(revision=revision).count(), 1)

from datetime import datetime, timezone

from django.db import IntegrityError
from django.test import TestCase

from apps.companies.models import Company
from apps.history.models import ClaimEvidence, ClaimReview, EvidenceRole, HistoricalClaim, ResearchSubject, ReviewState, SubjectKind
from apps.ingestion.models import EvidenceSpan, SourceDocument, SourceRevision


class ClaimReviewTests(TestCase):
    def test_conflicting_evidence_and_review_journal_are_preserved(self):
        company = Company.objects.create(name="Conflict Co")
        subject = ResearchSubject.objects.create(kind=SubjectKind.COMPANY, company=company, canonical_name=company.name)
        source = SourceDocument.objects.create(company=company, source_api="test", url="https://example.test/conflict", title="Conflict source")
        revision = SourceRevision.objects.create(source_document=source, content_sha256="d" * 64, retrieved_at=datetime.now(timezone.utc), media_type="text/html", storage_key="revisions/d", parser_version="test")
        first_span = EvidenceSpan.objects.create(revision=revision, locator="one", excerpt="1903", excerpt_sha256="e" * 64)
        second_span = EvidenceSpan.objects.create(revision=revision, locator="two", excerpt="1904", excerpt_sha256="f" * 64)
        claim = HistoricalClaim.objects.create(subject=subject, track="company", claim_type="founding", event_kind="founding", statement="Competing dates retained", value={"fixture": True}, review_state=ReviewState.CONFLICTED)
        ClaimEvidence.objects.create(claim=claim, evidence_span=first_span, role=EvidenceRole.SUPPORTS, source_family="archive")
        ClaimEvidence.objects.create(claim=claim, evidence_span=second_span, role=EvidenceRole.CONTRADICTS, source_family="press")
        ClaimReview.objects.create(claim=claim, decision=ReviewState.CONFLICTED, reviewer="staff-1", rationale="retain both", conflict_group="ford-date")
        ClaimReview.objects.create(claim=claim, decision=ReviewState.PENDING, reviewer="staff-2", rationale="needs resolution", conflict_group="ford-date")
        self.assertEqual(claim.evidence_links.count(), 2)
        self.assertEqual(claim.review_journal.count(), 2)
        with self.assertRaises(IntegrityError):
            ClaimEvidence.objects.create(claim=claim, evidence_span=first_span, role=EvidenceRole.SUPPORTS, source_family="archive")

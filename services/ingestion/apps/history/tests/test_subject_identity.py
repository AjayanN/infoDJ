from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.companies.models import Company
from apps.history.models import ResearchSubject, SubjectAlias, SubjectIdentifier, SubjectKind, SubjectRelation


class SubjectIdentityTests(TestCase):
    def test_company_identity_and_product_lineage_are_distinct(self):
        company = Company.objects.create(name="Acme Holdings")
        company_subject = ResearchSubject.objects.create(kind=SubjectKind.COMPANY, company=company, canonical_name=company.name)
        product = ResearchSubject.objects.create(kind=SubjectKind.PRODUCT, parent_subject=company_subject, canonical_name="Acme One")
        successor = ResearchSubject.objects.create(kind=SubjectKind.PRODUCT, parent_subject=company_subject, canonical_name="Acme Two")
        relation = SubjectRelation.objects.create(subject=successor, related_subject=product, relation_type="version_of")
        self.assertEqual(product.parent_subject_id, company_subject.id)
        self.assertEqual(relation.related_subject_id, product.id)
        self.assertNotEqual(product.id, company_subject.id)

    def test_company_subject_mapping_and_identifier_are_constrained(self):
        company = Company.objects.create(name="Identity Co")
        invalid = ResearchSubject(kind=SubjectKind.PRODUCT, company=company, canonical_name="not valid")
        with self.assertRaises(ValidationError):
            invalid.full_clean()
        subject = ResearchSubject.objects.create(kind=SubjectKind.COMPANY, company=company, canonical_name=company.name)
        SubjectIdentifier.objects.create(subject=subject, namespace="wikidata", external_id="Q1")
        with self.assertRaises(IntegrityError):
            SubjectIdentifier.objects.create(subject=subject, namespace="wikidata", external_id="Q1")

    def test_alias_is_not_global_identity(self):
        first = ResearchSubject.objects.create(kind=SubjectKind.PRODUCT, canonical_name="Alpha")
        second = ResearchSubject.objects.create(kind=SubjectKind.PRODUCT, canonical_name="Beta")
        SubjectAlias.objects.create(subject=first, alias="Common", language="en")
        SubjectAlias.objects.create(subject=second, alias="Common", language="en")
        self.assertEqual(SubjectAlias.objects.filter(alias="Common").count(), 2)

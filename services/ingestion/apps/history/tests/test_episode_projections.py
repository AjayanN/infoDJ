from django.test import TestCase
from apps.companies.models import Company
from apps.history.models import HistoricalClaim, ResearchSubject, ReviewState, SubjectKind
from apps.history.services.episode_builder import build_episode_skeletons
from apps.history.services.projections import projection_rows
from apps.ingestion.services.dashboard_quality import historical_claim_eligibility
from types import SimpleNamespace

class EpisodeProjectionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Apple Fixture")
        self.subject = ResearchSubject.objects.create(kind=SubjectKind.COMPANY, company=self.company, canonical_name=self.company.name)
    def claim(self, **kwargs):
        values={"subject":self.subject,"track":"product","claim_type":"documented_action","event_kind":"release","statement":"Released product","value":{"scope":"product","phase":"validation"},"review_state":ReviewState.REVIEWED}
        values.update(kwargs); return HistoricalClaim.objects.create(**values)
    def test_company_incorporation_does_not_become_product_validation(self):
        incorporation=self.claim(track="operations_finance", claim_type="documented_action", event_kind="incorporation", statement="Apple incorporated", value={"scope":"company","phase":"formation"})
        launch=self.claim()
        rows=build_episode_skeletons([incorporation, launch])
        self.assertEqual(len(rows),2)
        product=next(row for row in rows if row.scope=="product")
        self.assertEqual(product.claim_ids,(str(launch.id),))
    def test_multi_topic_claims_are_distinct_tracks_and_projections_replay(self):
        price=self.claim(track="pricing", event_kind="price", statement="Plan costs $20", value={"kind":"money","amount":"20","currency":"USD","unit":"month","geography":"US","terms":{"billing_period":"month","tax_included":None,"shipping_included":None,"promotional":False},"scope":"product","phase":"launch"})
        product=self.claim(track="product", statement="Available online")
        first=projection_rows([price, product]); second=projection_rows([price, product])
        self.assertEqual(first,second)
        self.assertEqual({row["projection"] for row in first},{"price","product"})
    def test_conflicted_price_is_not_projected(self):
        claim=self.claim(track="pricing", value={"kind":"money","amount":"20","currency":"USD","unit":"month"}, review_state=ReviewState.CONFLICTED)
        self.assertEqual(projection_rows([claim]),[])
    def test_dashboard_claim_bridge_keeps_conflicts_held(self):
        links = SimpleNamespace(filter=lambda **kwargs: SimpleNamespace(exists=lambda: True))
        claim = SimpleNamespace(review_state="CONFLICTED", evidence_links=links, date_precision="DAY", date_min=None, date_max=None)
        result = historical_claim_eligibility(claim)
        self.assertFalse(result.eligible)
        self.assertIn("date_conflicts", result.reasons)

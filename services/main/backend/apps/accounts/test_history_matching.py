from django.test import SimpleTestCase
from apps.accounts.history_matching import rank_history_cases
class HistoryMatchingTests(SimpleTestCase):
 def test_objective_changes_rank_and_business_type_gate(self):
  cases=[{"id":"a","claim_type":"documented_action","source_families":["official","sec"],"scope":"product","sector":"tech","business_type":"saas","objective":"retention"},{"id":"b","claim_type":"documented_action","source_families":["official"],"scope":"product","sector":"tech","business_type":"saas","objective":"acquisition"}]
  r=rank_history_cases({"scope":"product","sector":"tech","business_type":"saas","objective":"retention"},cases); self.assertEqual(r["cases"][0]["id"],"a")
  r=rank_history_cases({"scope":"product","sector":"tech","business_type":"marketplace","objective":"retention"},cases); self.assertEqual(r["semantics"],"insufficient")
 def test_company_is_not_product_and_single_case_is_honest(self):
  r=rank_history_cases({"scope":"product"},[{"id":"c","claim_type":"documented_action","source_families":["official"],"scope":"company"}]); self.assertEqual(r["semantics"],"insufficient")
  r=rank_history_cases({},[{"id":"c","claim_type":"documented_action","source_families":["official"],"scope":"company"}]); self.assertEqual(r["semantics"],"case_study")
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.api import ensure_profile, serialize_founder_context
class FounderContextApiTests(TestCase):
 def test_legacy_profile_serializes_optional_context_as_empty(self):
  user=get_user_model().objects.create_user(username="legacy",password="x")
  context=serialize_founder_context(ensure_profile(user))
  self.assertEqual(context["scope"],"")
  self.assertEqual(context["product_phase"],"")
  self.assertEqual(context["capital_band"],"")
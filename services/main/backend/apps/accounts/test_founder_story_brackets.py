from django.test import SimpleTestCase

from apps.accounts.founder_story_brackets import build_story_brackets


def event(*, company="Netflix", slug="netflix", sector="Communication Services", conflict=False):
    return {
        "id": 1, "company": company, "company_slug": slug, "event_date": "1998-04-14",
        "event_type": "DISTRIBUTION_CHANNEL_SHIFT", "decision_theme": "ONLINE_RENTAL_LAUNCH",
        "actual_change": "Netflix opened an online DVD rental store.",
        "trigger": "Customers needed broader DVD access.", "before_state": "A company preparing an online rental service.",
        "outcome": "The workflow was publicly available.",
        "source": {"title": "Netflix release", "url": "https://example.test/netflix"},
        "quality": {"eligible": not conflict},
        "lifecycle_timing": {"eligible": not conflict, "action_date": "1998-04-14", "action_date_precision": "DAY"},
        "_sector": sector,
    }


class FounderStoryBracketTests(SimpleTestCase):
    def test_bracket_keeps_documented_fact_question_and_citation_separate(self):
        row = event()
        payload = build_story_brackets(
            [{"slug": "netflix", "sector": "Communication Services"}],
            {"historical_events": [row]},
            "Communication Services",
        )
        self.assertEqual(payload["status"], "available")
        bracket = payload["brackets"][0]
        self.assertEqual(bracket["documented_action"], row["actual_change"])
        self.assertEqual(bracket["source"]["url"], "https://example.test/netflix")
        self.assertIn("What customer problem", bracket["question"])
        self.assertIn("not proof", bracket["evidence_note"])

    def test_conflicted_or_ineligible_event_does_not_become_a_bracket(self):
        payload = build_story_brackets(
            [{"slug": "netflix", "sector": "Communication Services"}],
            {"historical_events": [event(conflict=True)]},
            "Communication Services",
        )
        self.assertEqual(payload["status"], "insufficient_evidence")
        self.assertEqual(payload["brackets"], [])
        self.assertEqual(payload["source_gaps"][0]["key"], "founder_story_brackets")

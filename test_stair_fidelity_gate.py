import unittest

from stair_fidelity_gate import triage_candidate, triage_candidates
from stair_rule_extractor import validate_candidates, observe_extraction


SOURCE = [{
    "id": "S001",
    "text": "If the hero is poisoned, check the healing condition. However, the effect may not apply during the last turn.",
    "page": 7,
    "source_refs": ["#/texts/40"],
}]
PROPOSAL = {
    "rules": [{
        "id": "r1",
        "if": ["hero_poisoned"],
        "then": "check_healing",
        "evidence_id": "S001",
        "quote": "If the hero is poisoned",
    }]
}


def candidate():
    return validate_candidates(PROPOSAL, SOURCE)["candidates"][0]


class FidelityGateTests(unittest.TestCase):
    def test_candidate_is_never_verified(self):
        result = triage_candidate(candidate(), SOURCE[0])
        self.assertEqual(result["status"], "needs_review")
        self.assertFalse(result["semantically_verified"])
        self.assertIn("entailment_not_proven", result["issues"])

    def test_surrounding_exception_detected(self):
        issues = triage_candidate(candidate(), SOURCE[0])["issues"]
        self.assertIn("exception_or_override", issues)
        self.assertIn("scope_or_time", issues)
        self.assertIn("partial_quote_context", issues)

    def test_tampered_page_is_blocked(self):
        item = candidate()
        item["provenance"]["page"] = 99
        self.assertEqual(triage_candidate(item, SOURCE[0])["status"], "blocked")

    def test_tampered_source_refs_blocked(self):
        item = candidate()
        item["provenance"]["source_refs"] = ["#/texts/999"]
        self.assertEqual(triage_candidate(item, SOURCE[0])["status"], "blocked")

    def test_wrong_evidence_id_blocked(self):
        item = candidate()
        item["source"] = "S404"
        self.assertEqual(triage_candidate(item, SOURCE[0])["status"], "blocked")

    def test_fake_quote_blocked(self):
        item = candidate()
        item["quote"] = "A different invented passage"
        self.assertEqual(triage_candidate(item, SOURCE[0])["status"], "blocked")

    def test_no_source_is_blocked(self):
        self.assertEqual(triage_candidate(candidate(), None)["status"], "blocked")

    def test_batch_unverified(self):
        result = triage_candidates([candidate()], SOURCE)
        self.assertEqual(result["needs_review_count"], 1)
        self.assertFalse(result["semantically_verified"])

    def test_observation_returns_counts_not_content(self):
        result = observe_extraction(
            SOURCE, extraction_enabled=True, generator=lambda messages: PROPOSAL
        )
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["needs_review_count"], 1)
        self.assertFalse(result["semantically_verified"])
        self.assertNotIn("reviews", result)
        self.assertNotIn("candidates", result)

    def test_empty_input_batch(self):
        result = triage_candidates([], SOURCE)
        self.assertEqual(result["candidate_count"], 0)
        self.assertFalse(result["semantically_verified"])


if __name__ == "__main__":
    unittest.main()

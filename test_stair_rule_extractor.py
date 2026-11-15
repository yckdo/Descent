import unittest
from stair_rule_extractor import validate_candidates, propose_candidates, observe_extraction

EVIDENCE = [{"id": "S001", "text": "If the hero is poisoned, check the healing condition.",
             "page": 7, "source_refs": ["#/texts/40"]}]
GOOD = {"rules": [{"id": "r1", "if": ["hero_poisoned"],
                    "then": "check_healing", "evidence_id": "S001",
                    "quote": "If the hero is poisoned"}]}


class ExtractorTests(unittest.TestCase):
    def test_good_candidate_is_only_proposed(self):
        result = validate_candidates(GOOD, EVIDENCE)
        self.assertEqual(result["candidate_count"], 1)
        self.assertFalse(result["semantically_verified"])
        self.assertEqual(result["candidates"][0]["review_status"], "proposed")
        self.assertEqual(result["candidates"][0]["provenance"]["page"], 7)

    def test_reject_fake_source(self):
        bad = {"rules": [dict(GOOD["rules"][0], evidence_id="S999")]}
        self.assertEqual(validate_candidates(bad, EVIDENCE)["candidate_count"], 0)

    def test_reject_fake_quote(self):
        bad = {"rules": [dict(GOOD["rules"][0], quote="This is a fabricated quote")]}
        self.assertEqual(validate_candidates(bad, EVIDENCE)["candidate_count"], 0)

    def test_reject_invalid_atom(self):
        bad = {"rules": [dict(GOOD["rules"][0], then="anything;import os")]}
        self.assertEqual(validate_candidates(bad, EVIDENCE)["candidate_count"], 0)

    def test_reject_missing_provenance(self):
        no_ref = [dict(EVIDENCE[0], source_refs=[])]
        self.assertEqual(validate_candidates(GOOD, no_ref)["candidate_count"], 0)

    def test_reject_duplicate_id(self):
        bad = {"rules": [GOOD["rules"][0], GOOD["rules"][0]]}
        self.assertEqual(validate_candidates(bad, EVIDENCE)["candidate_count"], 1)

    def test_generator_is_injected(self):
        self.assertEqual(propose_candidates(EVIDENCE, generator=lambda messages: GOOD)["candidate_count"], 1)

    def test_disabled_no_generator_invocation(self):
        def fail(messages):
            raise AssertionError("should never run")
        self.assertEqual(observe_extraction(EVIDENCE, extraction_enabled=False, generator=fail)["status"], "disabled")

    def test_enabled_only_reports_counts(self):
        result = observe_extraction(EVIDENCE, extraction_enabled=True,
                                    generator=lambda messages: GOOD)
        self.assertEqual(result["candidate_count"], 1)
        self.assertNotIn("candidates", result)
        self.assertFalse(result["semantically_verified"])

    def test_failed_model_is_nonfatal(self):
        def fail(messages):
            raise RuntimeError("offline")
        self.assertEqual(observe_extraction(EVIDENCE, extraction_enabled=True,
                                            generator=fail)["status"], "error")

    def test_empty_evidence(self):
        self.assertEqual(propose_candidates([], generator=lambda _: GOOD)["status"], "no_evidence")

    def test_nonlist_payload(self):
        with self.assertRaises(ValueError):
            validate_candidates({"rules": {}}, EVIDENCE)


if __name__ == "__main__":
    unittest.main()

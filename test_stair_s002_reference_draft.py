"""Synthetic-only regression tests for provisional S002 reference construction."""
import hashlib
import unittest

from stair_s002_reference_draft import provisional_reference
from stair_s002_semantic_review import compare_s002


TEXT = "synthetic movement paragraph (not a manual passage)"


def fixture():
    sha = hashlib.sha256(TEXT.encode()).hexdigest()
    return {
        "case_id": "descent_sec_0047",
        "evidence": [{"id": "S002", "page": 8, "source_refs": ["#/texts/263"], "text": TEXT}],
        "evidence_hashes": {"S002": sha},
    }


def candidate(row):
    return dict(row, source="S002")


class ReferenceDraftTests(unittest.TestCase):
    def test_reference_is_provisional_and_private_text_absent(self):
        ref = provisional_reference(fixture())
        self.assertEqual(ref["annotation_status"], "synthetic_reference")
        self.assertEqual(len(ref["expected_actions"]), 10)
        self.assertNotIn(TEXT, str(ref))

    def test_full_matching_fixture_still_not_semantic_approval(self):
        ref = provisional_reference(fixture())
        result = compare_s002({"scenario": "S002",
                               "actions": [candidate(r) for r in ref["expected_actions"]]},
                              ref, ref["evidence_sha256"])
        self.assertTrue(result["exact_descriptor_agreement"])
        self.assertFalse(result["semantically_verified"])

    def test_missing_general_no_passage_is_detected(self):
        ref = provisional_reference(fixture())
        subset = [r for r in ref["expected_actions"]
                  if r["conclusion"] != "!figure_can_move_through_blocked_space"]
        result = compare_s002({"scenario": "S002", "actions": [candidate(r) for r in subset]},
                              ref, ref["evidence_sha256"])
        self.assertEqual(result["missing_reference_actions"], 1)

    def test_missing_diagonal_examples_detected(self):
        ref = provisional_reference(fixture())
        subset = [r for r in ref["expected_actions"]
                  if r["target"] not in ("around_corner", "between_blocked_spaces")]
        result = compare_s002({"scenario": "S002", "actions": [candidate(r) for r in subset]},
                              ref, ref["evidence_sha256"])
        self.assertEqual(result["missing_reference_actions"], 2)

    def test_fingerprint_mismatch_fails(self):
        data = fixture()
        data["evidence_hashes"]["S002"] = "0" * 64
        with self.assertRaises(ValueError):
            provisional_reference(data)

    def test_wrong_source_reference_fails(self):
        data = fixture()
        data["evidence"][0]["source_refs"] = []
        with self.assertRaises(ValueError):
            provisional_reference(data)


if __name__ == "__main__":
    unittest.main()

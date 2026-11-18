"""Synthetic tests: reference agreement is not approval of real Descent rules."""
import unittest
from stair_s002_semantic_review import compare_s002

HASH = "a" * 64


def row(**changes):
    record = dict(source="S002", action="pass_through", actor="figure",
                  target="friendly_figure", polarity="positive",
                  conditions=["figure", "space_contains_friendly_figure"],
                  conclusion="figure_can_move_through_friendly_figure")
    record.update(changes)
    return record


def gold(**changes):
    record = dict(case_id="descent_sec_0047", source_id="S002",
                  evidence_sha256=HASH, annotation_status="synthetic_reference",
                  expected_actions=[row()])
    record.update(changes)
    return record


def candidates(actions=None):
    return {"scenario": "S002", "actions": [row()] if actions is None else actions}


class ScopeReviewTests(unittest.TestCase):
    def test_exact_fixture_does_not_approve(self):
        r = compare_s002(candidates(), gold(), HASH)
        self.assertTrue(r["exact_descriptor_agreement"])
        self.assertFalse(r["automatic_approval"])
        self.assertFalse(r["semantically_verified"])

    def test_traversal_not_equivalent_to_finishing(self):
        last = row(action="end_movement", target="occupied_space",
                   polarity="negative", conclusion="!figure_can_end_movement_in_same_space")
        r = compare_s002(candidates([last]), gold(), HASH)
        self.assertEqual((r["unexpected_candidates"], r["missing_reference_actions"]), (1, 1))

    def test_target_mismatch(self):
        self.assertFalse(compare_s002(candidates([row(target="enemy_figure")]),
                                      gold(), HASH)["exact_descriptor_agreement"])

    def test_conditions_mismatch(self):
        self.assertFalse(compare_s002(candidates([row(conditions=["figure"])]),
                                      gold(), HASH)["exact_descriptor_agreement"])

    def test_polarity_mismatch(self):
        negative = row(polarity="negative", conclusion="!figure_can_move_through_friendly_figure")
        self.assertEqual(compare_s002(candidates([negative]), gold(), HASH)["exact_field_matches"], 0)

    def test_missing_candidate(self):
        self.assertEqual(compare_s002(candidates([]), gold(), HASH)["missing_reference_actions"], 1)

    def test_source_hash_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            compare_s002(candidates(), gold(), "b" * 64)

    def test_bad_polarity_rejected(self):
        with self.assertRaises(ValueError):
            compare_s002(candidates([row(polarity="negative")]), gold(), HASH)

    def test_human_review_metadata_not_proof(self):
        r = compare_s002(candidates(), gold(annotation_status="human_reviewed",
                                            reviewer="reviewer-A"), HASH)
        self.assertTrue(r["reference_metadata_claims_human_review"])
        self.assertFalse(r["semantically_verified"])

    def test_wrong_case_rejected(self):
        with self.assertRaises(ValueError):
            compare_s002(candidates(), gold(case_id="other"), HASH)

    def test_duplicate_candidate_counts_as_extra(self):
        self.assertEqual(compare_s002(candidates([row(), row()]), gold(), HASH)
                         ["unexpected_candidates"], 1)


if __name__ == "__main__":
    unittest.main()

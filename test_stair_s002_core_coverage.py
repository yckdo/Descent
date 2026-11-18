"""Tests for conservative distinction between S002 core rules and examples."""
import unittest

from stair_s002_core_coverage import audit_coverage
from test_stair_s002_reference_draft import fixture, candidate
from stair_s002_reference_draft import provisional_reference


def gold():
    return provisional_reference(fixture())


def report(rows):
    return audit_coverage({"scenario": "S002", "actions": [candidate(x) for x in rows]}, gold())


class CoreCoverageTests(unittest.TestCase):
    def test_full_reference_has_eight_core_and_two_examples(self):
        ref = gold()
        r = report(ref["expected_actions"])
        self.assertEqual(r["core_expected"], 8)
        self.assertEqual(r["core_missing"], 0)
        self.assertEqual(len(r["diagonal_scope_examples"]), 2)
        self.assertFalse(r["semantically_verified"])

    def test_missing_examples_are_not_core_omissions(self):
        rows = [x for x in gold()["expected_actions"]
                if x["target"] not in ("around_corner", "between_blocked_spaces")]
        r = report(rows)
        self.assertEqual(r["core_missing"], 0)
        self.assertEqual(r["core_unexpected"], 0)
        self.assertTrue(all(x["base_action_present"] for x in r["diagonal_scope_examples"]))
        self.assertTrue(all(not x["detail_explicitly_represented"] for x in r["diagonal_scope_examples"]))

    def test_general_traversal_omission_is_core(self):
        rows = [x for x in gold()["expected_actions"]
                if x["conclusion"] != "!figure_can_move_through_blocked_space"]
        r = report(rows)
        self.assertEqual(r["core_missing"], 1)
        self.assertFalse(r["general_traversal_prohibition_present"])
        self.assertTrue(r["friendly_pass_permission_present"])

    def test_no_priority_inferred(self):
        r = report(gold()["expected_actions"])
        self.assertEqual(r["exception_relation"], "requires_human_review")
        self.assertFalse(r["automatic_approval"])

    def test_invalid_source_fails_closed(self):
        item = candidate(gold()["expected_actions"][0])
        item["source"] = "S999"
        with self.assertRaises(ValueError):
            audit_coverage({"scenario": "S002", "actions": [item]}, gold())


if __name__ == "__main__":
    unittest.main()

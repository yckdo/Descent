"""Conservative S002 alias normalization: synthetic-only tests."""
import copy
import unittest

from stair_s002_vocabulary_audit import normalize_s002
from stair_s002_reference_draft import provisional_reference
from test_stair_s002_reference_draft import fixture, candidate


def gold():
    return provisional_reference(fixture())


def classified(rows):
    return {"scenario": "S002", "actions": rows}


class VocabularyAuditTests(unittest.TestCase):
    def test_guarded_occupancy_alias_improves_exact_match(self):
        row = candidate(gold()["expected_actions"][0])
        row["conditions"] = ["figure", "space_occupied_by_figure_or_obstacle"]
        original = copy.deepcopy(row)
        result = normalize_s002(classified([row]), gold())
        self.assertEqual(result["before"]["core_exact_matches"], 0)
        self.assertEqual(result["after"]["core_exact_matches"], 1)
        self.assertEqual(len(result["safe_alias_changes"]), 1)
        self.assertEqual(row, original)
        self.assertFalse(result["semantically_verified"])

    def test_friendly_figure_not_equated_with_occupied_space(self):
        row = candidate(next(x for x in gold()["expected_actions"]
                             if x["conclusion"] == "figure_can_move_through_friendly_figure"))
        row["conditions"] = ["figure", "friendly_figure"]
        result = normalize_s002(classified([row]), gold())
        self.assertEqual(result["after"]["core_exact_matches"], 0)
        self.assertTrue(any(x["atom"] == "friendly_figure"
                            for x in result["unresolved_ambiguities"]))
        self.assertFalse(result["automatic_approval"])

    def test_finishing_condition_needs_review(self):
        row = candidate(next(x for x in gold()["expected_actions"]
                             if x["action"] == "end_movement"))
        row["conditions"] = ["figure", "same_space_as_another_figure"]
        result = normalize_s002(classified([row]), gold())
        self.assertEqual(result["after"]["core_exact_matches"], 0)
        self.assertEqual(len(result["unresolved_ambiguities"]), 1)

    def test_nominal_blocked_label_not_equivalent(self):
        row = candidate(next(x for x in gold()["expected_actions"]
                             if x["action"] == "occupancy_label"))
        row["conclusion"] = "blocked_space"
        result = normalize_s002(classified([row]), gold())
        self.assertEqual(result["after"]["core_exact_matches"], 0)
        self.assertTrue(any(x["field"] == "conclusion"
                            for x in result["unresolved_ambiguities"]))

    def test_missing_general_traversal_not_created(self):
        rows = [candidate(x) for x in gold()["expected_actions"]
                if x["conclusion"] != "!figure_can_move_through_blocked_space"
                and x["target"] not in ("around_corner", "between_blocked_spaces")]
        result = normalize_s002(classified(rows), gold())
        self.assertFalse(result["general_traversal_prohibition_present"])
        self.assertTrue(any(x["conclusion"] == "!figure_can_move_through_blocked_space"
                            for x in result["missing_core_actions"]))

    def test_distinct_actions_not_rewritten(self):
        row = candidate(gold()["expected_actions"][0])
        row["action"] = "pass_through"
        result = normalize_s002(classified([row]), gold())
        self.assertEqual(result["after"]["core_exact_matches"], 0)

    def test_collision_does_not_overwrite_conditions(self):
        row = candidate(gold()["expected_actions"][0])
        row["conditions"] = ["space_occupied_by_figure_or_obstacle",
                             "space_contains_figure_or_obstacle"]
        result = normalize_s002(classified([row]), gold())
        self.assertEqual(result["safe_alias_changes"], [])
        self.assertTrue(any(x.get("reason") == "alias_collision"
                            for x in result["unresolved_ambiguities"]))

    def test_wrong_source_rejected(self):
        row = candidate(gold()["expected_actions"][0])
        row["source"] = "other"
        with self.assertRaises(ValueError):
            normalize_s002(classified([row]), gold())


if __name__ == "__main__":
    unittest.main()

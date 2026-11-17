"""Synthetic-only tests for provisional S002 movement scope descriptors."""
import unittest

from stair_movement_scope import classify_movement


def rule(premises, conclusion):
    return {"if": premises, "then": conclusion, "source": "S002"}


class MovementScopeTests(unittest.TestCase):
    def test_entry_pass_end_are_distinct(self):
        rows = [
            rule(["figure", "space_contains_figure_or_obstacle"], "!figure_can_move_into_space"),
            rule(["figure", "space_contains_friendly_figure"], "figure_can_move_through_friendly_figure"),
            rule(["figure", "figure_ends_movement_in_same_space_as_another_figure"],
                 "!figure_can_end_movement_in_same_space"),
        ]
        result = classify_movement(rows)
        self.assertEqual([r["action"] for r in result["actions"]],
                         ["enter_space", "pass_through", "end_movement"])
        self.assertTrue(all(result["distinctions_present"].values()))
        self.assertEqual([r["polarity"] for r in result["actions"]],
                         ["negative", "positive", "negative"])
        self.assertFalse(result["semantically_verified"])
        self.assertFalse(result["automatic_approval"])

    def test_conditions_untouched_except_order(self):
        result = classify_movement([rule(["z_condition", "a_condition"],
                                         "figure_can_move_through_friendly_figure")])
        self.assertEqual(result["actions"][0]["conditions"], ["a_condition", "z_condition"])
        self.assertFalse(result["actions"][0]["scope_verified"])

    def test_unknown_atom_is_not_guessed(self):
        result = classify_movement([rule(["figure"], "hero_teleports")])
        item = result["actions"][0]
        self.assertEqual((item["action"], item["actor"], item["target"]),
                         ("unknown", "unknown", "unknown"))
        self.assertEqual(item["classification"], "unclassified")

    def test_bad_source_rejected(self):
        with self.assertRaises(ValueError):
            classify_movement([{"if": ["figure"], "then": "allowed", "source": "S999"}])

    def test_no_semantic_inference_from_blocked(self):
        result = classify_movement([rule(["space_contains_figure_or_obstacle"], "space_is_blocked")])
        self.assertEqual(result["actions"][0]["action"], "occupancy_label")
        self.assertFalse(any(result["distinctions_present"].values()))


if __name__ == "__main__":
    unittest.main()

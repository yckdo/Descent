"""Regression tests for the read-only S002 scope audit (synthetic atoms only)."""
import unittest

from stair_s002_scope_audit import audit_s002, _validate


def rule(premises, conclusion):
    return {"if": premises, "then": conclusion, "source": "S002"}


class S002ScopeAuditTests(unittest.TestCase):
    def test_valid_atoms_are_accepted(self):
        rows = _validate([rule(["figure", "space_contains_friendly_figure"],
                               "figure_can_move_through_friendly_figure")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["then"], "figure_can_move_through_friendly_figure")

    def test_invalid_atoms_are_rejected(self):
        for atom in ("bad atom", "A_uppercase", "ok\\n", "", "x" * 82):
            with self.subTest(atom=atom):
                with self.assertRaises(ValueError):
                    _validate([rule(["figure"], atom)])

    def test_wrong_source_is_rejected(self):
        with self.assertRaises(ValueError):
            _validate([{"if": ["figure"], "then": "allowed", "source": "S999"}])

    def test_direct_opposites_are_flagged_as_potential(self):
        data = audit_s002([rule(["hero"], "allowed"), rule(["hero"], "!allowed")])
        self.assertIn("potential_direct_conflict", [issue["code"] for issue in data["issues"]])
        self.assertFalse(data["semantically_verified"])
        self.assertFalse(data["automatic_approval"])

    def test_disjoint_explicit_premises_not_flagged_directly(self):
        data = audit_s002([rule(["hero"], "allowed"), rule(["!hero"], "!allowed")])
        self.assertNotIn("potential_direct_conflict", [issue["code"] for issue in data["issues"]])

    def test_s002_entry_and_passage_scope_are_not_asserted_contradictory(self):
        rows = [
            rule(["figure", "space_contains_figure_or_obstacle"], "!figure_can_move_into_space"),
            rule(["space_contains_figure_or_obstacle"], "space_is_blocked"),
            rule(["figure", "space_contains_friendly_figure"], "figure_can_move_through_friendly_figure"),
            rule(["figure", "figure_ends_movement_in_same_space_as_another_figure"],
                 "!figure_can_end_movement_in_same_space"),
        ]
        data = audit_s002(rows)
        codes = {issue["code"] for issue in data["issues"]}
        self.assertIn("entry_vs_friendly_pass_scope_review", codes)
        self.assertIn("blocked_space_meaning_ambiguous", codes)
        self.assertNotIn("potential_direct_conflict", codes)
        self.assertEqual(data["missing_required_actions"], [])
        self.assertEqual(data["status"], "review_required")
        self.assertFalse(data["semantically_verified"])


if __name__ == "__main__":
    unittest.main()

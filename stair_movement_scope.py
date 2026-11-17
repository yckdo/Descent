"""Conservative, read-only movement-action classification for provisional S002 atoms.

This is a diagnostic vocabulary, NOT a semantic verifier or a rule engine.
Only exact known conclusion atoms are classified; conditions remain unverified.
"""
from __future__ import annotations

from stair_s002_scope_audit import _validate

# These mappings describe the *names* of candidate atoms, not official game rules.
KNOWN = {
    "figure_can_move_into_space": ("enter_space", "figure", "occupied_or_obstacle_space"),
    "figure_can_move_through_friendly_figure": ("pass_through", "figure", "friendly_figure"),
    "figure_can_end_movement_in_same_space": ("end_movement", "figure", "occupied_space"),
    "figure_can_move_diagonally": ("move_diagonally", "figure", "diagonal_space"),
    "hero_treats_all_other_heroes_as_friendly": ("classify_friendly", "hero", "other_heroes"),
    "monster_treats_all_other_monsters_as_friendly": ("classify_friendly", "monster", "other_monsters"),
    "space_is_blocked": ("occupancy_label", "unknown", "occupied_or_obstacle_space"),
}


def classify_movement(rule_atoms):
    """Return provisional action descriptors with original premises for human review."""
    checked = _validate(rule_atoms)
    entries = []
    for row in checked:
        conclusion = row["then"]
        positive = conclusion.removeprefix("!")
        name = KNOWN.get(positive)
        entries.append({
            "rule": row["rule"],
            "source": "S002",
            "action": name[0] if name else "unknown",
            "actor": name[1] if name else "unknown",
            "target": name[2] if name else "unknown",
            "polarity": "negative" if conclusion.startswith("!") else "positive",
            "conditions": sorted(row["if"]),
            "conclusion": conclusion,
            "classification": "atom_name_only" if name else "unclassified",
            "scope_verified": False,
        })
    by_action = {x["action"] for x in entries}
    return {
        "scenario": "S002",
        "status": "review_required",
        "actions": entries,
        "distinctions_present": {
            key: key in by_action for key in ("enter_space", "pass_through", "end_movement")
        },
        "automatic_approval": False,
        "semantically_verified": False,
        "limitations": [
            "Only exact atom names are classified",
            "Conditions are preserved, not interpreted",
            "No equivalence or precedence between enter, pass and end is inferred",
            "Actor and target labels are provisional, not checked against the manual",
        ],
    }

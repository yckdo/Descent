"""Build a PRIVATE provisional S002 comparison reference from source metadata.

No source passage is copied into this file or into the output.
Hand-authored interpretation based on the supplied S002 passage; NOT human-reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from stair_s002_semantic_review import compare_s002, read_json


def _action(action, actor, target, polarity, conditions, conclusion):
    return {"action": action, "actor": actor, "target": target,
            "polarity": polarity, "conditions": conditions, "conclusion": conclusion}


def provisional_reference(draft):
    if not isinstance(draft, dict) or draft.get("case_id") != "descent_sec_0047":
        raise ValueError("Not S002 case")
    evidence = [x for x in draft.get("evidence", []) if isinstance(x, dict) and x.get("id") == "S002"]
    if len(evidence) != 1:
        raise ValueError("Expected one S002 evidence")
    item = evidence[0]
    if (item.get("page") != 8 or "#/texts/263" not in item.get("source_refs", [])
            or not isinstance(item.get("text"), str)):
        raise ValueError("S002 provenance mismatch")
    digest = hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
    if draft.get("evidence_hashes", {}).get("S002") != digest:
        raise ValueError("S002 source fingerprint mismatch")
    figure = ["figure"]
    occupied = ["figure", "space_contains_figure_or_obstacle"]
    entries = [
        _action("enter_space", "figure", "occupied_or_obstacle_space", "negative",
                occupied, "!figure_can_move_into_space"),
        _action("pass_through", "figure", "occupied_or_obstacle_space", "negative",
                occupied, "!figure_can_move_through_blocked_space"),
        _action("occupancy_label", "unknown", "occupied_or_obstacle_space", "positive",
                ["space_contains_figure_or_obstacle"], "space_is_blocked"),
        _action("move_diagonally", "figure", "diagonal_space", "positive",
                figure, "figure_can_move_diagonally"),
        _action("move_diagonally", "figure", "around_corner", "positive",
                ["figure", "moving_around_corner"], "figure_can_move_diagonally"),
        _action("move_diagonally", "figure", "between_blocked_spaces", "positive",
                ["figure", "moving_between_two_blocked_spaces"], "figure_can_move_diagonally"),
        _action("pass_through", "figure", "friendly_figure", "positive",
                ["figure", "space_contains_friendly_figure"],
                "figure_can_move_through_friendly_figure"),
        _action("classify_friendly", "hero", "other_heroes", "positive",
                ["hero"], "hero_treats_all_other_heroes_as_friendly"),
        _action("classify_friendly", "monster", "other_monsters", "positive",
                ["monster"], "monster_treats_all_other_monsters_as_friendly"),
        _action("end_movement", "figure", "occupied_space", "negative",
                ["figure", "figure_ends_movement_in_same_space_as_another_figure"],
                "!figure_can_end_movement_in_same_space"),
    ]
    return {
        "case_id": "descent_sec_0047", "source_id": "S002",
        "evidence_sha256": digest, "annotation_status": "synthetic_reference",
        "reviewer": "unreviewed_hand_authored_draft",
        "expected_actions": entries,
        "review_notes": [
            "Provisional interpretation of one supplied S002 passage, not a validated gold standard",
            "General no-passage rule must be examined together with friendly-figure permission",
            "Diagonal corner and between-blocked-spaces cases are explicit textual examples",
            "Confirm the difference between entering, passing through, and ending movement",
            "No rule priority or semantic correctness is established by matching descriptors",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Create private provisional S002 reference (no Qwen)")
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = provisional_reference(read_json(args.draft))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Do not overwrite human annotations or accidentally replace earlier reviews.
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(reference, out, ensure_ascii=False, indent=2)
        out.write("\n")
    print(json.dumps({"created": str(args.output), "case_id": reference["case_id"],
                      "expected_actions": len(reference["expected_actions"]),
                      "annotation_status": reference["annotation_status"],
                      "semantically_verified": False}, indent=2))


if __name__ == "__main__":
    main()

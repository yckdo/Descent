"""S002 conservative vocabulary normalization and review-only coverage comparison.

No model calls, rule promotion, or semantic approval. Unknown/ambiguous terms
are NEVER coerced into reference predicates. Original inputs are retained.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stair_s002_core_coverage import audit_coverage
from stair_s002_reference_draft import provisional_reference
from stair_s002_semantic_review import read_json, signature

# Explicit, narrowly accepted predicate wording. No action or target rewrites.
SAFE_CONDITION_ALIASES = {
    "space_occupied_by_figure_or_obstacle": "space_contains_figure_or_obstacle",
}
# Possible relations requiring human review, not normalization.
AMBIGUOUS_CONDITIONS = {
    "friendly_figure": "space_contains_friendly_figure",
    "same_space_as_another_figure": "figure_ends_movement_in_same_space_as_another_figure",
}
AMBIGUOUS_CONCLUSIONS = {
    "blocked_space": "space_is_blocked",
}


def normalize_s002(classification, reference):
    """Return candidate copies and a report; source objects are not mutated."""
    if not isinstance(classification, dict) or classification.get("scenario") != "S002":
        raise ValueError("S002 classification required")
    if not isinstance(reference, dict) or reference.get("annotation_status") != "synthetic_reference":
        raise ValueError("Provisional S002 reference required")
    rows = classification.get("actions")
    if not isinstance(rows, list) or len(rows) > 12:
        raise ValueError("Invalid candidate rows")
    normalized = []
    changes, unresolved = [], []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or row.get("source") != "S002":
            raise ValueError("Invalid source")
        signature(row)  # validates structure, polarity and conclusion
        new = dict(row)
        updated = []
        for term in row["conditions"]:
            if term in SAFE_CONDITION_ALIASES:
                replacement = SAFE_CONDITION_ALIASES[term]
                updated.append(replacement)
                changes.append({"rule": row.get("rule", f"R{index:03d}"),
                                "field": "conditions", "from": term, "to": replacement,
                                "status": "explicit_alias_not_semantic_proof"})
            else:
                updated.append(term)
                if term in AMBIGUOUS_CONDITIONS:
                    unresolved.append({"rule": row.get("rule", f"R{index:03d}"),
                                       "field": "conditions", "atom": term,
                                       "possible_reference": AMBIGUOUS_CONDITIONS[term],
                                       "reason": "not_guaranteed_equivalent"})
        if row["conclusion"] in AMBIGUOUS_CONCLUSIONS:
            unresolved.append({"rule": row.get("rule", f"R{index:03d}"),
                               "field": "conclusion", "atom": row["conclusion"],
                               "possible_reference": AMBIGUOUS_CONCLUSIONS[row["conclusion"]],
                               "reason": "nominal_label_vs_predicate"})
        # Never collapse aliases that would duplicate conditions or change arity.
        if len(updated) != len(set(updated)):
            unresolved.append({"rule": row.get("rule", f"R{index:03d}"),
                               "field": "conditions", "reason": "alias_collision"})
            updated = list(row["conditions"])
            changes = [c for c in changes if c["rule"] != row.get("rule", f"R{index:03d}")]
        new["conditions"] = sorted(updated)
        normalized.append(new)
    result_classification = {**classification, "actions": normalized}
    raw = audit_coverage(classification, reference)
    after = audit_coverage(result_classification, reference)
    return {
        "scenario": "S002",
        "status": "review_required",
        "before": {"core_exact_matches": raw["core_exact_matches"],
                   "core_missing": raw["core_missing"], "core_unexpected": raw["core_unexpected"]},
        "after": {"core_exact_matches": after["core_exact_matches"],
                  "core_missing": after["core_missing"], "core_unexpected": after["core_unexpected"]},
        "safe_alias_changes": changes,
        "unresolved_ambiguities": unresolved,
        "missing_core_actions": after["missing_core_actions"],
        "diagonal_scope_examples": after["diagonal_scope_examples"],
        "general_traversal_prohibition_present": after["general_traversal_prohibition_present"],
        "original_atoms_preserved": True,
        "automatic_approval": False,
        "semantically_verified": False,
        "warning": "Unmatched descriptor does not prove semantic omission; ambiguity requires independent review",
    }


def main():
    parser = argparse.ArgumentParser(description="Conservative S002 normalizer; no LLM calls")
    parser.add_argument("--draft", required=True, type=Path)
    args = parser.parse_args()
    reference = provisional_reference(read_json(args.draft))
    raw = sys.stdin.read(100_001)
    if len(raw.encode("utf-8")) > 100_000:
        parser.error("Input exceeds 100 KB")
    print(json.dumps(normalize_s002(json.loads(raw), reference), indent=2))


if __name__ == "__main__":
    main()

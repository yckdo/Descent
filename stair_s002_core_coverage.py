"""Read-only S002 coverage report: core rules vs examples vs exception relation.

Provisional reference only. No Qwen calls, no source passages, no approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from stair_s002_reference_draft import provisional_reference
from stair_s002_semantic_review import signature, read_json

EXAMPLE_TARGETS = frozenset({"around_corner", "between_blocked_spaces"})
CORE_EXCLUDED = frozenset(EXAMPLE_TARGETS)


def audit_coverage(classification, reference):
    if not isinstance(reference, dict) or reference.get("annotation_status") != "synthetic_reference":
        raise ValueError("Expected provisional reference")
    if not isinstance(classification, dict) or classification.get("scenario") != "S002":
        raise ValueError("Expected S002 classification")
    actions = classification.get("actions")
    expected = reference.get("expected_actions")
    if not isinstance(actions, list) or len(actions) > 12 or not isinstance(expected, list):
        raise ValueError("Invalid action lists")
    if any(not isinstance(a, dict) or a.get("source") != "S002" for a in actions):
        raise ValueError("Only S002 candidates accepted")
    core = [x for x in expected if x.get("target") not in CORE_EXCLUDED]
    examples = [x for x in expected if x.get("target") in EXAMPLE_TARGETS]
    actual = Counter(signature(x) for x in actions)
    expected_core = Counter(signature(x) for x in core)
    matches = actual & expected_core
    missing = expected_core - actual
    extra = actual - expected_core
    # Examples are explicit scope details, not independent core rules.
    detail_rows = []
    for x in examples:
        base = next((r for r in core if r["action"] == x["action"]
                     and r["target"] == "diagonal_space"), None)
        detail_rows.append({
            "target": x["target"],
            "base_action_present": base is not None and actual[signature(base)] > 0,
            "detail_explicitly_represented": actual[signature(x)] > 0,
            "status": "review_required",
        })
    general = next((x for x in core if x["conclusion"] == "!figure_can_move_through_blocked_space"), None)
    friendly = next((x for x in core if x["conclusion"] == "figure_can_move_through_friendly_figure"), None)
    return {
        "scenario": "S002",
        "status": "review_required",
        "core_expected": len(core),
        "core_exact_matches": sum(matches.values()),
        "core_missing": sum(missing.values()),
        "core_unexpected": sum(extra.values()),
        "missing_core_actions": [
            {"action": sig[0], "actor": sig[1], "target": sig[2],
             "polarity": sig[3], "conclusion": sig[5], "count": count}
            for sig, count in sorted(missing.items())
        ],
        "diagonal_scope_examples": detail_rows,
        "general_traversal_prohibition_present": bool(general and actual[signature(general)]),
        "friendly_pass_permission_present": bool(friendly and actual[signature(friendly)]),
        "exception_relation": "requires_human_review",
        "reference_status": "synthetic_reference",
        "automatic_approval": False,
        "semantically_verified": False,
        "warning": "Missing explicit example is not necessarily a missing independent rule; full meaning and exception precedence are unverified",
    }


def main():
    parser = argparse.ArgumentParser(description="Private S002 scope coverage report")
    parser.add_argument("--draft", type=Path, required=True)
    args = parser.parse_args()
    draft = read_json(args.draft)
    reference = provisional_reference(draft)
    raw = sys.stdin.read(100_001)
    if len(raw.encode("utf-8")) > 100_000:
        parser.error("Input too large")
    classification = json.loads(raw)
    print(json.dumps(audit_coverage(classification, reference), indent=2))


if __name__ == "__main__":
    main()

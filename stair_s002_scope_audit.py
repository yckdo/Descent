"""Read-only diagnostic for provisional S002 movement rules.

This is a *warning system*, not a semantic verifier and not a rule engine.
A verbatim quote or a matching action name cannot establish rule correctness.
No Ollama calls, no corpus access, and no automatic precedence decisions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ATOM = re.compile(r"!?[a-z][a-z0-9_]{0,79}\\Z")
REQUIRED_ACTIONS = (
    "figure_can_move_through_friendly_figure",
    "!figure_can_end_movement_in_same_space",
)
# Only a narrow set of movement verbs can be classified without guessing.
ACTION_TYPES = {
    "figure_can_move_into_space": "enter_space",
    "figure_can_move_through_friendly_figure": "pass_through_friendly",
    "figure_can_end_movement_in_same_space": "finish_in_occupied_space",
    "space_is_blocked": "occupancy_label",
}


def _validate(rows):
    if not isinstance(rows, list) or len(rows) > 12:
        raise ValueError("Expected at most 12 rule atoms")
    checked = []
    for i, item in enumerate(rows, 1):
        if not isinstance(item, dict) or item.get("source") != "S002":
            raise ValueError("Expected S002 rule atoms only")
        premises, conclusion = item.get("if"), item.get("then")
        if (not isinstance(premises, list) or not 1 <= len(premises) <= 8
                or not all(isinstance(p, str) and ATOM.fullmatch(p) for p in premises)
                or not isinstance(conclusion, str) or not ATOM.fullmatch(conclusion)):
            raise ValueError("Invalid rule atom structure")
        checked.append({"rule": f"R{i:03d}", "if": set(premises), "then": conclusion})
    return checked


def _opposite(atom):
    return atom[1:] if atom.startswith("!") else "!" + atom


def _possible_overlap(left, right):
    """Disjoint explicit literals can exclude overlap; otherwise unknown."""
    return not any(_opposite(p) in right for p in left)


def audit_s002(rule_atoms):
    """Report candidates for independent review; never assert true/false semantics."""
    rows = _validate(rule_atoms)
    issues = []
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            # This is an exact-literal contradiction only if premises could coexist.
            if (left["then"] == _opposite(right["then"])
                    and _possible_overlap(left["if"], right["if"])):
                issues.append({
                    "code": "potential_direct_conflict",
                    "rules": [left["rule"], right["rule"]],
                    "action": ACTION_TYPES.get(left["then"].lstrip("!"), "other"),
                })

    no_entry = [r for r in rows if r["then"] == "!figure_can_move_into_space"
                and "space_contains_figure_or_obstacle" in r["if"]]
    friendly_pass = [r for r in rows
                     if r["then"] == "figure_can_move_through_friendly_figure"
                     and "space_contains_friendly_figure" in r["if"]]
    if no_entry and friendly_pass:
        issues.append({
            "code": "entry_vs_friendly_pass_scope_review",
            "rules": [no_entry[0]["rule"], friendly_pass[0]["rule"]],
            "note": "Different actions; potential scope overlap, not a proven contradiction",
        })

    blocked = [r for r in rows if r["then"] == "space_is_blocked"
               and "space_contains_figure_or_obstacle" in r["if"]]
    if blocked and friendly_pass:
        issues.append({
            "code": "blocked_space_meaning_ambiguous",
            "rules": [blocked[0]["rule"], friendly_pass[0]["rule"]],
            "note": "Blocked must not be silently equated to cannot pass through",
        })

    conclusions = {r["then"] for r in rows}
    missing = [name for name in REQUIRED_ACTIONS if name not in conclusions]
    for action in missing:
        issues.append({"code": "required_action_absent", "action": action})

    classified = [
        {"rule": r["rule"], "action": ACTION_TYPES.get(r["then"].lstrip("!"), "other"),
         "polarity": "prohibition" if r["then"].startswith("!") else "affirmation"}
        for r in rows
    ]
    return {
        "scenario": "S002",
        "status": "review_required",
        "rule_count": len(rows),
        "missing_required_actions": missing,
        "issues": issues,
        "action_classes": classified,
        "automatic_approval": False,
        "semantically_verified": False,
        "limitations": [
            "Different action verbs are not interchangeable",
            "Potential conflicts require compatible conditions and human review",
            "No exception priority inferred or applied",
            "Action presence does not prove correct scope, meaning, or completeness",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only S002 rule-atom scope audit; no Ollama")
    parser.add_argument("input", type=Path, help="Saved local JSON with rule_atoms, or '-' for stdin")
    args = parser.parse_args(argv)
    if str(args.input) == "-":
        raw = sys.stdin.read(100_001)
    else:
        if args.input.stat().st_size > 100_000:
            parser.error("Input exceeds 100 KB")
        raw = args.input.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > 100_000:
        parser.error("Input exceeds 100 KB")
    payload = json.loads(raw)
    rows = payload.get("rule_atoms") if isinstance(payload, dict) else payload
    print(json.dumps(audit_s002(rows), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

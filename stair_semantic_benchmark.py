"""Compare extracted rules to independently reviewed gold annotations.

This is an *evaluation harness*, NOT automated semantic entailment.
No inferred approval may flow from this module to the production reasoner.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from stair_rule_extractor import validate_candidates
from stair_fidelity_gate import triage_candidates

MAX_CASES = 1000


def _fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _signature(rule):
    """Compare full premise sets and conclusions; do not use fuzzy matching."""
    return (tuple(sorted(rule["if"])), rule["then"], rule["source"])


def evaluate_case(case):
    """Evaluate one test question against explicit human-reviewed truth data."""
    if not isinstance(case, dict):
        raise ValueError("Case must be an object")
    evidence = case["evidence"]
    proposals = case["proposals"]
    gold = case["gold_rules"]
    if not isinstance(evidence, list) or not isinstance(gold, list):
        raise ValueError("Evidence and gold_rules must be lists")
    if not case.get("case_id") or not isinstance(case["case_id"], str):
        raise ValueError("Missing case_id")
    if case.get("annotation_status") != "human_reviewed":
        raise ValueError("Gold data must be explicitly human reviewed")
    if not case.get("reviewer") or not isinstance(case["reviewer"], str):
        raise ValueError("Reviewer required")
    if not isinstance(case.get("evidence_hashes"), dict):
        raise ValueError("Evidence fingerprints required")

    by_id = {}
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Malformed evidence")
        if item["id"] in by_id:
            raise ValueError("Duplicate evidence id")
        by_id[item["id"]] = item
        expected = case["evidence_hashes"].get(item["id"])
        if expected != _fingerprint(item["text"]):
            raise ValueError("Gold annotation attached to changed evidence")
    if set(by_id) != set(case["evidence_hashes"]):
        raise ValueError("Evidence fingerprint set mismatch")

    candidates = validate_candidates(proposals, evidence)
    reviews = triage_candidates(candidates["candidates"], evidence)["reviews"]
    # Gold entries are reviewer-authored exact structured rules, without text.
    gold_signatures = set()
    for item in gold:
        if not isinstance(item, dict) or not isinstance(item.get("if"), list):
            raise ValueError("Invalid gold")
        if not item["if"] or not isinstance(item.get("then"), str) or item.get("source") not in by_id:
            raise ValueError("Invalid gold rule")
        if not all(isinstance(atom, str) and atom for atom in item["if"]):
            raise ValueError("Invalid gold premises")
        signature = _signature(item)
        if signature in gold_signatures:
            raise ValueError("Duplicate gold rule")
        gold_signatures.add(signature)

    candidate_signatures = {
        _signature(item) for item, review in zip(candidates["candidates"], reviews)
        if review["status"] == "needs_review"
    }
    matches = len(candidate_signatures & gold_signatures)
    return {
        "case_id": case["case_id"],
        "annotation_status": "human_reviewed",
        "matched": matches,
        "false_positive": len(candidate_signatures - gold_signatures),
        "false_negative": len(gold_signatures - candidate_signatures),
        "rejected_proposals": candidates["rejected_count"],
        "unapproved_proposals": len(candidate_signatures),
        "result": "exact_match" if candidate_signatures == gold_signatures
                  and candidates["rejected_count"] == 0 else "mismatch",
        "promotable": False,
    }


def evaluate_suite(suite):
    if not isinstance(suite, dict) or not isinstance(suite.get("cases"), list):
        raise ValueError("Suite must contain cases")
    cases = suite["cases"]
    if not cases or len(cases) > MAX_CASES:
        raise ValueError("Invalid number of cases")
    rows = [evaluate_case(case) for case in cases]
    if len(set(row["case_id"] for row in rows)) != len(rows):
        raise ValueError("Duplicate case_id")
    tp = sum(row["matched"] for row in rows)
    fp = sum(row["false_positive"] for row in rows)
    fn = sum(row["false_negative"] for row in rows)
    return {
        "cases": len(rows),
        "exact_cases": sum(row["result"] == "exact_match" for row in rows),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "matched": tp,
        "false_positive": fp,
        "false_negative": fn,
        "rejected_proposals": sum(row["rejected_proposals"] for row in rows),
        "all_rules_unapproved": True,
        "rows": rows,
        "warning": "Fixture agreement is not proof of general semantic validity.",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    if args.fixture.stat().st_size > 2_000_000:
        parser.error("Fixture too large")
    print(json.dumps(evaluate_suite(json.loads(
        args.fixture.read_text(encoding="utf-8"))), indent=2))

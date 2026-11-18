"""S002 experiment: real STAIR evidence -> candidate comparison -> logical demo.

All reference rules are provisional, not independently reviewed.
No copyrighted evidence is stored in this public source file.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from stair_reasoner import reason
from stair_rule_extractor import propose_candidates
from stair_semantic_benchmark import evaluate_case

SECTION = "descent_sec_0047"
REF = "#/texts/263"
EXPECTED = [
    {"if": ["hero_moving", "other_hero_occupies_space"],
     "then": "may_pass_through_other_hero", "source": "S002"},
    {"if": ["hero_ending_movement", "other_hero_occupies_space"],
     "then": "!may_end_on_other_hero", "source": "S002"},
]
# A language-model extraction might choose different atomic names, so the
# benchmark uses exact names as a deliberately strict first experiment.


def run_case(case, *, extractor=None):
    """Run with an existing private STAIR section draft (not arbitrary text)."""
    if not isinstance(case, dict) or case.get("case_id") != SECTION:
        raise ValueError("Expected STAIR movement draft")
    evidence = case.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("Missing STAIR evidence")
    source = [item for item in evidence if item.get("id") == "S002"]
    if len(source) != 1 or source[0].get("page") != 8 or REF not in source[0].get("source_refs", []):
        raise ValueError("S002 identity/page/Docling reference mismatch")
    if not isinstance(source[0].get("text"), str) or not source[0]["text"]:
        raise ValueError("S002 text missing")
    # Evaluate only the relevant passage, avoiding confusion with other S IDs.
    evidence = source
    proposals = {"rules": []}
    if extractor is not None:
        proposed = propose_candidates(evidence, generator=extractor)
        proposals = {"rules": [{
            "id": rule["id"], "if": rule["if"], "then": rule["then"],
            "evidence_id": rule["source"], "quote": rule["quote"]
        } for rule in proposed["candidates"]]}
    refcase = {
        "case_id": "s002_experiment",
        "annotation_status": "synthetic_reference",
        "reviewer": "provisional_not_human_reviewed",
        "evidence": evidence,
        "evidence_hashes": {"S002": case["evidence_hashes"].get("S002")},
        "proposals": proposals, "gold_rules": EXPECTED,
    }
    agreement = evaluate_case(refcase)
    # Feed ONLY manually constructed illustrative rules to the reasoner.
    # Do not feed unreviewed Qwen proposals.
    rules = [{"id": f"s002_demo_{i}", "if": item["if"], "then": item["then"],
              "source": REF} for i, item in enumerate(EXPECTED, 1)]
    demos = {}
    for name, premises in [
        ("traverse", ["hero_moving", "other_hero_occupies_space"]),
        ("finish", ["hero_ending_movement", "other_hero_occupies_space"]),
    ]:
        spec = {"facts": [{"literal": value, "source": "hypothetical_scenario"}
                          for value in premises],
                "rules": rules,
                "query": ("may_pass_through_other_hero" if name == "traverse"
                          else "may_end_on_other_hero")}
        output = reason(spec)
        demos[name] = {"status": output["status"],
                       "proof_steps": len(output["proof_graph"])}
    return {"source_ref": REF, "section": SECTION,
            "agreement": agreement, "logical_demonstration": demos,
            "reference_review_status": "provisional",
            "automatic_approval": False,
            "warning": "Not a real Qwen accuracy score without --extract; atom vocabulary must be aligned before scoring."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path, help="Local private descent_sec_0047.json")
    parser.add_argument("--extract", action="store_true",
                        help="Explicitly call localhost Ollama for candidate extraction")
    args = parser.parse_args()
    case = json.loads(args.draft.read_text(encoding="utf-8"))
    generator = None
    if args.extract:
        from stair_rule_extractor import _local_ollama
        import os
        def generator(messages):
            return _local_ollama(messages, url="http://127.0.0.1:11434/api/chat",
                                 model=os.environ.get("STAIR_EXTRACTOR_MODEL", "qwen2.5-coder:14b"),
                                 timeout=30)
    print(json.dumps(run_case(case, extractor=generator), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

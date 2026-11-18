"""Read-only S002 comparison with independent structured review. Not semantic proof."""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

FIELDS = ("action", "actor", "target", "polarity", "conditions", "conclusion")
ATOM = re.compile(r"!?[a-z][a-z0-9_]{0,79}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def signature(item):
    if not isinstance(item, dict):
        raise ValueError("Expected descriptor object")
    for key in FIELDS[:4]:
        if not isinstance(item.get(key), str) or not item[key]:
            raise ValueError("Invalid descriptor field: " + key)
    terms, result = item.get("conditions"), item.get("conclusion")
    if (not isinstance(terms, list) or not 1 <= len(terms) <= 8
            or not all(isinstance(t, str) and ATOM.fullmatch(t) for t in terms)
            or len(set(terms)) != len(terms)
            or not isinstance(result, str) or not ATOM.fullmatch(result)):
        raise ValueError("Invalid conditions or conclusion")
    if item["polarity"] not in ("positive", "negative"):
        raise ValueError("Invalid polarity")
    if result.startswith("!") != (item["polarity"] == "negative"):
        raise ValueError("Polarity and conclusion disagree")
    return (item["action"], item["actor"], item["target"], item["polarity"],
            tuple(sorted(terms)), result)


def compare_s002(classification, reference, evidence_sha256):
    """Compare exact descriptors without approving rules or inferring exceptions."""
    if not isinstance(evidence_sha256, str) or not SHA.fullmatch(evidence_sha256):
        raise ValueError("Invalid evidence fingerprint")
    if not isinstance(classification, dict) or classification.get("scenario") != "S002":
        raise ValueError("Expected S002 classification")
    if (not isinstance(reference, dict)
            or reference.get("case_id") != "descent_sec_0047"
            or reference.get("source_id") != "S002"
            or reference.get("evidence_sha256") != evidence_sha256):
        raise ValueError("Review does not match the S002 source")
    annotation_status = reference.get("annotation_status")
    if annotation_status not in ("synthetic_reference", "human_reviewed"):
        raise ValueError("Missing review status")
    if annotation_status == "human_reviewed" and (
            not isinstance(reference.get("reviewer"), str)
            or not reference["reviewer"].strip()):
        raise ValueError("Human review requires reviewer metadata")
    actions, gold = classification.get("actions"), reference.get("expected_actions")
    if (not isinstance(actions, list) or len(actions) > 12
            or not isinstance(gold, list) or not 1 <= len(gold) <= 50):
        raise ValueError("Invalid descriptor lists")
    if any(not isinstance(x, dict) or x.get("source") != "S002" for x in actions):
        raise ValueError("Candidate source mismatch")
    actual = Counter(signature(x) for x in actions)
    expected = Counter(signature(x) for x in gold)
    matched = sum((actual & expected).values())
    extras = sum((actual - expected).values())
    missing = sum((expected - actual).values())
    return {
        "scenario": "S002", "status": "review_required",
        "reference_status": annotation_status,
        "reference_metadata_claims_human_review": annotation_status == "human_reviewed",
        "exact_field_matches": matched,
        "unexpected_candidates": extras,
        "missing_reference_actions": missing,
        "exact_descriptor_agreement": extras == 0 and missing == 0,
        "automatic_approval": False, "semantically_verified": False,
        "warning": "Exact field agreement is not semantic truth; reviewer independence is not authenticated",
    }


def read_json(path):
    if path.stat().st_size > 2_000_000:
        raise ValueError("File too large")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Local-only S002 comparison; no Qwen calls")
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    draft = read_json(args.draft)
    evidence = [x for x in draft.get("evidence", []) if x.get("id") == "S002"]
    if len(evidence) != 1 or not isinstance(evidence[0].get("text"), str):
        parser.error("Expected exactly one S002 evidence")
    digest = hashlib.sha256(evidence[0]["text"].encode("utf-8")).hexdigest()
    if draft.get("evidence_hashes", {}).get("S002") != digest:
        parser.error("Source fingerprint mismatch")
    raw = sys.stdin.read(100_001)
    if len(raw.encode("utf-8")) > 100_000:
        parser.error("Classification too large")
    print(json.dumps(compare_s002(json.loads(raw), read_json(args.reference), digest),
                     indent=2))


if __name__ == "__main__":
    main()

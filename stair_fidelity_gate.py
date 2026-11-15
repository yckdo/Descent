"""Fail-closed fidelity triage for STAIR rules; never grants semantic approval.

The check is deliberately conservative. Matching a verbatim quote is *not*
proof that the proposed condition and consequence are entailed by that quote.
"""
from __future__ import annotations

import hashlib
import re

MAX_QUOTE = 800
RISK = {
    "exception_or_override": re.compile(r"\b(?:except|unless|however|instead|but|only if|even if|cannot|can't|may not|must not|not allowed)\b", re.I),
    "scope_or_time": re.compile(r"\b(?:during|before|after|at the start|at the end|while|until|once per|each turn|per turn|when|whenever)\b", re.I),
    "quantity": re.compile(r"\b(?:at least|at most|up to|exactly|no more than|one|two|three|\d+)\b", re.I),
}
ATOM = re.compile(r"!?[a-z][a-z0-9_]{0,79}\Z")


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def triage_candidate(candidate, evidence):
    """Return only non-approving statuses; require original full excerpt."""
    result = {"status": "blocked", "semantically_verified": False, "issues": []}
    if not isinstance(candidate, dict) or not isinstance(evidence, dict):
        result["issues"].append("invalid_input")
        return result
    quote = candidate.get("quote")
    eid = candidate.get("source")
    provenance = candidate.get("provenance")
    raw_text = evidence.get("text")
    premises = candidate.get("if")
    conclusion = candidate.get("then")
    if (not isinstance(quote, str) or not 12 <= len(quote) <= MAX_QUOTE
            or not isinstance(raw_text, str) or not raw_text
            or not isinstance(eid, str) or eid != evidence.get("id")
            or not isinstance(provenance, dict)
            or provenance.get("evidence_id") != eid
            or provenance.get("source_refs") != evidence.get("source_refs")
            or provenance.get("page") != evidence.get("page")
            or not isinstance(premises, list) or not 1 <= len(premises) <= 8
            or not all(isinstance(p, str) and ATOM.fullmatch(p) for p in premises)
            or not isinstance(conclusion, str) or not ATOM.fullmatch(conclusion)):
        result["issues"].append("invalid_or_mismatched_provenance")
        return result
    if quote not in raw_text:
        result["issues"].append("quote_not_in_source")
        return result

    result["status"] = "needs_review"
    result["source_digest"] = _digest(raw_text)
    result["candidate_digest"] = _digest(repr((candidate.get("id"), premises, conclusion, quote, eid)))
    result["issues"].append("entailment_not_proven")
    for label, regex in RISK.items():
        # Search entire evidence, not only the quoted span, to catch omissions
        # of surrounding exceptions or conditions.
        if regex.search(raw_text):
            result["issues"].append(label)
    if raw_text.count(quote) > 1:
        result["issues"].append("ambiguous_quote_occurrence")
    if quote != raw_text.strip():
        result["issues"].append("partial_quote_context")
    return result


def triage_candidates(candidates, evidence):
    """Triage a list against the exact evidence set; never export to reasoner."""
    if not isinstance(candidates, list) or not isinstance(evidence, list):
        raise ValueError("Expected lists")
    lookup = {item["id"]: item for item in evidence if isinstance(item, dict) and isinstance(item.get("id"), str)}
    outcomes = []
    for item in candidates:
        original = lookup.get(item.get("source")) if isinstance(item, dict) else None
        outcomes.append(triage_candidate(item, original))
    return {"status": "review_required", "candidate_count": len(outcomes),
            "blocked_count": sum(r["status"] == "blocked" for r in outcomes),
            "needs_review_count": sum(r["status"] == "needs_review" for r in outcomes),
            "semantically_verified": False, "reviews": outcomes}

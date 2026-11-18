"""Conservative source-backed forward-chaining prototype; no natural-language extraction."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def literal(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Empty literal")
    value = value.strip()
    if value.startswith("!!") or value == "!":
        raise ValueError("Invalid literal")
    return value


def source(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing source")
    return value.strip()


def opposite(value):
    return value[1:] if value.startswith("!") else "!" + value


def reason(spec):
    if not isinstance(spec, dict):
        raise ValueError("Expected object")
    facts = spec.get("facts", [])
    rules = spec.get("rules", [])
    query = literal(spec["query"])
    if not isinstance(facts, list) or not isinstance(rules, list) or len(facts) + len(rules) > 10000:
        raise ValueError("Invalid or oversized facts/rules")
    proofs = {}
    for fact in facts:
        name = literal(fact["literal"])
        proofs.setdefault(name, {"kind": "fact", "literal": name, "source": source(fact["source"]), "premises": []})
    validated = []
    ids = set()
    for rule in rules:
        rid = rule["id"]
        if not isinstance(rid, str) or not rid.strip() or rid in ids:
            raise ValueError("Duplicate or invalid rule ID")
        ids.add(rid)
        premises = [literal(p) for p in rule["if"]]
        if not premises:
            raise ValueError("Rule without premises")
        validated.append((rid, premises, literal(rule["then"]), source(rule["source"])))
    for _ in range(len(validated) + 1):
        changed = False
        for rid, premises, conclusion, ref in sorted(validated):
            if conclusion not in proofs and all(p in proofs for p in premises):
                proofs[conclusion] = {"kind": "rule", "literal": conclusion, "rule_id": rid, "source": ref, "premises": premises}
                changed = True
        if not changed:
            break
    yes, no = query in proofs, opposite(query) in proofs
    status = "contradicted" if yes and no else "supported" if yes else "refuted" if no else "uncertain"
    needed = set()
    def visit(name):
        if name in needed or name not in proofs:
            return
        needed.add(name)
        for premise in proofs[name]["premises"]:
            visit(premise)
    visit(query)
    visit(opposite(query))
    return {"query": query, "status": status,
            "proof_graph": [proofs[name] for name in sorted(needed)],
            "limitations": ["Explicit facts and Horn-style rules only",
                            "Open-world assumption: missing does not imply false",
                            "Source identifiers are not authenticated",
                            "Exceptions and rule precedence require upstream normalization"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    print(json.dumps(reason(json.loads(args.input.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))

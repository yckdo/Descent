
import json
from copy import deepcopy
from pathlib import Path

from audit_stair_generic import audit_capture, load_json
from validate_stair_evidence import audit_evidence

ROOT = Path(__file__).resolve().parent


def merge_additions(capture, reviewed, reference):
    if capture["question"] != reviewed["question"]:
        raise ValueError("Questions différentes.")

    if reviewed["scenario"] != reference["scenario"]:
        raise ValueError("Scénarios différents.")

    original_points = deepcopy(capture["answer"]["points"])
    evidence = capture["evidence"]

    allowed_ids = {item["id"] for item in evidence}

    existing_citations = {
        (point["text"].strip(), tuple(point["source_ids"]))
        for point in original_points
    }

    merged_points = list(original_points)

    for addition in reviewed["additions"]:
        text = addition["text"].strip()
        source_ids = addition["source_ids"]

        if not text:
            raise ValueError("Complément vide.")

        if not source_ids or not set(source_ids).issubset(
            allowed_ids
        ):
            raise ValueError("Citations invalides.")

        signature = (text, tuple(source_ids))

        if signature in existing_citations:
            continue

        merged_points.append({
            "text": text,
            "source_ids": source_ids,
        })

        existing_citations.add(signature)

    merged_answer = {"points": merged_points}

    citation_audit = audit_evidence(
        merged_answer,
        evidence,
    )

    if not citation_audit["valid"]:
        raise ValueError(
            "Audit des citations échoué : "
            + str(citation_audit["errors"])
        )

    merged_capture = {
        **capture,
        "answer": merged_answer,
    }

    coverage = audit_capture(
        merged_capture,
        reference,
    )

    return {
        "answer": merged_answer,
        "citation_audit": citation_audit,
        "coverage_audit": coverage,
        "semantic_validation_completed": False,
    }


def main():
    capture = load_json(
        ROOT / "validation/captures/boutique_latest.json"
    )

    reviewed = load_json(
        ROOT / "validation/captures/boutique_web_additions_reviewed.json"
    )

    reference = load_json(
        ROOT / "validation/rule_checks/boutique.json"
    )

    result = merge_additions(
        capture,
        reviewed,
        reference,
    )

    original_count = len(capture["answer"]["points"])
    merged_count = len(result["answer"]["points"])

    print("=== FUSION STAIR — BOUTIQUE ===")
    print("Points initiaux :", original_count)
    print("Points après fusion :", merged_count)
    print("Citations valides :", result["citation_audit"]["valid"])
    print(
        "Règles signalées après fusion :",
        result["coverage_audit"]["rules_flagged"],
    )
    print(
        "Validation sémantique automatique :",
        result["semantic_validation_completed"],
    )
    print("Aucun fichier modifié.")
    print("Aucun appel Ollama.")


if __name__ == "__main__":
    main()

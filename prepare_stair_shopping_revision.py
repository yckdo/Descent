
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CAPTURE = ROOT / "validation/captures/boutique_latest.json"
COVERAGE = ROOT / "validation/captures/boutique_coverage.json"
OUTPUT = ROOT / "validation/captures/boutique_revision_input.json"

def load(path):
    if not path.is_file():
        raise SystemExit(f"Fichier absent : {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def main():
    capture = load(CAPTURE)
    coverage = load(COVERAGE)

    if capture.get("scenario") != "boutique":
        raise ValueError("Capture inattendue")

    if coverage.get("scenario") != "boutique":
        raise ValueError("Audit inattendu")

    if not capture.get("citation_audit", {}).get("valid"):
        raise ValueError("Citations initiales non valides")

    evidence_by_id = {
        item["id"]: item
        for item in capture["evidence"]
    }

    missing_rules = [
        check
        for check in coverage["checks"]
        if not check["lexical_signals_present"]
    ]

    revision_items = []

    for rule in missing_rules:
        source_id = rule["source_id"]

        if source_id not in evidence_by_id:
            raise ValueError(
                f"Source introuvable : {source_id}"
            )

        source = evidence_by_id[source_id]

        revision_items.append({
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "source_id": source_id,
            "pdf_page": source["page"],
            "section_id": source["section_id"],
            "source_text": source["text"],
            "source_refs": source["source_refs"],
        })

    result = {
        "scenario": "boutique",
        "question": capture["question"],
        "model": capture["model"],
        "original_answer": capture["answer"],
        "revision_mode": "add_missing_rules_only",
        "rules_to_review": revision_items,
        "semantic_validation_completed": False,
    }

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8",
    )

    print("=== PRÉPARATION RÉVISION BOUTIQUE ===")
    print("Règles à examiner :", len(revision_items))

    for rule in revision_items:
        print(
            f"{rule['source_id']} | "
            f"PDF p.{rule['pdf_page']} | "
            f"{rule['rule_name']}"
        )

    print()
    print("Dossier :", OUTPUT)
    print("Aucun appel Ollama.")
    print("Réponse initiale inchangée.")
    print("Corpus V3 inchangé.")


if __name__ == "__main__":
    main()

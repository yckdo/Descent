
import json
from pathlib import Path

from validate_stair_evidence import audit_evidence

ROOT = Path(__file__).resolve().parent

CAPTURE = ROOT / "validation/captures/boutique_latest.json"
ADDITIONS = ROOT / "validation/captures/boutique_additions.json"
OUTPUT = ROOT / "validation/captures/boutique_consolidated.json"

# Formulations contrôlées à partir des sources.
# Elles remplacent uniquement les compléments,
# sans réécrire les cinq points initiaux.
DOCUMENTED_ADDITIONS = {
    "saved_gold": {
        "text": (
            "Les héros ne sont pas obligés de dépenser "
            "tout leur or pendant la phase de campagne. "
            "Ils peuvent en conserver pour une phase "
            "de campagne ultérieure."
        ),
        "source_id": "S002",
    },
    "act_transition": {
        "text": (
            "Le paquet Boutique dépend de l'acte en cours : "
            "les cartes de l'acte I sont utilisées jusqu'à "
            "la fin de l'Interlude, puis les joueurs "
            "utilisent les cartes de l'acte II."
        ),
        "source_id": "S003",
    },
    "unbought_cards": {
        "text": (
            "Après les achats, les cartes Boutique "
            "non achetées sont remélangées dans "
            "le paquet Boutique."
        ),
        "source_id": "S005",
    },
}


def main():
    capture = json.loads(
        CAPTURE.read_text(encoding="utf-8")
    )
    additions = json.loads(
        ADDITIONS.read_text(encoding="utf-8")
    )

    if capture["scenario"] != "boutique":
        raise ValueError("Capture inattendue")

    if additions["scenario"] != "boutique":
        raise ValueError("Compléments inattendus")

    original_points = capture["answer"]["points"]

    if len(original_points) != 5:
        raise ValueError("Cinq points initiaux attendus")

    generated_ids = {
        item["rule_id"]
        for item in additions["additions"]
    }

    expected_ids = set(DOCUMENTED_ADDITIONS)

    if generated_ids != expected_ids:
        raise ValueError(
            "Liste des compléments inattendue"
        )

    consolidated_points = [
        {
            "text": point["text"],
            "source_ids": list(point["source_ids"]),
        }
        for point in original_points
    ]

    for rule_id, addition in DOCUMENTED_ADDITIONS.items():
        consolidated_points.append({
            "text": addition["text"],
            "source_ids": [addition["source_id"]],
        })

    answer = {"points": consolidated_points}

    audit = audit_evidence(
        answer,
        capture["evidence"],
    )

    if not audit["valid"]:
        raise ValueError(
            f"Audit documentaire échoué : {audit['errors']}"
        )

    result = {
        "scenario": "boutique",
        "question": capture["question"],
        "method": "documented_additions",
        "original_points_preserved": True,
        "answer": answer,
        "citation_audit": audit,
        "semantic_validation_completed": False,
    }

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print("=== CONSOLIDATION STAIR : BOUTIQUE ===")
    print("Points initiaux conservés :", len(original_points))
    print("Compléments ajoutés :", len(DOCUMENTED_ADDITIONS))
    print("Points finaux :", len(consolidated_points))
    print("Citations valides :", audit["valid"])
    print("Fichier :", OUTPUT)
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")


if __name__ == "__main__":
    main()

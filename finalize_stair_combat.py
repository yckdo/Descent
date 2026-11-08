
import json
from pathlib import Path

from answer_stair_ollama import (
    prepare_evidence,
    validate_answer,
)

ROOT = Path(__file__).resolve().parent

INPUT = ROOT / "validation/stair_combat_revised.json"
OUTPUT = ROOT / "validation/stair_combat_final_review.json"
REPORT = ROOT / "validation/stair_combat_final_review.txt"

QUESTION = "Comment fonctionne le combat ?"

ADDITION = (
    " Le défenseur constitue également sa réserve de dés "
    "de défense à partir des dés indiqués sur sa fiche de "
    "héros ou sa carte Monstre, en ajoutant ceux accordés "
    "par son équipement et les effets de cartes. "
    "Les dés supplémentaires doivent être ajoutés avant "
    "le lancer, puis le défenseur lance sa réserve."
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    previous = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    answer = previous["revised_answer"]

    data = prepare_evidence(QUESTION)

    require(data is not None, "Sources STAIR introuvables")

    evidence = data["evidence"]

    validate_answer(answer, evidence)

    require(
        len(answer["points"]) == 5,
        "Cinq étapes attendues"
    )

    source = next(
        (
            item for item in evidence
            if item["id"] == "S008"
        ),
        None
    )

    require(source is not None, "Source S008 absente")

    require(
        source["section_id"] == "sec_0073"
        and source["page"] == 12,
        "Provenance de S008 inattendue"
    )

    # Vérifier la présence des éléments documentaires
    # indispensables dans la source originale.
    source_text = source["text"].casefold()

    for term in [
        "defending player",
        "defense pool",
        "hero sheet",
        "monster card",
    ]:
        require(
            term in source_text,
            f"Terme documentaire absent : {term}"
        )

    final_answer = {
        "points": [
            {
                "text": point["text"],
                "source_ids": list(point["source_ids"]),
            }
            for point in answer["points"]
        ]
    }

    step_2 = final_answer["points"][1]

    # Protéger l'opération contre une double insertion.
    require(
        "Le défenseur constitue également" not in step_2["text"],
        "Correction déjà présente"
    )

    step_2["text"] += ADDITION

    if "S008" not in step_2["source_ids"]:
        step_2["source_ids"].append("S008")

    validate_answer(final_answer, evidence)

    result = {
        "question": QUESTION,
        "method": "documented_manual_correction",
        "corrected_step": 2,
        "added_source": "S008",
        "semantic_validation_completed": False,
        "answer": final_answer,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8",
    )

    lines = [
        "=== RÉPONSE COMBAT APRÈS CORRECTION ===",
        "",
    ]

    for point in final_answer["points"]:
        lines.append(point["text"])
        lines.append(
            "Sources : "
            + ", ".join(point["source_ids"])
        )
        lines.append("")

    lines.extend([
        "=== CONTRÔLE ===",
        "Correction ajoutée : étape 2",
        "Source vérifiée : S008, PDF p.12",
        "Autres étapes conservées.",
        "Aucun appel Ollama.",
        "Validation sémantique complète : non.",
        "Corpus V3 inchangé.",
    ])

    REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("=== FINALISATION COMBAT STAIR ===")
    print("Étapes :", len(final_answer["points"]))
    print("Correction :", "Constitution des dés de défense")
    print("Source ajoutée : S008, PDF p.12")
    print("Autres étapes : inchangées")
    print("Rapport :", REPORT)
    print("JSON :", OUTPUT)
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")


if __name__ == "__main__":
    main()

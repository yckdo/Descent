
import json
import re
import unicodedata
from pathlib import Path

from answer_stair_ollama import (
    prepare_evidence,
    validate_answer,
)

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "validation/stair_combat_final_review.json"
OUTPUT = ROOT / "validation/stair_regressions_review.txt"

QUESTION = "Comment fonctionne le combat ?"

# Contrôles documentaires spécifiques au test Combat.
# Ils ne constituent pas un évaluateur universel.
CHECKS = [
    {
        "step": 2,
        "name": "Échec automatique sur X",
        "required_sources": ["S007"],
        "patterns": [r"\bx\b", r"\bbleu\b"],
    },
    {
        "step": 2,
        "name": "Constitution de la défense",
        "required_sources": ["S008"],
        "patterns": [
            r"\bdefenseur\b",
            r"\b(?:des|de)\s+defense\b|\breserve de defense\b",
        ],
    },
    {
        "step": 2,
        "name": "Relances des dés",
        "required_sources": ["S010"],
        "patterns": [r"\brelanc"],
    },
    {
        "step": 4,
        "name": "Restrictions des capacités SURGE",
        "required_sources": ["S015"],
        "patterns": [
            r"\bcapacite",
            r"\bune fois\b",
            r"\bdifferent",
        ],
    },
    {
        "step": 4,
        "name": "Récupération de fatigue",
        "required_sources": ["S016"],
        "patterns": [
            r"\bheros\b",
            r"\bfatigue\b",
            r"\bsurge\b",
        ],
    },
    {
        "step": 5,
        "name": "Défaite et santé",
        "required_sources": ["S020"],
        "patterns": [r"\bsante\b", r"\b(?:battu|vaincu|defait)"],
    },
    {
        "step": 5,
        "name": "Défense contre les dégâts hors attaque",
        "required_sources": ["S022"],
        "patterns": [
            r"\bdefense\b",
            r"\bhors d'une attaque\b|\bautre raison\b",
        ],
    },
]


def normalize(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", text)


def main():
    saved = json.loads(INPUT.read_text(encoding="utf-8"))
    answer = saved["answer"]

    data = prepare_evidence(QUESTION)
    if data is None:
        raise ValueError("Aucune source STAIR disponible")

    evidence = data["evidence"]

    # Vérification des identifiants existants.
    sources = validate_answer(answer, evidence)
    points = answer["points"]

    if len(points) != 5:
        raise ValueError("Cinq étapes attendues")

    lines = [
        "=== AUDIT DES RÉGRESSIONS STAIR ===",
        "Test : Combat",
        "Réponse : dernière révision enregistrée",
        "Aucun appel à Ollama",
        "",
    ]

    alerts = 0

    for check in CHECKS:
        step = check["step"]
        point = points[step - 1]

        cited = set(point["source_ids"])

        valid_provenance = all(
            sid in cited and sid in sources
            for sid in check["required_sources"]
        )

        text = normalize(point["text"])

        detected = all(
            re.search(pattern, text)
            for pattern in check["patterns"]
        )

        if not valid_provenance or not detected:
            alerts += 1

        status = (
            "INDICES ET CITATIONS PRÉSENTS"
            if valid_provenance and detected
            else "À EXAMINER"
        )

        lines.extend([
            f"ÉTAPE {step} | {check['name']}",
            f"  Statut : {status}",
            f"  Citations attendues : "
            f"{', '.join(check['required_sources'])}",
            f"  Citations présentes : "
            f"{'OUI' if valid_provenance else 'NON'}",
            f"  Indices textuels : "
            f"{'PRÉSENTS' if detected else 'INCOMPLETS'}",
            "",
        ])

    lines.extend([
        "=== BILAN ===",
        f"Contrôles : {len(CHECKS)}",
        f"Signalements : {alerts}",
        "",
        "LIMITES :",
        "Les citations attendues sont propres à ce test.",
        "Une autre source peut parfois justifier la même règle.",
        "Les expressions régulières peuvent manquer une paraphrase.",
        "Ce contrôle ne garantit pas la fidélité sémantique.",
        "Corpus V3 inchangé.",
    ])

    OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("=== AUDIT DES RÉGRESSIONS STAIR ===")
    print("Contrôles :", len(CHECKS))
    print("Signalements :", alerts)
    print("Rapport :", OUTPUT)
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")


if __name__ == "__main__":
    main()



import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent

INPUT = ROOT / "validation/stair_rule_coverage_review.json"
OUTPUT = ROOT / "validation/stair_combat_semantic_checks.txt"


def normalize(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", text)


def contains_any(text, patterns):
    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def check_rule(point, requirements):
    text = normalize(point.get("text", ""))

    details = []
    for label, patterns in requirements:
        detected = contains_any(text, patterns)
        details.append((label, detected))

    return details


RULES = [
    {
        "step": 2,
        "name": "Échec automatique sur X",
        "source": "S007",
        "requirements": [
            ("Résultat X", [r"\bx\b", r"\bcroix\b"]),
            ("Dé bleu", [r"\bbleu\b"]),
            ("Attaque manquée", [
                r"\bechec\b",
                r"\bmanqu",
                r"\brate",
            ]),
        ],
    },
    {
        "step": 2,
        "name": "Lancer des dés de défense",
        "source": "S008",
        "requirements": [
            ("Défenseur", [r"\bdefense", r"\bdefenseur"]),
            ("Lancer des dés", [
                r"\blanc",
                r"\bjet\b",
                r"\broul",
            ]),
        ],
    },
    {
        "step": 2,
        "name": "Relances des dés",
        "source": "S010",
        "requirements": [
            ("Relance", [
                r"\brelanc",
                r"\brelancem",
                r"\brelancable",
            ]),
        ],
    },
    {
        "step": 4,
        "name": "Limites des capacités SURGE",
        "source": "S015",
        "requirements": [
            ("Un usage par capacité", [
                r"\bcapacite.{0,100}une seule fois",
                r"\bcapacite.{0,100}une fois",
                r"\bchaque.{0,35}capacite.{0,100}fois",
            ]),
        ],
    },
    {
        "step": 4,
        "name": "Fatigue et SURGE",
        "source": "S016",
        "requirements": [
            ("Héros", [r"\bheros\b"]),
            ("Fatigue", [r"\bfatigue\b"]),
            ("Monstres exclus", [
                r"\bmonstre.{0,100}(?:ne peu|impossible|interdit)",
                r"\bmonstre.{0,100}pas\b",
            ]),
        ],
    },
    {
        "step": 5,
        "name": "Dégâts hors attaque",
        "source": "S022",
        "requirements": [
            ("Dégâts hors attaque", [
                r"\bhors.{0,25}attaque",
                r"\bautre.{0,35}attaque",
                r"\bnon.{0,25}attaque",
            ]),
            ("Défense impossible", [
                r"\bne peu.{0,60}defense",
                r"\bpas.{0,40}de.{0,15}defense",
                r"\bdefense.{0,50}impossible",
            ]),
        ],
    },
]


def main():
    report = json.loads(INPUT.read_text(encoding="utf-8"))
    points = report["generated_answer"]["points"]

    if len(points) != 5:
        raise ValueError(
            f"Cinq étapes attendues, {len(points)} trouvées"
        )

    lines = [
        "=== AUDIT LEXICAL DES RÈGLES CRITIQUES ===",
        "Méthode : détection d'indices textuels.",
        "Ce contrôle ne valide PAS la vérité des règles.",
        "",
    ]

    flagged = 0

    for rule in RULES:
        point = points[rule["step"] - 1]
        details = check_rule(
            point,
            rule["requirements"]
        )

        all_detected = all(ok for _, ok in details)

        if not all_detected:
            flagged += 1

        status = (
            "INDICES PRÉSENTS"
            if all_detected
            else "À EXAMINER"
        )

        lines.append(
            f"{rule['source']} | {status} | "
            f"Étape {rule['step']} | {rule['name']}"
        )

        for label, detected in details:
            lines.append(
                f"  {'OK' if detected else 'ABSENT'} : {label}"
            )

        lines.append("")

    lines.extend([
        "=== SYNTHÈSE ===",
        f"Règles examinées : {len(RULES)}",
        f"Règles signalées : {flagged}",
        "",
        "LIMITES :",
        "- Une formulation différente peut produire "
        "un faux signalement.",
        "- Des mots présents ne prouvent pas "
        "que la règle est correcte.",
        "- Le rapport ne modifie pas la réponse.",
        "- Le corpus V3 reste inchangé.",
    ])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("=== AUDIT LEXICAL COMBAT ===")
    print("Règles examinées :", len(RULES))
    print("Règles signalées :", flagged)
    print("Rapport :", OUTPUT)
    print("Aucun appel Ollama.")
    print("Corpus inchangé.")


if __name__ == "__main__":
    main()

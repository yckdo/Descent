
import json
import re
import urllib.request
from pathlib import Path

from answer_stair_ollama import (
    prepare_evidence,
    validate_answer,
)
from audit_combat_semantics import RULES, check_rule

ROOT = Path(__file__).resolve().parent

INPUT = ROOT / "validation/stair_rule_coverage_review.json"
OUTPUT = ROOT / "validation/stair_combat_revised.json"
REPORT = ROOT / "validation/stair_combat_revision_review.txt"

QUESTION = "Comment fonctionne le combat ?"
MODEL = "qwen3:8b"
URL = "http://127.0.0.1:11434/api/chat"

# Seules ces étapes seront révisées.
TARGETS = {
    2: {
        "section": "sec_0073",
        "required_sources": ["S006", "S007", "S008", "S010"],
        "focus": (
            "Expliquer le lancer des dés d'attaque et de défense, "
            "l'échec automatique sur X du dé bleu, "
            "les résultats [SHIELD] et les éventuelles relances."
        ),
    },
    4: {
        "section": "sec_0076",
        "required_sources": ["S014", "S015", "S016"],
        "focus": (
            "Expliquer les capacités [SURGE], la restriction "
            "d'une activation par capacité et par attaque, "
            "la distinction entre capacités différentes "
            "ayant le même effet, et la limite d'un seul "
            "[SURGE] inutilisé pour récupérer une fatigue "
            "chez un héros attaquant, jamais un monstre."
        ),
    },
    5: {
        "section": "sec_0077",
        "required_sources": ["S019", "S020", "S022"],
        "focus": (
            "Expliquer les boucliers, les dégâts, la défaite "
            "et l'impossibilité de lancer des dés de défense "
            "contre des dégâts subis hors d'une attaque."
        ),
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_revision_context(evidence, original):
    parts = []

    for step, target in TARGETS.items():
        point = original["points"][step - 1]

        sources = [
            item for item in evidence
            if item["section_id"] == target["section"]
        ]

        require(
            sources,
            f"Aucune source pour l'étape {step}"
        )

        available_ids = {
            item["id"] for item in sources
        }

        require(
            set(target["required_sources"]).issubset(available_ids),
            f"Sources critiques absentes pour l'étape {step}"
        )

        parts.extend([
            f"=== ÉTAPE {step} ===",
            f"Réponse actuelle : {point['text']}",
            f"Points à vérifier : {target['focus']}",
            "",
            "Sources originales :",
        ])

        for item in sources:
            parts.append(
                f"[{item['id']}] PDF p.{item['page']}\n"
                f"{item['text']}\n"
            )

    return "\n".join(parts)


def call_ollama(context):
    system = """
Tu révises une réponse sur les règles de Descent,
deuxième édition.

Réponds en français avec fidélité au manuel fourni.

CONSIGNES :
- Révise uniquement les étapes 2, 4 et 5.
- Conserve leur ordre et leur numérotation.
- Utilise exclusivement les sources fournies.
- Explique les conditions et exceptions importantes.
- À l'étape 2, explique explicitement les relances de dés
  permises par les capacités après les lancers initiaux (S010).
- À l'étape 4, distingue clairement :
  une même capacité SURGE, utilisable une fois par attaque,
  et deux capacités différentes ayant un effet identique,
  qui peuvent chacune être utilisées (S015).
- Précise qu'un héros attaquant peut dépenser au maximum
  un SURGE inutilisé pour récupérer un point de fatigue (S016).
- À l'étape 5, conserve l'interdiction de lancer des dés
  de défense contre des dégâts hors attaque (S022).
- À l'étape 2, explique explicitement les relances de dés
  permises par les capacités après les lancers initiaux (S010).
- À l'étape 4, distingue clairement :
  une même capacité SURGE, utilisable une fois par attaque,
  et deux capacités différentes ayant un effet identique,
  qui peuvent chacune être utilisées (S015).
- Précise qu'un héros attaquant peut dépenser au maximum
  un SURGE inutilisé pour récupérer un point de fatigue (S016).
- À l'étape 5, conserve l'interdiction de lancer des dés
  de défense contre des dégâts hors attaque (S022).
- Ne transforme pas les règles en simples résumés.
- N'ajoute aucune règle issue de tes connaissances.
- Emploie "réserve de dés", "jetons de dégâts",
  "figurine" et "vaincue" lorsque approprié.
- Ne mentionne pas de numéro de page dans les phrases.
- Associe chaque étape aux sources réellement utilisées.
- Ne cite jamais une source absente.

Retourne UNIQUEMENT ce JSON :

{
  "points": [
    {
      "step": 2,
      "text": "2. Explication...",
      "source_ids": ["S006", "S007"]
    },
    {
      "step": 4,
      "text": "4. Explication...",
      "source_ids": ["S014", "S015"]
    },
    {
      "step": 5,
      "text": "5. Explication...",
      "source_ids": ["S019", "S022"]
    }
  ]
}

Les identifiants dans cet exemple sont illustratifs.
Cite tous les extraits nécessaires pour justifier
les affirmations effectivement formulées.
""".strip()

    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 1900,
        },
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": context},
        ],
    }

    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request, timeout=180
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    require(
        result.get("done_reason") != "length",
        "Réponse tronquée par Ollama"
    )

    content = result.get("message", {}).get("content", "")

    require(content.strip(), "Réponse Ollama vide")

    return json.loads(content)


def main():
    previous = load(INPUT)
    original = previous["generated_answer"]

    data = prepare_evidence(QUESTION)

    require(data is not None, "Aucune preuve STAIR")
    evidence = data["evidence"]

    require(
        len(original["points"]) == 5,
        "La réponse initiale ne contient pas cinq étapes"
    )

    validate_answer(original, evidence)

    context = build_revision_context(evidence, original)
    revision = call_ollama(context)

    require(
        isinstance(revision, dict),
        "Révision JSON invalide"
    )

    revised_points = revision.get("points")

    require(
        isinstance(revised_points, list)
        and len(revised_points) == 3,
        "Trois étapes révisées attendues"
    )

    # Vérifier les numéros et éviter les doublons.
    revisions_by_step = {}

    for point in revised_points:
        step = point.get("step")

        require(
            type(step) is int and step in TARGETS,
            f"Étape inattendue : {step}"
        )
        require(
            step not in revisions_by_step,
            f"Étape dupliquée : {step}"
        )

        require(
            isinstance(point.get("text"), str)
            and re.match(
                rf"^\s*{step}\.",
                point["text"]
            ),
            f"Numérotation incorrecte : {step}"
        )

        revisions_by_step[step] = point

    require(
        set(revisions_by_step) == set(TARGETS),
        "Étapes de révision incomplètes"
    )

    # Remplacer uniquement les points 2, 4 et 5.
    merged = {
        "points": [
            dict(point)
            for point in original["points"]
        ]
    }

    for step, point in revisions_by_step.items():
        merged["points"][step - 1] = {
            "text": point["text"],
            "source_ids": point["source_ids"],
        }

    # Valider toutes les références documentaires.
    validate_answer(merged, evidence)

    # Vérifier que chaque étape révisée cite des passages
    # appartenant à sa propre section STAIR.
    evidence_by_id = {
        item["id"]: item
        for item in evidence
    }

    for step, target in TARGETS.items():
        point = merged["points"][step - 1]

        for source_id in point["source_ids"]:
            source = evidence_by_id[source_id]

            require(
                source["section_id"] == target["section"],
                f"Source hors section à l'étape {step}: "
                f"{source_id}"
            )

    # Mesurer à nouveau les indices lexicaux.
    audit = []

    for rule in RULES:
        point = merged["points"][rule["step"] - 1]
        details = check_rule(
            point,
            rule["requirements"]
        )

        audit.append({
            "source": rule["source"],
            "name": rule["name"],
            "step": rule["step"],
            "signals_present": all(
                detected for _, detected in details
            ),
            "details": [
                {"label": label, "detected": detected}
                for label, detected in details
            ],
        })

    result = {
        "question": QUESTION,
        "model": MODEL,
        "original_answer": original,
        "revised_answer": merged,
        "lexical_audit": audit,
        "semantic_validation_completed": False,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(
            result, ensure_ascii=False, indent=2
        ) + "\n",
        encoding="utf-8",
    )

    lines = [
        "=== RÉVISION DOCUMENTAIRE DU COMBAT ===",
        "",
        "Étapes révisées : 2, 4, 5",
        "Étapes conservées : 1, 3",
        "",
        "=== RÉPONSE RÉVISÉE ===",
        "",
    ]

    for point in merged["points"]:
        lines.append(point["text"])
        lines.append(
            "Sources : "
            + ", ".join(point["source_ids"])
        )
        lines.append("")

    lines.append("=== AUDIT LEXICAL APRÈS RÉVISION ===")

    for item in audit:
        status = (
            "INDICES PRÉSENTS"
            if item["signals_present"]
            else "À EXAMINER"
        )

        lines.append(
            f"{item['source']} | {status} | {item['name']}"
        )

        for detail in item["details"]:
            lines.append(
                f"  {'OK' if detail['detected'] else 'ABSENT'} "
                f": {detail['label']}"
            )

    lines.extend([
        "",
        "NOTE : la détection lexicale ne garantit pas "
        "la fidélité sémantique.",
        "Révision non validée automatiquement.",
        "Corpus V3 inchangé.",
    ])

    REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    flagged = sum(
        not item["signals_present"]
        for item in audit
    )

    print("=== RÉVISION STAIR + OLLAMA ===")
    print("Étapes révisées : 2, 4, 5")
    print("Étapes conservées : 1, 3")
    print("Règles critiques examinées :", len(audit))
    print("Règles encore signalées :", flagged)
    print("Citations : identifiants contrôlés")
    print("Rapport :", REPORT)
    print("JSON :", OUTPUT)
    print("Corpus V3 inchangé")


if __name__ == "__main__":
    main()

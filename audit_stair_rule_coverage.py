
import json
from pathlib import Path

from answer_stair_ollama import (
    prepare_evidence,
    format_context,
    call_ollama,
    validate_answer,
)

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "validation/stair_rule_coverage_review.txt"
JSON_REPORT = ROOT / "validation/stair_rule_coverage_review.json"

QUESTION = "Comment fonctionne le combat ?"

CRITICAL_RULES = [
    {
        "id": "combat_miss_x",
        "name": "Échec automatique sur X",
        "source_id": "S007",
        "section_id": "sec_0073",
    },
    {
        "id": "defense_dice",
        "name": "Utilisation des dés de défense",
        "source_id": "S008",
        "section_id": "sec_0073",
    },
    {
        "id": "reroll_dice",
        "name": "Possibilité de relancer les dés",
        "source_id": "S010",
        "section_id": "sec_0073",
    },
    {
        "id": "surge_limits",
        "name": "Restrictions des capacités SURGE",
        "source_id": "S015",
        "section_id": "sec_0076",
    },
    {
        "id": "surge_fatigue",
        "name": "Fatigue récupérable par un héros",
        "source_id": "S016",
        "section_id": "sec_0076",
    },
    {
        "id": "defense_outside_attack",
        "name": "Défense contre les dégâts hors attaque",
        "source_id": "S022",
        "section_id": "sec_0077",
    },
]


def main():
    data = prepare_evidence(QUESTION)

    if data is None:
        raise SystemExit("Aucune section STAIR trouvée.")

    evidence = data["evidence"]
    evidence_by_id = {
        item["id"]: item for item in evidence
    }

    # Vérifier que la grille d'audit désigne les bonnes
    # sources du corpus, avant toute génération.
    for rule in CRITICAL_RULES:
        source_id = rule["source_id"]

        if source_id not in evidence_by_id:
            raise ValueError(
                f"Source critique introuvable : {source_id}"
            )

        actual_section = evidence_by_id[source_id]["section_id"]

        if actual_section != rule["section_id"]:
            raise ValueError(
                f"Section incorrecte pour {source_id}: "
                f"{actual_section}"
            )

    context = format_context(evidence)
    answer = call_ollama(QUESTION, context)

    # Valide le format et les identifiants des citations.
    validate_answer(answer, evidence)

    cited_ids = {
        source_id
        for point in answer["points"]
        for source_id in point["source_ids"]
    }

    results = []

    for rule in CRITICAL_RULES:
        cited = rule["source_id"] in cited_ids

        results.append({
            **rule,
            "source_cited": cited,
            "status": (
                "source_cited"
                if cited
                else "source_not_cited"
            ),
        })

    count = sum(
        item["source_cited"] for item in results
    )

    report = {
        "question": QUESTION,
        "model": "qwen3:8b",
        "audit_type": "citation_coverage_only",
        "critical_sources_total": len(CRITICAL_RULES),
        "critical_sources_cited": count,
        "rules": results,
        "generated_answer": answer,
        "warning": (
            "Une source citée ne prouve pas que son "
            "contenu est correctement expliqué."
        ),
    }

    lines = [
        "=== AUDIT DE COUVERTURE STAIR ===",
        f"Question : {QUESTION}",
        "",
        f"Règles critiques : {len(CRITICAL_RULES)}",
        f"Sources critiques citées : {count}",
        "",
        "=== DÉTAIL ===",
    ]

    for item in results:
        status = (
            "CITÉE"
            if item["source_cited"]
            else "NON CITÉE - À EXAMINER"
        )

        lines.append(
            f"{item['source_id']} | {status} "
            f"| {item['name']}"
        )

    lines.extend([
        "",
        "=== RÉPONSE GÉNÉRÉE ===",
        "",
    ])

    for index, point in enumerate(
        answer["points"], start=1
    ):
        lines.append(f"Point {index}:")
        lines.append(point["text"])
        lines.append(
            "Sources : "
            + ", ".join(point["source_ids"])
        )
        lines.append("")

    lines.extend([
        "=== LIMITES ===",
        "La couverture des citations ne mesure pas",
        "la fidélité sémantique des affirmations.",
        "Une règle peut être expliquée sans citer",
        "l'extrait attendu, ou citée sans être expliquée.",
        "Toute anomalie nécessite une revue du texte.",
    ])

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    JSON_REPORT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8",
    )

    print("=== AUDIT DE COUVERTURE STAIR ===")
    print("Règles critiques :", len(CRITICAL_RULES))
    print("Sources critiques citées :", count)
    print(
        "Sources non citées :",
        len(CRITICAL_RULES) - count
    )

    for item in results:
        status = (
            "CITÉE"
            if item["source_cited"]
            else "NON CITÉE"
        )

        print(
            f"{item['source_id']} | "
            f"{status} | {item['name']}"
        )

    print()
    print("Rapport :", REPORT)
    print("JSON :", JSON_REPORT)
    print("Corpus V3 inchangé")


if __name__ == "__main__":
    main()

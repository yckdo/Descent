
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent

INPUT = ROOT / "validation/captures/boutique_final.json"
OUTPUT = ROOT / "validation/captures/boutique_coverage.json"

RULES = [
    {
        "id": "shared_gold",
        "name": "Or commun aux héros",
        "source": "S002",
        "patterns": [
            r"\bor\b",
            r"\b(partag|commun|collectiv)",
        ],
    },
    {
        "id": "saved_gold",
        "name": "Or conservé pour une campagne ultérieure",
        "source": "S002",
        "patterns": [
            r"\b(or|pieces d'or)\b",
            r"\b(conserv|gard|economis|epargn)",
        ],
    },
    {
        "id": "five_cards",
        "name": "Cinq cartes Boutique révélées",
        "source": "S003",
        "patterns": [
            r"\bcinq\b|\b5\b",
            r"\b(revel|devoil|retourn)",
        ],
    },
    {
        "id": "act_transition",
        "name": "Transition acte I vers acte II",
        "source": "S003",
        "patterns": [
            r"\binterlude\b",
            r"\bacte\s*(i|1)\b",
            r"\bacte\s*(ii|2)\b",
        ],
    },
    {
        "id": "affordable_purchases",
        "name": "Achats selon les moyens disponibles",
        "source": "S004",
        "patterns": [
            r"\bachet",
            r"\b(moyen|or|prix|cout)",
        ],
    },
    {
        "id": "unbought_cards",
        "name": "Cartes non achetées remélangées",
        "source": "S005",
        "patterns": [
            r"\bnon achet",
            r"\b(remelang|melang.{0,35}(?:paquet|deck)|(?:paquet|deck).{0,35}melang)",
        ],
    },
]


def normalize(text):
    text = unicodedata.normalize(
        "NFKD", text.casefold()
    )
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", text)


def main():
    capture = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    if capture.get("scenario") != "boutique":
        raise ValueError("Capture inattendue.")

    if capture.get("selected_section") != "sec_0126":
        raise ValueError("Section STAIR inattendue.")

    answer = capture["answer"]
    evidence = capture["evidence"]

    # Vérifier que les sources attendues existent réellement.
    source_ids = {
        item["id"]
        for item in evidence
    }

    for rule in RULES:
        if rule["source"] not in source_ids:
            raise ValueError(
                f"Source manquante : {rule['source']}"
            )

    text = normalize(
        " ".join(
            point["text"]
            for point in answer["points"]
        )
    )

    results = []

    print("=== AUDIT COUVERTURE : BOUTIQUE ===")
    print("Source : capture JSON réelle")
    print()

    for rule in RULES:
        detected = all(
            re.search(pattern, text)
            for pattern in rule["patterns"]
        )

        status = (
            "INDICES PRÉSENTS"
            if detected
            else "À EXAMINER"
        )

        results.append({
            "id": rule["id"],
            "name": rule["name"],
            "source_id": rule["source"],
            "lexical_signals_present": bool(detected),
        })

        print(
            f"{rule['source']} | {status} "
            f"| {rule['name']}"
        )

    flagged = sum(
        not result["lexical_signals_present"]
        for result in results
    )

    report = {
        "scenario": "boutique",
        "capture_file": str(INPUT.relative_to(ROOT)),
        "checks": results,
        "rules_checked": len(results),
        "rules_flagged": flagged,
        "semantic_validation_completed": False,
    }

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("=== BILAN ===")
    print("Règles examinées :", len(results))
    print("Règles signalées :", flagged)
    print("Rapport :", OUTPUT)
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")
    print("Validation sémantique : non effectuée.")


if __name__ == "__main__":
    main()

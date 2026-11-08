
import json
from pathlib import Path

from validate_stair_evidence import audit_evidence

ROOT = Path(__file__).resolve().parent

INPUT = ROOT / "validation/captures/boutique_consolidated.json"
OUTPUT = ROOT / "validation/captures/boutique_final.json"

# Réponse pilote rédigée et vérifiée à partir
# des extraits S002 à S005.
FINAL_POINTS = [
    {
        "text": (
            "1. Après chaque quête, les héros visitent "
            "la boutique. Le paquet Boutique dépend de "
            "l'acte en cours : les cartes de l'acte I "
            "sont utilisées jusqu'à la fin de "
            "l'Interlude, puis celles de l'acte II. "
            "Les joueurs mélangent le paquet approprié "
            "et révèlent cinq cartes Boutique."
        ),
        "source_ids": ["S003"],
    },
    {
        "text": (
            "2. Les héros choisissent les articles "
            "révélés qu'ils souhaitent acheter, dans "
            "la limite de l'or disponible. Ils peuvent "
            "en acheter plusieurs ou n'en acheter aucun."
        ),
        "source_ids": ["S004"],
    },
    {
        "text": (
            "3. Les articles achetés sont retirés de "
            "la zone de jeu commune et attribués aux "
            "héros. Les joueurs déduisent l'or dépensé "
            "sur la feuille de campagne."
        ),
        "source_ids": ["S005"],
    },
    {
        "text": (
            "4. Une fois les achats terminés, les "
            "cartes Boutique non achetées sont "
            "remélangées dans le paquet Boutique."
        ),
        "source_ids": ["S005"],
    },
    {
        "text": (
            "5. Les héros disposent d'une réserve "
            "d'or commune et peuvent répartir les "
            "équipements achetés entre eux. Ils ne "
            "sont pas obligés de dépenser tout leur "
            "or pendant la phase de campagne et "
            "peuvent le conserver pour une phase "
            "ultérieure."
        ),
        "source_ids": ["S002"],
    },
]


def main():
    data = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    if data.get("scenario") != "boutique":
        raise ValueError("Scénario inattendu.")

    if len(data["answer"]["points"]) != 8:
        raise ValueError(
            "Huit points consolidés attendus."
        )

    evidence = data["evidence"]

    evidence_by_id = {
        item["id"]: item for item in evidence
    }

    for source_id, expected_page in [
        ("S002", 20),
        ("S003", 21),
        ("S004", 21),
        ("S005", 21),
    ]:
        source = evidence_by_id.get(source_id)

        if source is None:
            raise ValueError(
                f"Source manquante : {source_id}"
            )

        if (
            source["page"] != expected_page
            or source["section_id"] != "sec_0126"
        ):
            raise ValueError(
                f"Provenance inattendue : {source_id}"
            )

    answer = {
        "points": FINAL_POINTS
    }

    audit = audit_evidence(answer, evidence)

    if not audit["valid"]:
        raise ValueError(
            f"Citations invalides : {audit['errors']}"
        )

    result = {
        "scenario": "boutique",
        "question": data["question"],
        "selected_section": "sec_0126",
        "method": "manual_documented_deduplication",
        "answer": answer,
        "evidence": evidence,
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

    print("=== FINALISATION STAIR : BOUTIQUE ===")
    print("Points avant :", len(data["answer"]["points"]))
    print("Points après :", len(FINAL_POINTS))
    print("Citations valides :", audit["valid"])
    print("Fichier :", OUTPUT)
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")


if __name__ == "__main__":
    main()


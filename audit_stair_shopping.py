
import re
import unicodedata

from answer_stair_ollama import prepare_evidence

QUESTION = "Comment fonctionne la boutique ?"

RULES = [
    {
        "source_id": "S002",
        "name": "Or commun aux héros",
        "patterns": [
            r"\bgold\b",
            r"\bshare",
        ],
    },
    {
        "source_id": "S003",
        "name": "Cinq cartes Boutique révélées",
        "patterns": [
            r"\bfive\b",
            r"\breveal",
        ],
    },
    {
        "source_id": "S003",
        "name": "Changement de paquet après l'Interlude",
        "patterns": [
            r"\binterlude\b",
            r"\bact i\b",
            r"\bact ii\b",
        ],
    },
    {
        "source_id": "S004",
        "name": "Achats selon les moyens disponibles",
        "patterns": [
            r"\bpurchase\b",
            r"\bafford\b",
        ],
    },
    {
        "source_id": "S005",
        "name": "Cartes non achetées remélangées",
        "patterns": [
            r"\bunpurchased\b",
            r"\bshuffle\b",
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
    data = prepare_evidence(QUESTION)

    if data is None:
        raise SystemExit("Aucune source STAIR.")

    sources = {
        item["id"]: item
        for item in data["evidence"]
    }

    print("=== GRILLE DOCUMENTAIRE : BOUTIQUE ===")
    print("Section :", data["selected"]["id"])
    print("Extraits :", len(sources))
    print()

    problems = 0

    for rule in RULES:
        sid = rule["source_id"]

        if sid not in sources:
            print(f"{sid} | SOURCE ABSENTE | {rule['name']}")
            problems += 1
            continue

        source = sources[sid]
        text = normalize(source["text"])

        found = all(
            re.search(pattern, text)
            for pattern in rule["patterns"]
        )

        status = (
            "DOCUMENTÉE"
            if found
            else "À EXAMINER"
        )

        if not found:
            problems += 1

        print(
            f"{sid} | {status} | "
            f"PDF p.{source['page']} | {rule['name']}"
        )

    print()
    print("=== BILAN ===")
    print("Règles examinées :", len(RULES))
    print("Problèmes documentaires :", problems)
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")

    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

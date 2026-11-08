
import re
import unicodedata

# Transcription de la réponse Boutique du test 10.37.
# Ce n'est pas une nouvelle génération Ollama.

ANSWER = """
1. Les héros visitent la boutique après chaque quête
pour voir les articles en stock. Les cartes des articles
de la boutique sont mélangées et cinq cartes sont révélées.

2. Les héros peuvent acheter autant d'articles qu'ils le
souhaitent, tant qu'ils en ont les moyens, ou aucun.

3. Les articles achetés sont ajoutés aux cartes portées
par l'un des héros. Les joueurs soustraient l'or dépensé
de leur feuille de campagne.

4. Les cartes non achetées sont remises dans le paquet
des articles de la boutique après les achats.

5. Les héros partagent collectivement leurs pièces d'or
pour acheter des équipements et peuvent les répartir
entre eux comme ils le souhaitent.
"""

RULES = [
    (
        "S002",
        "Or commun aux héros",
        [r"\bor\b", r"\b(partag|commun|collectiv)"],
    ),
    (
        "S003",
        "Cinq cartes révélées",
        [r"\bcinq\b|\b5\b", r"\b(revel|devoil)"],
    ),
    (
        "S003",
        "Transition acte I vers acte II",
        [
            r"\binterlude\b",
            r"\bacte\s*(i|1)\b",
            r"\bacte\s*(ii|2)\b",
        ],
    ),
    (
        "S004",
        "Achats selon les moyens",
        [r"\bachet", r"\b(moyen|or|prix|cout)"],
    ),
    (
        "S005",
        "Retour des cartes non achetées",
        [r"\bnon achet", r"\b(paquet|remis|remett|melang)"],
    ),
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
    text = normalize(ANSWER)
    flagged = 0

    print("=== AUDIT RÉPONSE : BOUTIQUE ===")
    print("Réponse : transcription du test 10.37")
    print()

    for source, name, patterns in RULES:
        present = all(
            re.search(pattern, text)
            for pattern in patterns
        )

        if not present:
            flagged += 1

        status = (
            "INDICES PRÉSENTS"
            if present
            else "À EXAMINER"
        )

        print(f"{source} | {status} | {name}")

    print()
    print("=== BILAN ===")
    print("Règles examinées :", len(RULES))
    print("Règles signalées :", flagged)
    print("Aucun appel Ollama.")
    print("Corpus V3 inchangé.")
    print("Validation sémantique : non effectuée.")


if __name__ == "__main__":
    main()

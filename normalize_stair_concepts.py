
import re


STOPWORDS = {
    "a", "an", "the", "is", "are", "can", "could",
    "does", "do", "what", "when", "how", "where",
    "during", "their", "his", "her", "its", "my",
    "in", "on", "of", "to", "for", "from", "with",
    "and", "or", "if", "there", "any", "get",
    "have", "has", "may", "be", "it", "that",
    "this", "which", "who", "at", "by", "you",
    "your", "not", "happens", "rules", "rule",
    "edition", "second", "descent", "journeys",
    "dark", "game", "games",
}


def normalize_word(word):
    """
    Normalisation morphologique anglaise légère.

    Ne fait aucune interprétation des règles.
    """

    word = word.lower().strip()

    if not re.fullmatch(r"[a-z]+", word):
        return ""

    if len(word) <= 3:
        return word

    # Pluriels en -ies : abilities -> ability
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"

    # Pluriels en -oes : heroes -> hero
    if word.endswith("oes") and len(word) > 4:
        return word[:-2]

    # Formes en -ing : attacking -> attack
    if word.endswith("ing") and len(word) > 5:
        root = word[:-3]

        # running -> run
        if len(root) >= 3 and root[-1] == root[-2]:
            root = root[:-1]

        return root

    # Preserve words like ranged -> range.
    if word.endswith("ged") and len(word) > 5:
        return word[:-1]

    # Formes en -ed : attacked -> attack
    if word.endswith("ed") and len(word) > 4:
        root = word[:-2]

        if len(root) >= 3 and root[-1] == root[-2]:
            root = root[:-1]

        return root

    # Pluriel simple.
    if (
        word.endswith("s")
        and not word.endswith(("ss", "us", "is"))
        and len(word) > 4
    ):
        return word[:-1]

    return word


def extract_concepts(queries, max_concepts=8):
    """
    Extrait les concepts récurrents des reformulations.

    Les mots répétés dans une même requête sont
    comptabilisés une seule fois.
    """

    from collections import Counter

    if not isinstance(queries, list):
        raise ValueError("Liste de requêtes attendue.")

    counts = Counter()

    for query in queries:
        if not isinstance(query, str):
            continue

        words = re.findall(r"[a-z]+", query.lower())

        normalized = set()

        for word in words:
            if word in STOPWORDS:
                continue

            concept = normalize_word(word)

            if concept and len(concept) > 2:
                normalized.add(concept)

        counts.update(normalized)

    return [
        concept
        for concept, count in sorted(
            counts.items(),
            key=lambda pair: (-pair[1], pair[0]),
        )[:max_concepts]
    ]

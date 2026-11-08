
import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STRUCTURE = ROOT / "data/stair/document_structure.json"

# Lexique pilote : correspondances explicites,
# limitées aux concepts déjà vérifiés.
FRENCH_ALIASES = {
    "boutique": ["shopping"],
    "achats": ["shopping"],
    "acheter": ["shopping"],
    "combat": ["combat"],
    "attaque": ["attack"],
    "deplacement": ["move", "movement"],
    "mouvement": ["move", "movement"],
    "fatigue": ["fatigue"],
    "repos": ["rest"],
    "monstres": ["monsters"],
    "seigneur": ["overlord"],
    "campagne": ["campaign"],
    "installation": ["setup"],
}

STOP_WORDS = {
    "a", "au", "aux", "avec", "comment", "dans", "de",
    "des", "du", "en", "est", "et", "fonctionne", "je",
    "la", "le", "les", "ma", "mes", "mon", "on",
    "par", "pour", "que", "quel", "quelle", "quels",
    "quelles", "qui", "se", "son", "sur", "the",
    "un", "une", "what", "when", "how", "does",
    "do", "is", "are", "can", "my", "your",
}


def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )
    return text.casefold()


def tokens(text):
    words = re.findall(r"[a-z0-9]+", normalize(text))
    return [
        word for word in words
        if word not in STOP_WORDS
    ]


def query_terms(question):
    original = tokens(question)

    # Conserver les mots originaux et ajouter
    # une variante singulière pour les pluriels
    # simples. Ne jamais remplacer l'original.
    variants = set(original)

    for word in original:
        if len(word) > 4 and word.endswith("s"):
            variants.add(word[:-1])

    expanded = set(variants)

    # Appliquer le lexique bilingue également
    # aux variantes singulières.
    for word in variants:
        expanded.update(FRENCH_ALIASES.get(word, []))

    return expanded


def title_terms(section):
    names = [section["title"]]

    names.extend(
        entry["title"]
        for entry in section["index_entries"]
    )

    return names


def rank(question, sections):
    terms = query_terms(question)
    results = []

    for section in sections:
        # Les résumés de la page 24 ne sont pas
        # prioritaires face aux règles détaillées.
        is_summary = section["kind"] == "rules_summary"

        best_score = 0
        best_title = None

        for title in title_terms(section):
            title_tokens = set(tokens(title))

            if not title_tokens:
                continue

            overlap = terms & title_tokens

            if not overlap:
                continue

            # Score de navigation lexical uniquement.
            # Il ne s'agit pas d'une probabilité.
            score = len(overlap) * 10

            if title_tokens.issubset(terms):
                score += 20

            if title_tokens == terms:
                score += 30

            if score > best_score:
                best_score = score
                best_title = title

        if best_score:
            if is_summary:
                best_score -= 5

            results.append({
                "id": section["id"],
                "title": section["title"],
                "page": section["pdf_page"],
                "kind": section["kind"],
                "matched_title": best_title,
                "score": best_score,
            })

    results.sort(
        key=lambda item: (
            -item["score"],
            item["page"],
            item["id"],
        )
    )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Routeur lexical STAIR pilote."
    )
    parser.add_argument(
        "question",
        help="Question en français ou en anglais"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Nombre maximal de sections affichées"
    )

    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top doit être supérieur à zéro")

    structure = json.loads(
        STRUCTURE.read_text(encoding="utf-8")
    )

    results = rank(
        args.question,
        structure["sections"]
    )

    print("=== ROUTAGE STAIR PILOTE ===")
    print("Question :", args.question)
    print("Méthode : titres + index + lexique contrôlé")
    print("Sections candidates :", len(results))
    print()

    if not results:
        print("Aucune correspondance lexicale.")
        print("Ne pas inventer de section.")
        return

    for position, result in enumerate(
        results[:args.top], start=1
    ):
        print(
            f"{position}. {result['id']} "
            f"| {result['title']}"
        )
        print(f"   PDF p.{result['page']}")
        print(
            f"   Correspondance : "
            f"{result['matched_title']}"
        )
        print(f"   Score lexical : {result['score']}")

        if result["kind"] == "rules_summary":
            print("   Type : résumé des règles")

        print()

    print(
        "ATTENTION : candidats non validés "
        "sémantiquement."
    )


if __name__ == "__main__":
    main()

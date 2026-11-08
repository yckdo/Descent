
import argparse
import hashlib
import json
from pathlib import Path

from route_stair_sections import rank
from retrieve_stair_section import (
    build_source_lookup,
    retrieve,
)

ROOT = Path(__file__).resolve().parent

CORPUS_PATH = ROOT / "data/normalized/descent_rulebook.json"
STRUCTURE_PATH = ROOT / "data/stair/document_structure.json"
LINKS_PATH = ROOT / "data/stair/cross_page_links.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline STAIR pilote : "
            "question -> section -> sources PDF"
        )
    )

    parser.add_argument(
        "question",
        help="Question en français ou en anglais"
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Afficher les métadonnées sans le texte intégral"
    )

    args = parser.parse_args()

    corpus = load(CORPUS_PATH)
    structure = load(STRUCTURE_PATH)
    links = load(LINKS_PATH)

    check(
        links["source"]["corpus_sha256"] == sha256(CORPUS_PATH),
        "Le corpus a changé depuis l'audit des continuités"
    )

    check(
        links["source"]["structure_sha256"]
        == sha256(STRUCTURE_PATH),
        "La structure a changé depuis l'audit des continuités"
    )

    print("=== PIPELINE STAIR PILOTE ===")
    print("Question :", args.question)
    print()

    candidates = rank(
        args.question,
        structure["sections"]
    )

    if not candidates:
        print("Aucune section candidate trouvée.")
        print("Aucune règle récupérée.")
        return

    print("=== ROUTAGE ===")
    print("Candidats :", len(candidates))

    for i, candidate in enumerate(candidates[:3], start=1):
        print(
            f"{i}. {candidate['id']} | "
            f"{candidate['title']} | "
            f"PDF p.{candidate['page']} | "
            f"score {candidate['score']}"
        )

    # Sélection provisoire du premier candidat.
    # Ce classement lexical n'est pas une validation
    # sémantique de la question.
    selected = candidates[0]

    print()
    print("=== SECTION SÉLECTIONNÉE ===")
    print("ID :", selected["id"])
    print("Titre :", selected["title"])

    lookup = build_source_lookup(corpus)

    section, blocks, continuation_count = retrieve(
        selected["id"],
        structure,
        links,
        lookup
    )

    pages = sorted({
        section["pdf_page"],
        *(block["page"] for block in blocks)
    })

    print(
        "Pages du PDF original :",
        ", ".join(map(str, pages))
    )
    print("Éléments récupérés :", len(blocks))
    print("Continuités utilisées :", continuation_count)
    print("Méthode : sélection lexicale STAIR pilote")
    print("Validation sémantique : non effectuée")

    if args.summary:
        print()
        print("=== SOURCES RÉCUPÉRÉES ===")

        for block in blocks:
            print(
                f"PDF p.{block['page']} | "
                f"{', '.join(block['source_refs'])}"
            )

        return

    print()
    print("=== CONTENU DOCUMENTAIRE ===")
    print()
    print(f"# {section['title']}")
    print(f"[Titre : PDF p.{section['pdf_page']}]")

    for block in blocks:
        print()
        print(block["text"].strip())
        print(
            f"[PDF p.{block['page']} | "
            f"Docling : {', '.join(block['source_refs'])}]"
        )

    print()
    print("=== FIN ===")
    print(
        "Les passages ci-dessus proviennent du corpus "
        "normalisé. Aucune réponse n'a été générée."
    )


if __name__ == "__main__":
    main()

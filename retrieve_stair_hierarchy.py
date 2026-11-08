
import argparse
import hashlib
import json
from collections import defaultdict
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


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_index_children(structure):
    children = defaultdict(list)

    section_ids = {
        section["id"]
        for section in structure["sections"]
    }

    for relation in structure["relations"]:
        if relation["type"] != "index_subentry":
            continue

        require(
            relation["validation_status"]
            == "validated_as_index_relation",
            "Relation d'index non validée"
        )

        parent = relation["from_section_id"]
        child = relation["to_section_id"]

        require(
            parent in section_ids and child in section_ids,
            "Relation vers une section inconnue"
        )

        require(parent != child, "Relation réflexive")

        require(
            child not in children[parent],
            "Relation d'index dupliquée"
        )

        children[parent].append(child)

    return children


def ordered_sections(root_id, children):
    """
    Parcours limité à un niveau :
    section principale + sous-entrées directes de l'index.

    Le résultat est une navigation conceptuelle et
    ne constitue pas une hiérarchie physique prouvée.
    """
    return [root_id] + children.get(root_id, [])


def main():
    parser = argparse.ArgumentParser(
        description="Récupération STAIR avec sous-entrées d'index"
    )

    parser.add_argument(
        "question",
        help="Question à router"
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Afficher les métadonnées uniquement"
    )

    parser.add_argument(
        "--no-children",
        action="store_true",
        help="Récupérer uniquement la section principale"
    )

    args = parser.parse_args()

    corpus = load(CORPUS_PATH)
    structure = load(STRUCTURE_PATH)
    cross_links = load(LINKS_PATH)

    require(
        cross_links["source"]["corpus_sha256"]
        == sha256(CORPUS_PATH),
        "Le corpus a changé depuis l'audit"
    )

    require(
        cross_links["source"]["structure_sha256"]
        == sha256(STRUCTURE_PATH),
        "La structure a changé depuis l'audit"
    )

    candidates = rank(
        args.question,
        structure["sections"]
    )

    print("=== RÉCUPÉRATION HIÉRARCHIQUE STAIR ===")
    print("Question :", args.question)

    if not candidates:
        print("Aucune section candidate.")
        return

    selected = candidates[0]
    root_id = selected["id"]

    print("Section principale :", root_id)
    print("Titre :", selected["title"])
    print("Score lexical :", selected["score"])

    children = build_index_children(structure)

    if args.no_children:
        selected_ids = [root_id]
    else:
        selected_ids = ordered_sections(root_id, children)

    require(
        len(selected_ids) == len(set(selected_ids)),
        "Sections dupliquées dans la sélection"
    )

    lookup = build_source_lookup(corpus)

    retrieved = []
    used_elements = set()

    for section_id in selected_ids:
        section, blocks, continuation_count = retrieve(
            section_id,
            structure,
            cross_links,
            lookup
        )

        # Un même élément ne doit pas apparaître deux fois
        # dans la récupération globale.
        for block in blocks:
            identity = tuple(block["source_refs"])

            require(
                identity not in used_elements,
                f"Élément récupéré deux fois : {identity}"
            )

            used_elements.add(identity)

        retrieved.append({
            "section": section,
            "blocks": blocks,
            "continuations": continuation_count,
        })

    all_pages = sorted({
        section_data["section"]["pdf_page"]
        for section_data in retrieved
    } | {
        block["page"]
        for item in retrieved
        for block in item["blocks"]
    })

    print()
    print("=== SYNTHÈSE ===")
    print("Sections récupérées :", len(retrieved))
    print(
        "Sous-entrées d'index incluses :",
        len(retrieved) - 1
    )
    print(
        "Éléments documentaires :",
        sum(len(item["blocks"]) for item in retrieved)
    )
    print(
        "Continuités entre pages :",
        sum(item["continuations"] for item in retrieved)
    )
    print(
        "Pages du PDF original :",
        ", ".join(map(str, all_pages))
    )

    print()
    print("=== SECTIONS ===")

    for position, item in enumerate(retrieved):
        section = item["section"]
        blocks = item["blocks"]

        pages = sorted({
            section["pdf_page"],
            *(block["page"] for block in blocks)
        })

        prefix = "RACINE" if position == 0 else "INDEX"

        print(
            f"{prefix} | {section['id']} "
            f"| {section['title']} "
            f"| PDF p.{','.join(map(str, pages))} "
            f"| {len(blocks)} éléments"
        )

    if args.summary:
        print()
        print("Mode résumé : aucun texte intégral affiché.")
        return

    print()
    print("=== PASSAGES DOCUMENTAIRES ===")

    for item in retrieved:
        section = item["section"]

        print()
        print("=" * 60)
        print(f"# {section['title']}")
        print(
            f"[Titre : PDF p.{section['pdf_page']}"
            f" | {', '.join(section['heading_refs'])}]"
        )

        for block in item["blocks"]:
            print()
            print(block["text"].strip())
            print(
                f"[PDF p.{block['page']} | "
                f"Docling : {', '.join(block['source_refs'])}]"
            )

    print()
    print("=== FIN ===")
    print("Navigation : relations d'index validées.")
    print("Hiérarchie physique : non encore établie.")
    print("Réponse générée par Ollama : non.")


if __name__ == "__main__":
    main()

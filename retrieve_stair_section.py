
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

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


def build_source_lookup(corpus):
    lookup = {}

    for page in corpus["pages"]:
        for element in page["elements"]:
            for ref in element["source_refs"]:
                check(
                    ref not in lookup,
                    f"Référence Docling dupliquée : {ref}"
                )
                lookup[ref] = element

    return lookup


def get_elements(refs, lookup, expected_page=None):
    result = []
    seen_elements = set()

    for ref in refs:
        check(ref in lookup, f"Source introuvable : {ref}")

        element = lookup[ref]
        identity = tuple(element["source_refs"])

        if expected_page is not None:
            check(
                element["page"] == expected_page,
                f"Page incorrecte pour {ref}"
            )

        if identity not in seen_elements:
            result.append(element)
            seen_elements.add(identity)

    return result


def retrieve(section_id, structure, links, lookup):
    sections = {
        section["id"]: section
        for section in structure["sections"]
    }

    check(
        section_id in sections,
        f"Section STAIR inconnue : {section_id}"
    )

    section = sections[section_id]

    heading = get_elements(
        section["heading_refs"],
        lookup,
        expected_page=section["pdf_page"]
    )

    check(
        len(heading) == 1,
        f"Titre non résolu de façon unique : {section_id}"
    )

    check(
        heading[0]["text"] == section["title"],
        f"Titre incohérent : {section_id}"
    )

    content = get_elements(
        section["content_refs"],
        lookup,
        expected_page=section["pdf_page"]
    )

    check(
        len(content) == section["content_element_count"],
        f"Nombre d'éléments incorrect : {section_id}"
    )

    blocks = list(content)

    cross_page_links = [
        link
        for link in links["links"]
        if link["section_id"] == section_id
    ]

    for link in cross_page_links:
        check(
            link["from_pdf_page"] == section["pdf_page"],
            f"Page source incohérente : {section_id}"
        )

        continuation = get_elements(
            link["source_refs"],
            lookup,
            expected_page=link["to_pdf_page"]
        )

        check(
            len(continuation) == link["source_element_count"],
            f"Continuation incomplète : {section_id}"
        )

        blocks.extend(continuation)

    identities = [
        tuple(block["source_refs"])
        for block in blocks
    ]

    check(
        len(identities) == len(set(identities)),
        f"Éléments récupérés en double : {section_id}"
    )

    # Exclure les éléments de pagination des passages
    # transmis au moteur de réponses.
    # Les références restent intactes dans le corpus V3.
    blocks = [
        block
        for block in blocks
        if block["label"] not in {
            "page_header",
            "page_footer",
        }
    ]

    return section, blocks, len(cross_page_links)


def show(section, blocks, continuation_count):
    pages = sorted({
        section["pdf_page"],
        *(block["page"] for block in blocks)
    })

    print("=== RÉCUPÉRATION STAIR ===")
    print("Section :", section["id"])
    print("Titre :", section["title"])
    print("Type :", section["kind"])
    print("Pages du PDF original :", ", ".join(map(str, pages)))
    print("Éléments de contenu :", len(blocks))
    print("Continuités utilisées :", continuation_count)
    print()

    grouped = defaultdict(list)

    for block in blocks:
        grouped[block["page"]].append(block)

    print(f"# {section['title']}")
    print(f"[Titre : PDF p.{section['pdf_page']}]")

    for page in sorted(grouped):
        print(f"\n--- PDF ORIGINAL : PAGE {page} ---")

        for block in grouped[page]:
            print()
            print(block["text"].strip())
            print(
                f"[PDF p.{page} | "
                f"Docling : {', '.join(block['source_refs'])}]"
            )

    print("\n=== FIN DE LA SECTION ===")


def main():
    parser = argparse.ArgumentParser(
        description="Récupérer une section STAIR par identifiant."
    )

    parser.add_argument(
        "section_id",
        help="Exemple : sec_0062"
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
        links["source"]["structure_sha256"] == sha256(STRUCTURE_PATH),
        "La structure a changé depuis l'audit des continuités"
    )

    lookup = build_source_lookup(corpus)

    section, blocks, continuation_count = retrieve(
        args.section_id,
        structure,
        links,
        lookup
    )

    show(section, blocks, continuation_count)


if __name__ == "__main__":
    main()

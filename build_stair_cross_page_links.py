
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CORPUS = ROOT / "data/normalized/descent_rulebook.json"
STRUCTURE = ROOT / "data/stair/document_structure.json"

OUTPUT = ROOT / "data/stair/cross_page_links.json"
REPORT = ROOT / "validation/stair_cross_page_links_review.txt"

# Continuités examinées manuellement.
# Chaque référence a été observée dans le diagnostic.
CONFIRMED = [
    {
        "section_id": "sec_0062",
        "section_title": "Overlord Turn in Detail",
        "heading_ref": "#/texts/347",
        "from_page": 10,
        "to_page": 11,
        "first_ref": "#/texts/353",
        "last_ref": "#/texts/374",
        "expected_elements": 9,
    },
    {
        "section_id": "sec_0126",
        "section_title": "SHOPPING",
        "heading_ref": "#/texts/755",
        "from_page": 20,
        "to_page": 21,
        "first_ref": "#/texts/759",
        "last_ref": "#/texts/762",
        "expected_elements": 4,
    },
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    corpus = load(CORPUS)
    structure = load(STRUCTURE)

    pages = {
        page["page"]: page["elements"]
        for page in corpus["pages"]
    }

    sections = {
        section["id"]: section
        for section in structure["sections"]
    }

    links = []
    report_lines = [
        "=== CONTINUITÉS DOCUMENTAIRES STAIR ===",
        "",
        "Validation fondée sur l'examen des éléments",
        "aux frontières des pages du PDF.",
        "",
    ]

    used_refs = set()

    for rule in CONFIRMED:
        sid = rule["section_id"]
        section = sections.get(sid)

        require(section is not None, f"Section absente : {sid}")

        require(
            section["title"] == rule["section_title"],
            f"Titre inattendu : {sid}"
        )

        require(
            section["pdf_page"] == rule["from_page"],
            f"Page initiale inattendue : {sid}"
        )

        require(
            rule["heading_ref"] in section["heading_refs"],
            f"Référence du titre absente : {sid}"
        )

        require(
            rule["to_page"] == rule["from_page"] + 1,
            f"Pages non consécutives : {sid}"
        )

        elements = pages.get(rule["to_page"])

        require(
            elements is not None,
            f"Page cible absente : {sid}"
        )

        # Ignorer seulement les éléments de pagination
        # avant le début de la continuation.
        meaningful = [
            element
            for element in elements
            if element["label"] not in {
                "page_header",
                "page_footer"
            }
            and element["text"].strip()
        ]

        require(
            meaningful,
            f"Page cible vide : {sid}"
        )

        selected = []

        for element in meaningful:
            # S'arrêter au premier nouveau titre.
            if element["label"] in {
                "title",
                "section_header"
            }:
                break

            selected.append(element)

        require(
            len(selected) == rule["expected_elements"],
            f"{sid}: {len(selected)} éléments trouvés, "
            f"{rule['expected_elements']} attendus"
        )

        require(
            rule["first_ref"] in selected[0]["source_refs"],
            f"Première référence incorrecte : {sid}"
        )

        require(
            rule["last_ref"] in selected[-1]["source_refs"],
            f"Dernière référence incorrecte : {sid}"
        )

        refs = [
            ref
            for element in selected
            for ref in element["source_refs"]
        ]

        require(
            len(refs) == len(set(refs)),
            f"Références dupliquées : {sid}"
        )

        require(
            not used_refs.intersection(refs),
            f"Références utilisées deux fois : {sid}"
        )

        used_refs.update(refs)

        link = {
            "type": "continues_section",
            "section_id": sid,
            "from_pdf_page": rule["from_page"],
            "to_pdf_page": rule["to_page"],
            "source_element_count": len(selected),
            "source_refs": refs,
            "validation_status": "manually_reviewed",
            "evidence": {
                "section_heading_ref": rule["heading_ref"],
                "first_continuation_ref": rule["first_ref"],
                "last_continuation_ref": rule["last_ref"],
            },
        }

        links.append(link)

        report_lines.extend([
            f"SECTION : {sid}",
            f"TITRE : {section['title']}",
            f"PAGES : {rule['from_page']} -> {rule['to_page']}",
            f"ÉLÉMENTS : {len(selected)}",
            f"RÉFÉRENCES : {len(refs)}",
            f"PREMIÈRE : {refs[0]}",
            f"DERNIÈRE : {refs[-1]}",
            "",
        ])

    require(
        len(links) == 2,
        "Deux continuités attendues"
    )

    result = {
        "schema_version": "stair-cross-page-0.1",
        "source": {
            "corpus": str(CORPUS.relative_to(ROOT)),
            "corpus_sha256": sha256(CORPUS),
            "structure": str(STRUCTURE.relative_to(ROOT)),
            "structure_sha256": sha256(STRUCTURE),
        },
        "validation": {
            "recorded_links_manually_reviewed": True,
            "all_page_boundaries_validated": False,
        },
        "links": links,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    report_lines.extend([
        "=== SYNTHÈSE ===",
        f"Continuités enregistrées : {len(links)}",
        f"Éléments supplémentaires : "
        f"{sum(link['source_element_count'] for link in links)}",
        "Corpus original modifié : non",
        "Structure initiale modifiée : non",
        "",
        "Les autres frontières restent non validées.",
    ])

    REPORT.write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8"
    )

    print("=== CONTINUITÉS STAIR ===")
    print("Continuités enregistrées :", len(links))
    print(
        "Éléments supplémentaires :",
        sum(link["source_element_count"] for link in links)
    )
    print("Références distinctes :", len(used_refs))
    print("Erreurs : 0")
    print("Fichier :", OUTPUT)
    print("Rapport :", REPORT)
    print("Corpus V3 inchangé")


if __name__ == "__main__":
    main()

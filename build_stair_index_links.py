
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data/stair/section_inventory.json"
OUTPUT = ROOT / "data/stair/index_links.json"
REPORT = ROOT / "validation/stair_index_links_review.txt"

# Variantes constatées dans le manuel et l'index.
# Aucune correspondance approximative automatique.
ALIASES = {
    (20, "campaign phase"): "The Campaign Phase",
    (11, "dice"): "The Dice",
    (6, "setup diagram"): "Setup Diagram (Four-player Game)",
}


def normalize(value):
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    inventory = load(INPUT)
    sections = inventory["sections"]
    index = inventory["conceptual_index"]

    lookup = {}
    section_by_id = {}

    for section in sections:
        key = (section["page"], normalize(section["title"]))
        lookup.setdefault(key, []).append(section)
        section_by_id[section["id"]] = section

    nodes = []
    links = []
    errors = []
    methods = Counter()

    current_parent = None

    for number, entry in enumerate(index, start=1):
        page = entry["page"]
        title = entry["title"]
        level = entry["level"]

        if level not in (0, 1):
            errors.append(f"Index {number}: niveau non pris en charge")
            continue

        key = (page, normalize(title))
        candidates = lookup.get(key, [])
        method = "exact"

        if not candidates and key in ALIASES:
            alias_key = (page, normalize(ALIASES[key]))
            candidates = lookup.get(alias_key, [])
            method = "documented_alias"

        if len(candidates) != 1:
            errors.append(
                f"Index {number}: correspondance "
                f"absente ou ambiguë : {title}, p.{page}"
            )
            continue

        section = candidates[0]
        node_id = f"idx_{number:04d}"

        node = {
            "index_id": node_id,
            "index_title": title,
            "index_page": page,
            "index_level": level,
            "section_id": section["id"],
            "section_title": section["title"],
            "heading_refs": section["heading_refs"],
            "match_method": method,
        }

        nodes.append(node)
        methods[method] += 1

        if level == 0:
            current_parent = node

        elif current_parent is None:
            errors.append(
                f"Index {number}: enfant sans parent : {title}"
            )

        else:
            links.append({
                "parent_section_id": current_parent["section_id"],
                "child_section_id": section["id"],
                "relation": "index_subentry",
                "evidence": {
                    "source": "conceptual_index",
                    "source_pdf_page": 23,
                    "parent_index_id": current_parent["index_id"],
                    "child_index_id": node_id,
                },
                "status": "proposed",
            })

    if len(sections) != 143:
        errors.append(
            f"143 sections attendues, {len(sections)} trouvées"
        )

    if len(index) != 71:
        errors.append(
            f"71 entrées attendues, {len(index)} trouvées"
        )

    if len(nodes) != 71:
        errors.append(
            f"71 correspondances attendues, {len(nodes)} trouvées"
        )

    if len(links) != 24:
        errors.append(
            f"24 relations attendues, {len(links)} trouvées"
        )

    if methods["documented_alias"] != 3:
        errors.append(
            "Trois variantes documentées attendues"
        )

    linked_sections = [node["section_id"] for node in nodes]

    if len(linked_sections) != len(set(linked_sections)):
        errors.append("Plusieurs entrées associées à une même section")

    if errors:
        for error in errors:
            print("ERREUR :", error)
        raise SystemExit(1)

    result = {
        "schema_version": "stair-index-links-0.1",
        "source_inventory": "data/stair/section_inventory.json",
        "hierarchy_validated": False,
        "index_nodes": nodes,
        "proposed_parent_child_links": links,
        "unlinked_section_ids": [
            section["id"]
            for section in sections
            if section["id"] not in set(linked_sections)
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "=== CORRESPONDANCES STAIR / INDEX ===",
        "Statut : PROPOSITIONS NON VALIDÉES",
        "",
        f"Sections totales : {len(sections)}",
        f"Entrées d'index : {len(nodes)}",
        f"Correspondances exactes : {methods['exact']}",
        f"Variantes documentées : {methods['documented_alias']}",
        f"Relations parent-enfant proposées : {len(links)}",
        f"Sections hors index : {len(result['unlinked_section_ids'])}",
        "",
        "=== VARIANTES DE TITRES ===",
    ]

    for node in nodes:
        if node["match_method"] == "documented_alias":
            lines.append(
                f"p.{node['index_page']} | "
                f"{node['index_title']} => "
                f"{node['section_title']} ({node['section_id']})"
            )

    lines.extend(["", "=== RELATIONS PROPOSÉES ==="])

    for link in links:
        parent = section_by_id[link["parent_section_id"]]
        child = section_by_id[link["child_section_id"]]

        lines.append(
            f"{parent['id']} [{parent['title']}] "
            f"=> {child['id']} [{child['title']}]"
        )

    lines.extend([
        "",
        "Ces relations proviennent exclusivement des niveaux "
        "de l'index du PDF, page 23.",
        "Aucune relation n'a encore été validée ou appliquée "
        "à la hiérarchie générale.",
    ])

    REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("=== LIENS STAIR / INDEX ===")
    print("Correspondances exactes :", methods["exact"])
    print("Variantes documentées :", methods["documented_alias"])
    print("Relations proposées :", len(links))
    print("Sections hors index :", len(result["unlinked_section_ids"]))
    print("Erreurs : 0")
    print("Rapport :", REPORT)
    print("Hiérarchie non encore validée")


if __name__ == "__main__":
    main()

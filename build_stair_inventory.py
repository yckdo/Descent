
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "data/normalized/descent_rulebook.json"
OUTPUT_DIR = ROOT / "data/stair"
REPORT = ROOT / "validation/stair_inventory_review.txt"

HEADING_LABELS = {"title", "section_header"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    corpus = load(SOURCE)

    sections = []
    errors = []
    sequential_id = 0

    for page in corpus["pages"]:
        page_number = page["page"]
        elements = page["elements"]

        headings = [
            i for i, element in enumerate(elements)
            if element["label"] in HEADING_LABELS
        ]

        for position, start in enumerate(headings):
            heading = elements[start]
            end = (
                headings[position + 1]
                if position + 1 < len(headings)
                else len(elements)
            )

            sequential_id += 1
            section_id = f"sec_{sequential_id:04d}"

            content = elements[start + 1:end]

            sections.append({
                "id": section_id,
                "title": heading["text"].strip(),
                "page": page_number,
                "heading_refs": heading["source_refs"],
                "heading_label": heading["label"],
                "element_count": len(content),
                "content_refs": [
                    ref
                    for element in content
                    for ref in element["source_refs"]
                ],
                "parent_id": None,
                "hierarchy_status": "unreviewed",
            })

            if not heading["text"].strip():
                errors.append(f"{section_id}: titre vide")

            if not heading["source_refs"]:
                errors.append(f"{section_id}: provenance absente")

    index_entries = []

    for column in corpus["conceptual_index"]["columns"]:
        for entry in column["entries"]:
            index_entries.append({
                "title": entry["title"],
                "page": entry["page"],
                "level": entry["level"],
            })

    # Les titres répétés sont conservés : une même rubrique
    # peut apparaître dans les règles et dans le résumé.
    repeated = {
        title: count
        for title, count in Counter(
            section["title"] for section in sections
        ).items()
        if count > 1
    }

    output = {
        "schema_version": "stair-inventory-0.1",
        "source": str(SOURCE.relative_to(ROOT)),
        "hierarchy_validated": False,
        "sections": sections,
        "conceptual_index": index_entries,
    }

    lines = [
        "=== INVENTAIRE DOCUMENTAIRE STAIR ===",
        "Hiérarchie : NON VALIDÉE",
        "",
        f"Sections détectées : {len(sections)}",
        f"Entrées d'index : {len(index_entries)}",
        f"Titres distincts répétés : {len(repeated)}",
        f"Erreurs : {len(errors)}",
        "",
    ]

    for section in sections:
        lines.append(
            f"{section['id']} | PDF p.{section['page']} "
            f"| {section['title']}"
        )
        lines.append(
            f"  Sources : {', '.join(section['heading_refs'])}"
        )
        lines.append(
            f"  Éléments associés : {section['element_count']}"
        )
        lines.append("")

    lines.extend([
        "=== TITRES RÉPÉTÉS ===",
        "",
    ])

    for title, count in sorted(repeated.items()):
        lines.append(f"{title} : {count} occurrences")

    lines.extend([
        "",
        "=== INDEX CONCEPTUEL ===",
        "",
    ])

    for entry in index_entries:
        lines.append(
            f"Niveau {entry['level']} | PDF p.{entry['page']} "
            f"| {entry['title']}"
        )

    lines.extend([
        "",
        "=== ERREURS ===",
        "",
    ])

    lines.extend(errors or ["Aucune erreur détectée"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / "section_inventory.json"

    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print("=== INVENTAIRE STAIR ===")
    print("Sections :", len(sections))
    print("Entrées d'index :", len(index_entries))
    print("Titres répétés :", len(repeated))
    print("Erreurs :", len(errors))
    print("Inventaire :", output_path)
    print("Rapport :", REPORT)
    print("Hiérarchie non encore validée")

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

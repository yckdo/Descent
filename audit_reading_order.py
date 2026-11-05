
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data/normalized/descent_rulebook.json"
OUTPUT = ROOT / "validation/reading_order_report.txt"


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))

    lines = [
        "=== AUDIT DE L'ORDRE DE LECTURE ===",
        "Titres et transitions du corpus normalisé V3",
        ""
    ]

    total_headings = 0

    for page in data["pages"]:
        number = page["page"]
        elements = page["elements"]

        lines.append("=" * 65)
        lines.append(f"PAGE {number} — {len(elements)} éléments")
        lines.append("=" * 65)

        for index, element in enumerate(elements):
            if element["label"] not in (
                "title",
                "section_header"
            ):
                continue

            total_headings += 1

            lines.append(
                f"\n[{index:03d}] {element['label'].upper()}"
            )
            lines.append(f"TITRE : {element['text']}")
            lines.append(
                f"SOURCE : {element['source_refs']}"
            )

            # Montrer le début du contenu suivant.
            if index + 1 < len(elements):
                following = elements[index + 1]
                excerpt = following["text"].replace("\n", " ")
                lines.append(
                    f"SUIVANT : {excerpt[:160]}"
                )
                lines.append(
                    f"RÉF. SUIVANTE : {following['source_refs']}"
                )

        lines.append("")

    lines.append("=" * 65)
    lines.append(f"TOTAL TITRES : {total_headings}")
    lines.append("Aucune modification du corpus.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print("=== AUDIT DE L'ORDRE DE LECTURE ===")
    print("Pages analysées :", len(data["pages"]))
    print("Titres trouvés :", total_headings)
    print("Rapport :", OUTPUT)
    print("Aucune modification appliquée")


if __name__ == "__main__":
    main()

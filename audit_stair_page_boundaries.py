
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "data/normalized/descent_rulebook.json"
OUTPUT = ROOT / "validation/stair_page_boundaries_review.txt"

HEADING_LABELS = {"title", "section_header"}
SKIP_LABELS = {"page_header", "page_footer"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def excerpt(text, length=220):
    return " ".join(text.split())[:length]


def meaningful(elements):
    return [
        element
        for element in elements
        if element.get("label") not in SKIP_LABELS
        and element.get("text", "").strip()
    ]


def main():
    corpus = load(SOURCE)
    pages = corpus["pages"]

    lines = [
        "=== AUDIT DES FRONTIÈRES DE PAGES STAIR ===",
        "Diagnostic uniquement : aucune continuité inférée.",
        "",
    ]

    boundaries = 0

    for first, second in zip(pages, pages[1:]):
        page_a = first["page"]
        page_b = second["page"]

        # La page 23 n'a pas de texte normalisé.
        # Une interruption dans la numérotation reste visible.
        if page_b != page_a + 1:
            lines.append(
                f"ATTENTION : saut de page {page_a} -> {page_b}"
            )
            lines.append("")

        items_a = meaningful(first["elements"])
        items_b = meaningful(second["elements"])

        if not items_a or not items_b:
            continue

        boundaries += 1

        last_a = items_a[-1]
        first_b = items_b[0]

        heading_a = [
            item for item in items_a
            if item.get("label") in HEADING_LABELS
        ]

        last_heading = heading_a[-1] if heading_a else None

        lines.append("=" * 75)
        lines.append(f"FRONTIÈRE PDF {page_a} -> {page_b}")
        lines.append("=" * 75)

        if last_heading:
            lines.append(
                f"DERNIER TITRE PAGE {page_a} : "
                f"{last_heading['text']}"
            )
            lines.append(
                f"RÉF. TITRE : {last_heading['source_refs']}"
            )

        lines.append("")
        lines.append(f"DERNIER ÉLÉMENT PAGE {page_a}")
        lines.append(f"Type : {last_a['label']}")
        lines.append(
            f"Source : {last_a['source_refs']}"
        )
        lines.append(
            f"Texte : {excerpt(last_a['text'])}"
        )

        lines.append("")
        lines.append(f"PREMIER ÉLÉMENT PAGE {page_b}")
        lines.append(f"Type : {first_b['label']}")
        lines.append(
            f"Source : {first_b['source_refs']}"
        )
        lines.append(
            f"Texte : {excerpt(first_b['text'])}"
        )

        lines.append("")

        if first_b["label"] in HEADING_LABELS:
            lines.append(
                "INDICE : la page suivante commence par un titre."
            )
        else:
            lines.append(
                "À EXAMINER : la page suivante commence "
                "par un élément non titré."
            )

        lines.append("")

    lines.extend([
        "=" * 75,
        "SYNTHÈSE",
        f"Frontières examinées : {boundaries}",
        "Continuités automatiquement approuvées : 0",
        "Corpus modifié : non",
    ])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print("=== AUDIT DES FRONTIÈRES STAIR ===")
    print("Pages textuelles :", len(pages))
    print("Frontières examinées :", boundaries)
    print("Rapport :", OUTPUT)
    print("Continuités approuvées automatiquement : 0")
    print("Corpus inchangé")


if __name__ == "__main__":
    main()

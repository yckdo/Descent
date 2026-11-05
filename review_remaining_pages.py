
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "validation/fragment_review.json"
OUTPUT = ROOT / "validation/remaining_pages_review.txt"

PAGES = (2, 5, 7, 8, 9, 11, 12, 17, 18, 19, 24)


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))

    lines = ["=== AUDIT DES PAGES RESTANTES ==="]
    total = 0

    for page in PAGES:
        findings = [
            item for item in data["findings"]
            if item["page"] == page
        ]

        total += len(findings)

        lines.append(f"\n{'=' * 60}")
        lines.append(f"PAGE {page} — {len(findings)} signalements")
        lines.append("=" * 60)

        for item in findings:
            lines.extend([
                f"\n{item['id']} [{item['suggestion']}]",
                f"SOURCE : {item['source_refs']}",
                f"TEXTE : {item['text']}",
                f"SUIVANT : {item['next_refs']}",
                f"SUITE : {item['next_text']}",
                f"RAISON : {item['reason']}"
            ])

    OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print("=== RAPPORT DES PAGES RESTANTES ===")
    print("Signalements :", total)
    print("Pages examinées :", len(PAGES))
    print("Fichier :", OUTPUT)
    print("Aucune correction appliquée")


if __name__ == "__main__":
    main()


import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "data/normalized/descent_rulebook.json"
OUTPUT = ROOT / "validation/critical_rules_review.txt"

TARGETS = {
    8: ["Move", "ADDITIONAL MOVEMENT"],
    9: ["Attack", "Use a Skill", "Rest"],
    11: ["Core Rules", "The Dice", "Equipment"],
    12: ["Combat", "LINE OF SIGHT", "2. ROLL DICE", "3. CHECK RANGE"],
    13: ["4. SPEND SURGES", "5. DEAL DAMAGE"],
    15: ["Defeated", "KNOCKED OUT", "Conditions", "Attribute Tests"],
    16: ["Monsters", "Large Monsters"],
    17: ["Lieutenants", "Familiars"],
    18: ["FAMILIARS TREATED AS FIGURES", "Terrain",
         "Obstacles", "Water", "Pit", "Lava"],
    24: ["Attack Keywords", "Conditions"],
}


def main():
    corpus = json.loads(SOURCE.read_text(encoding="utf-8"))

    lines = [
        "=== AUDIT DES REGLES CRITIQUES — CORPUS V3 ===",
        "Rapport documentaire en lecture seule.",
        "Les passages sont reproduits dans leur ordre normalise.",
        "",
    ]

    matched = set()
    reviewed_elements = 0

    for page in corpus["pages"]:
        number = page["page"]
        if number not in TARGETS:
            continue

        elements = page["elements"]
        headings = [
            (i, e)
            for i, e in enumerate(elements)
            if e.get("label") in ("title", "section_header")
        ]

        for position, (start, heading) in enumerate(headings):
            title = heading["text"].strip()
            if title not in TARGETS[number]:
                continue

            matched.add((number, title))

            end = (
                headings[position + 1][0]
                if position + 1 < len(headings)
                else len(elements)
            )

            lines.append("=" * 75)
            lines.append(f"PAGE PDF {number} | SECTION : {title}")
            lines.append("=" * 75)

            for index in range(start, end):
                item = elements[index]
                reviewed_elements += 1

                text = item.get("text", "")
                source_refs = ", ".join(item.get("source_refs", []))

                lines.append(
                    f"[{index:03d}] {item.get('label')} "
                    f"| {source_refs}"
                )
                lines.append(text)
                lines.append("")

    expected = {
        (page, title)
        for page, titles in TARGETS.items()
        for title in titles
    }

    missing = sorted(expected - matched)

    lines.append("=" * 75)
    lines.append("SYNTHESE")
    lines.append(f"Sections attendues : {len(expected)}")
    lines.append(f"Sections trouvees : {len(matched)}")
    lines.append(f"Elements presentes : {reviewed_elements}")
    lines.append(f"Sections absentes : {len(missing)}")

    for page, title in missing:
        lines.append(f"ABSENTE : page {page}, {title}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("=== AUDIT DES REGLES CRITIQUES ===")
    print("Sections attendues :", len(expected))
    print("Sections trouvees :", len(matched))
    print("Sections absentes :", len(missing))
    print("Elements presentes :", reviewed_elements)
    print("Rapport :", OUTPUT)
    print("Corpus non modifie")

    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

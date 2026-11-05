
import json
from pathlib import Path
from collections import Counter

SOURCE = Path("data/processed/descent_rulebook_en.json")
OUTPUT = Path("validation/pages_10_11_review.txt")

document = json.loads(SOURCE.read_text(encoding="utf-8"))

lines = []

for page in (10, 11):
    items = [
        item
        for item in document.get("texts", [])
        if any(
            p.get("page_no") == page
            for p in item.get("prov", [])
        )
    ]

    counts = Counter(item.get("label") for item in items)

    lines.append(f"\n{'=' * 60}")
    lines.append(f"PAGE {page}")
    lines.append(f"Éléments : {len(items)}")
    lines.append(f"Types : {dict(counts)}")
    lines.append(f"{'=' * 60}")

    for item in items:
        ref = item.get("self_ref")
        label = item.get("label")
        content = item.get("text", "")

        lines.append(f"\n{ref} [{label}]")
        lines.append(content)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8")

print("=== AUDIT PAGES 10 ET 11 ===")
print("Rapport créé :", OUTPUT)
print("Nombre de lignes :", len(lines))

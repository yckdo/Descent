
import json
import re
from pathlib import Path
from collections import Counter

SOURCE = Path("data/processed/descent_rulebook_en.json")
OUTPUT = Path("validation/low_confidence_audit.json")

PAGES = [1, 3, 6, 10, 11, 17, 23]

doc = json.loads(SOURCE.read_text(encoding="utf-8"))

report = []

for page in PAGES:
    items = [
        item for item in doc.get("texts", [])
        if any(
            prov.get("page_no") == page
            for prov in item.get("prov", [])
        )
    ]

    anomalies = []

    for item in items:
        content = item.get("text", "")
        reference = item.get("self_ref")

        # Caractères de remplacement Unicode.
        if "\ufffd" in content:
            anomalies.append({
                "reference": reference,
                "type": "replacement_character",
                "text": content
            })

        # Caractères inhabituels à examiner.
        if "口" in content:
            anomalies.append({
                "reference": reference,
                "type": "unexpected_character",
                "text": content
            })

        # Mots collés après une ponctuation.
        if re.search(r"[.!?][A-Za-z]", content):
            anomalies.append({
                "reference": reference,
                "type": "possible_missing_space",
                "text": content
            })

    report.append({
        "page": page,
        "text_elements": len(items),
        "labels": dict(Counter(
            item.get("label") for item in items
        )),
        "anomalies": anomalies,
        "status": "pending_review"
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=== AUDIT DES PAGES À FAIBLE CONFIANCE ===")

for page in report:
    print(
        f"Page {page['page']} : "
        f"{page['text_elements']} éléments, "
        f"{len(page['anomalies'])} anomalie(s)"
    )

print("\nRapport :", OUTPUT)


import json
import re
from pathlib import Path
from collections import Counter

doc = json.loads(
    Path("data/processed/descent_rulebook_en.json")
    .read_text(encoding="utf-8")
)

index = json.loads(
    Path("data/reference/index_page23.json")
    .read_text(encoding="utf-8")
)

def clean(text):
    text = text.replace("\ufffd", "")
    text = re.sub(r"\.{2,}", " ", text)
    return " ".join(text.split())

tables = {
    table["self_ref"]: table
    for table in doc["tables"]
    if any(p.get("page_no") == 23 for p in table.get("prov", []))
}

results = []

for column in index["columns"]:
    table_ref = f"#/tables/{column['column'] - 1}"
    table = tables[table_ref]
    cells = table["data"]["table_cells"]

    rows = {}

    for cell in cells:
        row = cell["start_row_offset_idx"]
        col = cell["start_col_offset_idx"]
        rows.setdefault(row, []).append((col, clean(cell.get("text", ""))))

    for entry in column["entries"]:
        title = entry["title"]
        page = str(entry["page"])

        status = "REVIEW"
        evidence = None

        for row_number, row_cells in rows.items():
            combined = " ".join(
                text for _, text in sorted(row_cells)
            )

            # Comparaison du titre entier, sans accepter
            # une simple sous-chaîne d'un autre titre.
            pattern = (
                r"(?<!\w)"
                + re.escape(title)
                + r"(?!\w)"
            )

            if not re.search(pattern, combined, re.IGNORECASE):
                continue

            # Vérifier que le numéro est présent après le titre.
            match = re.search(pattern, combined, re.IGNORECASE)
            following = combined[match.end():]

            if re.search(r"(?<!\d)" + re.escape(page) + r"(?!\d)", following):
                status = "MATCH" if len(row_cells) == 1 else "RECONSTRUCTED"
                evidence = f"{table_ref}, ligne {row_number}: {combined}"
                break

        results.append({
            "title": title,
            "page": entry["page"],
            "status": status,
            "evidence": evidence,
        })

print("=== CONTRÔLE DES PAGES DE L'INDEX ===")

counts = Counter(r["status"] for r in results)

for status in ("MATCH", "RECONSTRUCTED", "REVIEW"):
    print(f"{status} : {counts[status]}")

print("\nENTRÉES À EXAMINER :")

for entry in results:
    if entry["status"] == "REVIEW":
        print(f"- {entry['title']} → page {entry['page']}")

print("\nTotal :", len(results))

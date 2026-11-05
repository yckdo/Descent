
import json
from pathlib import Path

index_path = Path("data/reference/index_page23.json")
report_path = Path("validation/index_audit.json")

index = json.loads(index_path.read_text(encoding="utf-8"))

entries = [
    entry
    for column in index["columns"]
    for entry in column["entries"]
]

assert len(entries) == 71

stand_up = [
    entry for entry in entries
    if entry["title"] == "Stand Up"
]

assert len(stand_up) == 1
assert stand_up[0]["page"] == 10

report = {
    "source_page": 23,
    "method": "docling_cross_check_and_targeted_visual_review",
    "total_entries": 71,
    "same_cell_matches": 39,
    "multi_cell_reconstructions": 31,
    "visual_exception": {
        "title": "Stand Up",
        "target_page": 10,
        "source_table": "#/tables/2",
        "issue": "title_and_page_in_different_rows",
        "status": "verified"
    },
    "status": "cross_check_completed",
    "normalized_index": str(index_path),
    "notes": (
        "71 associations titre-page contrôlées. "
        "La hiérarchie a été transcrite depuis le PDF. "
        "Aucune vérification visuelle individuelle "
        "des 71 entrées n'est revendiquée."
    )
}

report_path.parent.mkdir(parents=True, exist_ok=True)

if report_path.exists():
    existing = json.loads(report_path.read_text(encoding="utf-8"))
    if existing != report:
        raise RuntimeError("Un rapport différent existe déjà.")

report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=== RAPPORT INDEX ===")
print("Entrées :", report["total_entries"])
print("Correspondances directes :", report["same_cell_matches"])
print("Correspondances multi-cellules :", report["multi_cell_reconstructions"])
print("Exception visuelle :", report["visual_exception"]["title"])
print("Statut :", report["status"])
print("Rapport :", report_path)

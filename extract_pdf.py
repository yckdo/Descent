
from pathlib import Path
import json

from docling.document_converter import DocumentConverter


# ==================================================
# 1. CONFIGURATION
# ==================================================

source = Path("data/raw/descent_rulebook_en.pdf")
output = Path("data/processed")

output.mkdir(parents=True, exist_ok=True)

markdown_path = output / "descent_rulebook_en.md"
json_path = output / "descent_rulebook_en.json"
report_path = output / "descent_rulebook_en_report.json"


# ==================================================
# 2. INITIALISATION DE DOCLING
# ==================================================

print("\n=== INITIALISATION DOCLING ===")

if not source.is_file():
    raise FileNotFoundError(f"PDF introuvable : {source}")

converter = DocumentConverter()


# ==================================================
# 3. EXTRACTION DU PDF
# ==================================================

print("\n=== EXTRACTION PDF ===")
print("Source :", source)

result = converter.convert(source)

print("Statut :", result.status)
print("Nombre d'erreurs :", len(result.errors))


# ==================================================
# 4. CONTROLES NATIFS DOCLING
# ==================================================

print("\n=== VALIDATION DOCLING ===")

confidence = result.confidence

report = {
    "source": str(source),
    "status": str(result.status),
    "errors": [str(error) for error in result.errors],
    "confidence": None,
}

if confidence is not None:

    print("Qualité moyenne :", confidence.mean_grade)
    print("Qualité minimale :", confidence.low_grade)

    confidence_data = confidence.model_dump(mode="json")
    report["confidence"] = confidence_data

    print("\nRapport de confiance :")
    print(json.dumps(confidence_data, indent=2, ensure_ascii=False))

else:
    print("Aucun score de confiance disponible.")

# Sauvegarder le rapport
report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("\nRapport enregistré :", report_path)


# ==================================================
# 5. RECUPERATION DU DOCUMENT
# ==================================================

if result.document is None:
    raise RuntimeError(
        "Docling n'a produit aucun document exploitable."
    )

document = result.document


# ==================================================
# 6. EXPORT MARKDOWN
# ==================================================

print("\n=== EXPORT MARKDOWN ===")

markdown = document.export_to_markdown()

markdown_path.write_text(
    markdown,
    encoding="utf-8",
)

print("Markdown enregistré :", markdown_path)


# ==================================================
# 7. EXPORT JSON
# ==================================================

print("\n=== EXPORT JSON ===")

json_data = document.export_to_dict()

json_path.write_text(
    json.dumps(json_data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("JSON enregistré :", json_path)


# ==================================================
# 8. STATISTIQUES
# ==================================================

print("\n=== STATISTIQUES ===")

print("Pages :", len(document.pages))
print("Éléments textuels :", len(document.texts))
print("Tableaux :", len(document.tables))
print("Images :", len(document.pictures))


# ==================================================
# 9. FIN
# ==================================================

print("\n=== EXTRACTION TERMINEE ===")
print("PDF :", source)
print("Markdown :", markdown_path)
print("JSON :", json_path)
print("Rapport qualité :", report_path)

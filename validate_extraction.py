
from pathlib import Path
from collections import Counter
from html import unescape
import json
import re


# ==========================================
# 1. CONFIGURATION
# ==========================================

BASE = Path("data/processed")
PDF_JSON = BASE / "descent_rulebook_en.json"
MARKDOWN = BASE / "descent_rulebook_en.md"
DOCLING_REPORT = BASE / "descent_rulebook_en_report.json"

OUTPUT_DIR = Path("validation")
OUTPUT_FILE = OUTPUT_DIR / "report.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2. CHARGEMENT DES DONNEES
# ==========================================

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


document = load_json(PDF_JSON)
report = load_json(DOCLING_REPORT)
markdown = MARKDOWN.read_text(encoding="utf-8")

page_count = len(document.get("pages", {}))
anomalies = []


# ==========================================
# 3. ENREGISTREMENT DES ANOMALIES
# ==========================================

def add_anomaly(category, severity, message, page=None, ref=None):
    anomalies.append({
        "category": category,
        "severity": severity,
        "page": page,
        "reference": ref,
        "message": message,
    })


# ==========================================
# 4. CONTROLE DU STATUT DOCLING
# ==========================================

status = report.get("status", "")

if not status.endswith("SUCCESS") or "PARTIAL_SUCCESS" in status:
    add_anomaly(
        "conversion",
        "blocking",
        f"Statut de conversion : {status}"
    )

if report.get("errors"):
    add_anomaly(
        "conversion",
        "review",
        "Docling a signalé des erreurs de conversion."
    )


# ==========================================
# 5. CONTROLE DE LA COUVERTURE
# ==========================================

counts = Counter()

for item in document.get("texts", []):
    for prov in item.get("prov", []):
        page = prov.get("page_no")
        if isinstance(page, int):
            counts[page] += 1

for page in range(1, page_count + 1):
    if counts[page] == 0:
        add_anomaly(
            "coverage",
            "review",
            "Aucun élément textuel sur cette page.",
            page=page
        )


# ==========================================
# 6. SCORES NATIFS DOCLING
# ==========================================

confidence = report.get("confidence") or {}
page_scores = confidence.get("pages") or {}

for page_str, scores in page_scores.items():
    page = int(page_str)

    if scores.get("low_grade") == "poor":
        add_anomaly(
            "confidence",
            "review",
            "Docling attribue la note POOR à cette page.",
            page=page
        )

    elif scores.get("low_grade") == "fair":
        add_anomaly(
            "confidence",
            "review",
            "Docling attribue la note FAIR à cette page.",
            page=page
        )


# ==========================================
# 7. COMPARAISON DES TITRES
# ==========================================

def normalize_title(value):
    value = unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


markdown_normalized = normalize_title(markdown)

titles = [
    item for item in document.get("texts", [])
    if item.get("label") in ("title", "section_header")
]

for item in titles:
    title = normalize_title(item.get("text", ""))

    if title and title not in markdown_normalized:
        prov = item.get("prov") or []
        page = prov[0].get("page_no") if prov else None

        add_anomaly(
            "heading",
            "review",
            f"Titre absent du Markdown : {item.get('text')}",
            page=page,
            ref=item.get("self_ref")
        )


# ==========================================
# 8. CARACTERES SUSPECTS
# ==========================================

for item in document.get("texts", []):
    text = item.get("text", "")
    prov = item.get("prov") or []
    page = prov[0].get("page_no") if prov else None

    if "\ufffd" in text:
        add_anomaly(
            "encoding",
            "review",
            "Caractère de remplacement Unicode détecté.",
            page=page,
            ref=item.get("self_ref")
        )

    if re.search(r"\born\b", text, flags=re.IGNORECASE):
        add_anomaly(
            "game_symbol",
            "review",
            "Symbole de jeu potentiellement mal extrait : orn.",
            page=page,
            ref=item.get("self_ref")
        )


# ==========================================
# 9. CARACTERES SUSPECTS DANS LES TABLEAUX
# ==========================================

for table in document.get("tables", []):
    prov = table.get("prov") or []
    page = prov[0].get("page_no") if prov else None

    cells = (table.get("data") or {}).get("table_cells") or []

    suspicious = sum(
        "\ufffd" in cell.get("text", "")
        for cell in cells
    )

    if suspicious:
        add_anomaly(
            "table_encoding",
            "review",
            f"{suspicious} cellule(s) contiennent des caractères suspects.",
            page=page,
            ref=table.get("self_ref")
        )


# ==========================================
# 10. VERIFICATION DES PROVENANCES
# ==========================================

for category in ("texts", "tables", "pictures"):
    for item in document.get(category, []):
        prov = item.get("prov") or []

        if not prov:
            add_anomaly(
                "provenance",
                "review",
                "Aucune provenance disponible.",
                ref=item.get("self_ref")
            )
            continue

        for source in prov:
            page = source.get("page_no")

            if not isinstance(page, int) or not (1 <= page <= page_count):
                add_anomaly(
                    "provenance",
                    "blocking",
                    f"Numéro de page invalide : {page}",
                    ref=item.get("self_ref")
                )


# ==========================================
# 11. DECISION DE VALIDATION
# ==========================================

severity_counts = Counter(
    item["severity"] for item in anomalies
)

if severity_counts["blocking"]:
    validation_status = "rejected"
elif severity_counts["review"]:
    validation_status = "review"
else:
    validation_status = "automated_checks_passed"


# ==========================================
# 12. RAPPORT FINAL
# ==========================================

result = {
    "document": "descent_rulebook_en",
    "validation_status": validation_status,
    "checks": {
        "page_count": page_count,
        "text_elements": len(document.get("texts", [])),
        "titles": len(titles),
        "tables": len(document.get("tables", [])),
        "pictures": len(document.get("pictures", [])),
    },
    "anomaly_counts": dict(severity_counts),
    "anomalies": anomalies,
    "note": (
        "Les contrôles automatiques ne prouvent pas "
        "la fidélité intégrale au PDF original."
    ),
}

OUTPUT_FILE.write_text(
    json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
    encoding="utf-8",
)

print("\n=== VALIDATION DOCUMENTAIRE ===")
print("Pages :", page_count)
print("Titres :", len(titles))
print("Anomalies :", len(anomalies))
print("Bloquantes :", severity_counts["blocking"])
print("À vérifier :", severity_counts["review"])
print("Statut :", validation_status)
print("Rapport :", OUTPUT_FILE)

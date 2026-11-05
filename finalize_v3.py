
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NORMALIZED = ROOT / "data/normalized"
VALIDATION = ROOT / "validation"

FILES = {
    "corpus_json": NORMALIZED / "descent_rulebook.json",
    "corpus_markdown": NORMALIZED / "descent_rulebook.md",
    "corrections": VALIDATION / "text_corrections.json",
}

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    corpus = load(FILES["corpus_json"])
    corrections = load(FILES["corrections"])
    source = load(
        ROOT / "data/processed/descent_rulebook_en.json"
    )

    elements = [
        element
        for page in corpus["pages"]
        for element in page["elements"]
    ]

    retained = [
        ref
        for element in elements
        for ref in element["source_refs"]
    ]

    excluded = {
        ref
        for op in corrections["exclusions"]
        for ref in op["references"]
    }

    original = {
        item["self_ref"]
        for item in source["texts"]
    }

    columns = corpus["conceptual_index"]["columns"]
    index_count = sum(
        len(c if isinstance(c, list) else c["entries"])
        for c in columns
    )

    checks = {
        "source_elements": len(original) == 919,
        "normalized_elements": len(elements) == 658,
        "excluded_refs": len(excluded) == 180,
        "retained_refs": len(retained) == 739,
        "reference_conservation": (
            set(retained) == original - excluded
            and len(retained) == len(set(retained))
        ),
        "joins": len(corrections["joins"]) == 42,
        "relabels": len(corrections["relabels"]) == 6,
        "replacements": len(corrections["replacements"]) == 3,
        "index_entries": index_count == 71,
        "index_columns": len(columns) == 3,
        "index_source_page": (
            corpus["conceptual_index"]["source_page"] == 23
        ),
    }

    failures = [
        name for name, passed in checks.items()
        if not passed
    ]

    if failures:
        raise SystemExit(
            "ÉCHEC DE VALIDATION : " + ", ".join(failures)
        )

    hashes = {
        name: sha256(path)
        for name, path in FILES.items()
    }

    report = {
        "document": "Descent: Journeys in the Dark — Second Edition",
        "release": "corpus-v3",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": "structurally_validated",
        "source_elements": len(original),
        "normalized_elements": len(elements),
        "retained_references": len(retained),
        "excluded_references": len(excluded),
        "joins": len(corrections["joins"]),
        "relabels": len(corrections["relabels"]),
        "text_replacements": len(corrections["replacements"]),
        "verified_symbols": 77,
        "text_pages": len(corpus["pages"]),
        "index_entries": index_count,
        "index_source_pdf_page": 23,
        "checks": checks,
        "sha256": hashes,
        "known_limitations": [
            "Text-only MVP: figures and card artwork are not interpreted.",
            "Original printed typo 'quite' on page 19 is preserved.",
            "Some punctuation and spacing require further visual checks.",
            "Reading order and semantic fidelity are not fully proven by automated checks.",
            "Original PDF and extracted full text are not intended for public distribution.",
        ],
    }

    VALIDATION.mkdir(parents=True, exist_ok=True)

    json_path = VALIDATION / "corpus_validation_v3.json"
    md_path = VALIDATION / "corpus_validation_v3.md"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Descent V2 — Validation documentaire V3",
        "",
        f"Statut : `{report['status']}`",
        "",
        "## Résultats",
        "",
        f"- Éléments sources : {len(original)}",
        f"- Éléments normalisés : {len(elements)}",
        f"- Références conservées : {len(retained)}",
        f"- Références exclues : {len(excluded)}",
        f"- Fusions : {len(corrections['joins'])}",
        f"- Reclassements : {len(corrections['relabels'])}",
        f"- Corrections textuelles : {len(corrections['replacements'])}",
        "- Pictogrammes vérifiés : 77",
        f"- Index conceptuel : {index_count} entrées, page PDF 23",
        "",
        "## Contrôles",
        "",
    ]

    lines.extend(
        f"- {name} : {'OK' if passed else 'ÉCHEC'}"
        for name, passed in checks.items()
    )

    lines.extend([
        "",
        "## Empreintes SHA-256",
        "",
    ])

    lines.extend(
        f"- `{name}` : `{value}`"
        for name, value in hashes.items()
    )

    lines.extend([
        "",
        "## Limites connues",
        "",
    ])

    lines.extend(
        f"- {limitation}"
        for limitation in report["known_limitations"]
    )

    lines.extend([
        "",
        "Le corpus intégral reste stocké localement.",
        "La structuration STAIR et les tests Ollama restent à réaliser.",
        "",
    ])

    md_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=== VALIDATION DOCUMENTAIRE V3 ===")
    print("Contrôles réussis :", len(checks))
    print("Erreurs : 0")
    print("Rapport :", md_path)
    print("Manifest :", json_path)
    print("Empreintes SHA-256 calculées")
    print("Corpus intégral non publié")

if __name__ == "__main__":
    main()

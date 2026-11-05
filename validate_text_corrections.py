
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent

DOCLING = ROOT / "data/processed/descent_rulebook_en.json"
CORRECTIONS = ROOT / "validation/text_corrections.json"
SYMBOL_AUDIT = ROOT / "validation/symbol_audit.json"
SYMBOLS = ROOT / "data/reference/symbols.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def page_of(item):
    return {
        p["page_no"]
        for p in item.get("prov", [])
        if "page_no" in p
    }


def main():
    doc = load(DOCLING)
    corrections = load(CORRECTIONS)
    audit = load(SYMBOL_AUDIT)
    symbols = load(SYMBOLS)["symbols"]

    texts = {
        item["self_ref"]: item
        for item in doc["texts"]
    }

    errors = []
    warnings = []
    usage = defaultdict(list)

    valid_statuses = {"approved", "visual_reviewed"}

    def check_ref(ref, page, operation):
        if ref not in texts:
            errors.append(f"{operation}: référence inconnue {ref}")
            return False

        if page not in page_of(texts[ref]):
            errors.append(
                f"{operation}: page incorrecte pour {ref}"
            )

        return True

    def check_status(operation, name):
        if operation.get("status") not in valid_statuses:
            warnings.append(
                f"{name}: {operation.get('status')}"
            )

    # ------------------------------------------------------
    # Exclusions
    # ------------------------------------------------------

    for i, operation in enumerate(corrections["exclusions"]):
        name = f"exclusions[{i}]"
        check_status(operation, name)

        for ref in operation["references"]:
            if check_ref(ref, operation["page"], name):
                usage[ref].append("exclude")

    # ------------------------------------------------------
    # Fusions
    # ------------------------------------------------------

    positions = {
        item["self_ref"]: i
        for i, item in enumerate(doc["texts"])
    }

    for i, operation in enumerate(corrections["joins"]):
        name = f"joins[{i}]"
        check_status(operation, name)

        refs = operation["references"]

        if len(refs) < 2:
            errors.append(f"{name}: fusion trop courte")

        if len(refs) != len(set(refs)):
            errors.append(f"{name}: références répétées")

        indexes = []

        for ref in refs:
            if check_ref(ref, operation["page"], name):
                indexes.append(positions[ref])
                usage[ref].append("join")

        if len(indexes) == len(refs) and indexes:
            expected = list(
                range(indexes[0], indexes[0] + len(indexes))
            )
            if indexes != expected:
                errors.append(f"{name}: fusion non contiguë")

    # ------------------------------------------------------
    # Reconstituer le texte après remplacement des symboles
    # ------------------------------------------------------

    symbols_by_ref = defaultdict(list)

    if len(audit) != 77:
        errors.append(
            f"77 pictogrammes attendus, {len(audit)} trouvés"
        )

    for entry in audit:
        ref = entry["reference"]
        name = entry["id"]

        if not check_ref(ref, entry.get("page"), name):
            continue

        if entry["status"] != "verified":
            errors.append(f"{name}: pictogramme non vérifié")

        if entry["expected_symbol"] not in symbols:
            errors.append(f"{name}: symbole inconnu")

        start = entry["char_start"]
        end = entry["char_end"]
        source = texts[ref]["text"]

        if source[start:end] != entry["detected"]:
            errors.append(f"{name}: position incorrecte")

        symbols_by_ref[ref].append(entry)

    corrected_texts = {}

    for ref, item in texts.items():
        content = item.get("text", "")
        original = content
        last_start = len(content)

        for entry in sorted(
            symbols_by_ref.get(ref, []),
            key=lambda x: x["char_start"],
            reverse=True
        ):
            start = entry["char_start"]
            end = entry["char_end"]

            if end > last_start:
                errors.append(
                    f"{ref}: pictogrammes chevauchants"
                )
                continue

            last_start = start

            replacement = f"[{entry['expected_symbol']}]"

            if (
                entry["expected_symbol"] == "SURGE"
                and original[end:].startswith("results")
            ):
                replacement += " "

            content = (
                content[:start]
                + replacement
                + content[end:]
            )

        corrected_texts[ref] = content

    # ------------------------------------------------------
    # Remplacements textuels, après les pictogrammes
    # ------------------------------------------------------

    for i, operation in enumerate(corrections["replacements"]):
        name = f"replacements[{i}]"
        check_status(operation, name)

        ref = operation["reference"]

        if not check_ref(ref, operation["page"], name):
            continue

        usage[ref].append("replace")

        old = operation["old"]
        new = operation["new"]

        if corrected_texts[ref].count(old) != 1:
            errors.append(
                f"{name}: texte à remplacer absent ou ambigu"
            )
            continue

        corrected_texts[ref] = corrected_texts[ref].replace(
            old, new, 1
        )

    # ------------------------------------------------------
    # Reclassements de titres
    # ------------------------------------------------------

    for i, operation in enumerate(corrections.get("relabels", [])):
        name = f"relabels[{i}]"
        check_status(operation, name)

        ref = operation["reference"]

        if not check_ref(ref, operation["page"], name):
            continue

        usage[ref].append("relabel")

        if texts[ref].get("label") != operation["old_label"]:
            errors.append(
                f"{name}: étiquette Docling inattendue"
            )

    # ------------------------------------------------------
    # Titre de couverture
    # ------------------------------------------------------

    cover = corrections.get("cover_title")

    if cover:
        check_status(cover, "cover_title")
        check_ref(
            cover["reference"],
            cover["page"],
            "cover_title"
        )

    # ------------------------------------------------------
    # Conflits
    # ------------------------------------------------------

    for ref, operations in usage.items():
        if operations.count("exclude") > 1:
            errors.append(f"{ref}: exclusion répétée")

        if "exclude" in operations and len(operations) > 1:
            errors.append(
                f"{ref}: élément exclu et utilisé ailleurs"
            )

        if operations.count("join") > 1:
            errors.append(
                f"{ref}: plusieurs fusions incompatibles"
            )

        if operations.count("replace") > 1:
            errors.append(
                f"{ref}: plusieurs remplacements à examiner"
            )

    # ------------------------------------------------------
    # Rapport
    # ------------------------------------------------------

    excluded_refs = {
        ref
        for operation in corrections["exclusions"]
        for ref in operation["references"]
    }

    print("=== CONTRÔLE DES CORRECTIONS V2 ===")
    print("Groupes d'exclusion :", len(corrections["exclusions"]))
    print("Références exclues :", len(excluded_refs))
    print("Remplacements :", len(corrections["replacements"]))
    print("Fusions :", len(corrections["joins"]))
    print("Reclassements :", len(corrections.get("relabels", [])))
    print("Pictogrammes vérifiés :", len(audit))
    print("Erreurs :", len(errors))
    print("Opérations à examiner :", len(warnings))

    for error in errors:
        print("ERREUR :", error)

    for warning in warnings:
        print("À EXAMINER :", warning)

    if errors or warnings:
        raise SystemExit(1)

    print("Registre cohérent avec l'ordre de normalisation")


if __name__ == "__main__":
    main()

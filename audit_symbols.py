
import json
import re
from pathlib import Path
from collections import Counter

SOURCE = Path("data/processed/descent_rulebook_en.json")
OUTPUT = Path("validation/symbol_audit.json")

# Faux positifs connus : mots anglais contenant "orn"
KNOWN_WORDS = {
    "corner",
    "corners",
    "thornberg",
}

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    document = load_json(SOURCE)

    # Charger l'audit existant sans perdre les validations.
    existing = load_json(OUTPUT) if OUTPUT.exists() else []

    # Clé stable fondée sur la référence et la position textuelle.
    existing_by_key = {
        (
            item.get("reference"),
            item.get("char_start"),
            item.get("char_end"),
        ): item
        for item in existing
    }

    next_number = max(
        (
            int(item["id"].split("_")[-1])
            for item in existing
            if re.fullmatch(r"symbol_\d+", item.get("id", ""))
        ),
        default=0,
    ) + 1

    audit = []
    new_occurrences = 0

    for item in document.get("texts", []):
        text = item.get("text", "")
        reference = item.get("self_ref")
        provenance = item.get("prov") or []
        page = provenance[0].get("page_no") if provenance else None

        for match in re.finditer(r"orn", text, re.IGNORECASE):
            start, end = match.span()

            # Identifier le mot contenant éventuellement "orn".
            left = start
            right = end

            while left > 0 and text[left - 1].isalpha():
                left -= 1

            while right < len(text) and text[right].isalpha():
                right += 1

            word = text[left:right].lower()

            # Ignorer les mots anglais déjà identifiés.
            if word in KNOWN_WORDS:
                continue

            # On conserve les "orn" isolés et les cas suspects
            # comme "ornresults".
            if word != "orn" and not word.startswith("orn"):
                continue

            key = (reference, start, end)

            if key in existing_by_key:
                entry = existing_by_key[key].copy()
            else:
                entry = {
                    "id": f"symbol_{next_number:04d}",
                    "expected_symbol": None,
                    "status": "pending_review",
                    "evidence": None,
                }
                next_number += 1
                new_occurrences += 1

            entry.update({
                "page": page,
                "reference": reference,
                "char_start": start,
                "char_end": end,
                "paragraph": text,
                "detected": match.group(),
            })

            audit.append(entry)

    # Vérifier les identifiants.
    ids = [entry["id"] for entry in audit]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Identifiants d'audit en doublon.")

    # Ne pas perdre silencieusement des entrées existantes.
    audit_keys = {
        (e["reference"], e["char_start"], e["char_end"])
        for e in audit
    }

    missing_existing = [
        e["id"]
        for e in existing
        if (e.get("reference"), e.get("char_start"), e.get("char_end"))
        not in audit_keys
    ]

    if missing_existing:
        raise RuntimeError(
            "Certaines anciennes entrées ne sont plus détectées : "
            + ", ".join(missing_existing)
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Sauvegarde de sécurité avant remplacement.
    if OUTPUT.exists():
        backup = OUTPUT.with_suffix(".json.bak")
        backup.write_bytes(OUTPUT.read_bytes())

    OUTPUT.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pages = Counter(entry["page"] for entry in audit)

    print("\n=== AUDIT DES PICTOGRAMMES ===")
    print("Occurrences :", len(audit))
    print("Nouvelles occurrences :", new_occurrences)
    print("Pages concernées :", len(pages))

    for page, count in sorted(pages.items()):
        print(f"Page {page} : {count}")

    print("\nStatuts :")
    for status, count in Counter(
        entry["status"] for entry in audit
    ).items():
        print(f"  {status} : {count}")

    print("\nRapport :", OUTPUT)


if __name__ == "__main__":
    main()

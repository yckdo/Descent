
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DOCLING = ROOT / "data/processed/descent_rulebook_en.json"
REGISTER = ROOT / "validation/text_corrections.json"
SYMBOL_AUDIT = ROOT / "validation/symbol_audit.json"
BACKUP = ROOT / "validation/text_corrections.before_8_93.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def refs(start, end):
    return [f"#/texts/{n}" for n in range(start, end + 1)]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def page_of(item):
    pages = {
        p["page_no"]
        for p in item.get("prov", [])
        if "page_no" in p
    }
    require(len(pages) == 1, f"Page ambiguë : {item['self_ref']}")
    return next(iter(pages))


def main():
    document = load(DOCLING)
    register = load(REGISTER)
    symbol_audit = load(SYMBOL_AUDIT)

    by_ref = {
        item["self_ref"]: item
        for item in document["texts"]
    }

    new_exclusions = [
        {
            "page": 14,
            "references": (
                refs(489, 490)
                + refs(494, 499)
                + refs(501, 504)
                + ["#/texts/506", "#/texts/508"]
                + refs(509, 511)
            ),
            "reason": (
                "Repères graphiques et OCR interne aux cartes "
                "de l'exemple de combat. Les cinq explications "
                "et le calcul de dégâts sont préservés."
            ),
            "status": "approved"
        },
        {
            "page": 16,
            "references": refs(565, 579),
            "reason": (
                "Repères numérotés et OCR parasite de "
                "Monster Card Anatomy. Les descriptions "
                "rédigées du manuel sont préservées."
            ),
            "status": "approved"
        },
        {
            "page": 21,
            "references": refs(779, 811),
            "reason": (
                "Texte interne au journal de campagne "
                "illustré, champs de formulaire, mentions "
                "annexes et OCR de logo. Conservés dans "
                "l'extraction Docling originale, hors du "
                "corpus de règles du MVP."
            ),
            "status": "approved"
        }
    ]

    new_joins = [
        {
            "page": 16,
            "references": ["#/texts/546", "#/texts/547"],
            "reason": "Paragraphe Overlord Cards scindé.",
            "status": "approved"
        },
        {
            "page": 16,
            "references": ["#/texts/561", "#/texts/562"],
            "reason": (
                "Renvoi vers Large Monster Movement "
                "scindé sur deux éléments."
            ),
            "status": "approved"
        }
    ]

    # Éléments à conserver explicitement.
    # Ils ne sont ni exclus ni fusionnés ici.
    protected = {
        "#/texts/491",
        "#/texts/500",
        "#/texts/505",
        "#/texts/507",
        "#/texts/512",
        "#/texts/513",
        "#/texts/580",
        "#/texts/812",
    }

    new_excluded = [
        ref
        for operation in new_exclusions
        for ref in operation["references"]
    ]

    new_joined = [
        ref
        for operation in new_joins
        for ref in operation["references"]
    ]

    existing_excluded = {
        ref
        for op in register["exclusions"]
        for ref in op["references"]
    }

    existing_joined = {
        ref
        for op in register["joins"]
        for ref in op["references"]
    }

    replacement_refs = {
        op["reference"]
        for op in register["replacements"]
    }

    relabel_refs = {
        op["reference"]
        for op in register.get("relabels", [])
    }

    symbol_refs = {
        entry["reference"]
        for entry in symbol_audit
    }

    require(
        len(new_excluded) == len(set(new_excluded)),
        "Exclusions proposées en double"
    )

    require(
        len(new_joined) == len(set(new_joined)),
        "Références de fusion proposées en double"
    )

    # Toutes les références doivent correspondre
    # à la bonne page dans l'extraction originale.
    for operation in new_exclusions + new_joins:
        for ref in operation["references"]:
            require(ref in by_ref, f"Référence inconnue : {ref}")
            require(
                page_of(by_ref[ref]) == operation["page"],
                f"Page incorrecte : {ref}"
            )

    # Vérifier l'origine et la présence des contenus protégés.
    protected_pages = {
        "#/texts/491": 14,
        "#/texts/500": 14,
        "#/texts/505": 14,
        "#/texts/507": 14,
        "#/texts/512": 14,
        "#/texts/513": 14,
        "#/texts/580": 16,
        "#/texts/812": 21,
    }

    for ref, page in protected_pages.items():
        require(ref in by_ref, f"Texte protégé absent : {ref}")
        require(
            page_of(by_ref[ref]) == page,
            f"Page du texte protégé incorrecte : {ref}"
        )

    require(
        "4 orn" in by_ref["#/texts/512"]["text"]
        or "4 [DAMAGE]" in by_ref["#/texts/512"]["text"],
        "Formule de dégâts inattendue : vérifier #/texts/512"
    )

    # Aucun conflit avec les décisions précédentes.
    forbidden_exclusions = (
        existing_excluded
        | existing_joined
        | replacement_refs
        | relabel_refs
        | symbol_refs
        | protected
        | set(new_joined)
    )

    exclusion_conflicts = (
        set(new_excluded) & forbidden_exclusions
    )

    require(
        not exclusion_conflicts,
        f"Exclusions en conflit : {sorted(exclusion_conflicts)}"
    )

    join_conflicts = set(new_joined) & (
        existing_excluded
        | existing_joined
        | set(new_excluded)
    )

    require(
        not join_conflicts,
        f"Fusions en conflit : {sorted(join_conflicts)}"
    )

    # Ne pas écraser une sauvegarde existante.
    require(
        not BACKUP.exists(),
        f"Sauvegarde déjà existante : {BACKUP}"
    )

    # Toutes les validations sont passées :
    # nous pouvons sauvegarder et écrire.
    BACKUP.write_bytes(REGISTER.read_bytes())

    register["exclusions"].extend(new_exclusions)
    register["joins"].extend(new_joins)

    REGISTER.write_text(
        json.dumps(
            register,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    total_excluded = sum(
        len(op["references"])
        for op in register["exclusions"]
    )

    print("=== MISE À JOUR DOCUMENTAIRE 8.93 ===")
    print("Nouvelles exclusions :", len(new_excluded))
    print("Nouvelles fusions :", len(new_joins))
    print("Éléments protégés :", len(protected))
    print("Exclusions totales :", total_excluded)
    print("Fusions totales :", len(register["joins"]))
    print("Sauvegarde :", BACKUP)
    print("Registre :", REGISTER)
    print("Corpus V2 inchangé")


if __name__ == "__main__":
    main()

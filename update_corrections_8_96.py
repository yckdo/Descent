
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DOCLING = ROOT / "data/processed/descent_rulebook_en.json"
REGISTER = ROOT / "validation/text_corrections.json"
SYMBOL_AUDIT = ROOT / "validation/symbol_audit.json"
BACKUP = ROOT / "validation/text_corrections.before_8_96.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def refs(start, end):
    return [f"#/texts/{i}" for i in range(start, end + 1)]


def page_of(item):
    pages = {
        p["page_no"]
        for p in item.get("prov", [])
        if "page_no" in p
    }
    require(len(pages) == 1, f"Page ambiguë : {item['self_ref']}")
    return next(iter(pages))


def exclusion(page, references, reason):
    return {
        "page": page,
        "references": references,
        "reason": reason,
        "status": "approved"
    }


def join(page, start, end, reason):
    return {
        "page": page,
        "references": refs(start, end),
        "reason": reason,
        "status": "approved"
    }


def main():
    document = load(DOCLING)
    register = load(REGISTER)
    symbol_audit = load(SYMBOL_AUDIT)

    originals = document["texts"]
    by_ref = {e["self_ref"]: e for e in originals}
    positions = {
        e["self_ref"]: i for i, e in enumerate(originals)
    }

    require(len(by_ref) == len(originals),
            "Références sources dupliquées")

    # Exclusions confirmées par les captures du PDF.
    new_exclusions = [
        exclusion(
            5, refs(159, 162),
            "Numéros du schéma Map Tile Breakdown."
        ),
        exclusion(
            7, refs(203, 208),
            "Numéros et nom interne de Hero Sheet Anatomy."
        ),
        exclusion(
            8, refs(239, 244),
            "Numéros du schéma Class Card Anatomy."
        ),
        exclusion(
            9, refs(286, 291),
            "Repères graphiques de Movement Example."
        ),
        exclusion(
            12, refs(431, 432),
            "Numéros du schéma Line of Sight Example."
        )
    ]

    # Fusions distinctes : ne jamais réunir deux règles
    # ou deux paragraphes qui doivent rester séparés.
    new_joins = [
        join(5, 156, 157, "Fin de Hero Setup et Overlord Setup."),
        join(7, 218, 220, "Paragraphe sur l'équipement."),
        join(8, 259, 260, "Introduction des actions du héros."),
        join(8, 268, 272, "Déplacement avec fatigue."),
        join(8, 276, 278, "Cartes épuisées et rafraîchies."),
        join(9, 304, 305, "Étape Check Range."),
        join(9, 306, 307, "Étape Spend Surges."),
        join(9, 308, 309, "Étape Deal Damage."),
        join(12, 427, 429, "Exemple de cible à distance."),
        join(12, 435, 436, "Exemple de ligne de vue."),
        join(12, 445, 449, "Constitution de la défense."),
        join(12, 455, 456, "Exemple de portée."),
        join(17, 607, 612, "Présentation des familiers."),
        join(17, 614, 615, "Activation d'un familier."),
        join(17, 616, 619, "Ordre d'activation."),
        join(17, 620, 627, "Mouvement et actions du familier."),
        join(17, 628, 631, "Occupation des espaces."),
        join(17, 632, 634, "Exemple Widow Tarha.")
    ]

    # Passages qui doivent absolument rester disponibles.
    protected = {
        "#/texts/163",  # Description Map Tile
        "#/texts/209",  # Description Hero Name and Archetype
        "#/texts/245",  # Description Archetype Icon
        "#/texts/292",  # Exemple Movement
        "#/texts/433",  # Exemple Line of Sight
        "#/texts/596",  # Titre Lieutenants
        "#/texts/606",  # Titre Familiars
        "#/texts/613",  # Légende Familiar Token
        "#/texts/635",  # Large Monster Movement
        "#/texts/663",  # Description de carte Lieutenant
    }

    existing_excluded = {
        ref for op in register["exclusions"]
        for ref in op["references"]
    }
    existing_joined = {
        ref for op in register["joins"]
        for ref in op["references"]
    }
    replacement_refs = {
        op["reference"] for op in register["replacements"]
    }
    relabel_refs = {
        op["reference"]
        for op in register.get("relabels", [])
    }
    symbol_refs = {
        entry["reference"] for entry in symbol_audit
    }

    new_excluded = [
        ref for op in new_exclusions
        for ref in op["references"]
    ]
    new_joined = [
        ref for op in new_joins
        for ref in op["references"]
    ]

    require(len(new_excluded) == len(set(new_excluded)),
            "Nouvelles exclusions dupliquées")
    require(len(new_joined) == len(set(new_joined)),
            "Nouvelles fusions chevauchantes")

    for op in new_exclusions + new_joins:
        for ref in op["references"]:
            require(ref in by_ref, f"Référence inconnue : {ref}")
            require(
                page_of(by_ref[ref]) == op["page"],
                f"Page incorrecte : {ref}"
            )

    for op in new_joins:
        indexes = [positions[r] for r in op["references"]]
        require(
            indexes == list(range(indexes[0], indexes[0] + len(indexes))),
            f"Fusion non contiguë : {op['references']}"
        )

    forbidden = (
        existing_excluded
        | existing_joined
        | replacement_refs
        | relabel_refs
        | symbol_refs
        | protected
        | set(new_joined)
    )

    conflicts = set(new_excluded) & forbidden
    require(
        not conflicts,
        f"Exclusions en conflit : {sorted(conflicts)}"
    )

    join_conflicts = set(new_joined) & (
        existing_excluded | existing_joined | set(new_excluded)
    )
    require(
        not join_conflicts,
        f"Fusions en conflit : {sorted(join_conflicts)}"
    )

    require(
        protected <= set(by_ref),
        "Un passage à préserver manque dans Docling"
    )

    require(
        not BACKUP.exists(),
        f"Sauvegarde déjà présente : {BACKUP}"
    )

    # Écriture uniquement après tous les contrôles.
    BACKUP.write_bytes(REGISTER.read_bytes())

    register["exclusions"].extend(new_exclusions)
    register["joins"].extend(new_joins)

    REGISTER.write_text(
        json.dumps(register, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    total_excluded = sum(
        len(op["references"]) for op in register["exclusions"]
    )

    print("=== MISE À JOUR DOCUMENTAIRE 8.96 ===")
    print("Nouvelles références exclues :", len(new_excluded))
    print("Nouvelles fusions :", len(new_joins))
    print("Exclusions totales :", total_excluded)
    print("Fusions totales :", len(register["joins"]))
    print("Passages protégés :", len(protected))
    print("Sauvegarde :", BACKUP)
    print("Corpus V2 inchangé")


if __name__ == "__main__":
    main()

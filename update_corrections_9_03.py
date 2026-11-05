
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DOCLING = ROOT / "data/processed/descent_rulebook_en.json"
REGISTER = ROOT / "validation/text_corrections.json"
BACKUP = ROOT / "validation/text_corrections.before_9_03.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def page_of(item):
    pages = {
        p["page_no"]
        for p in item.get("prov", [])
        if "page_no" in p
    }
    require(
        len(pages) == 1,
        f"Provenance ambiguë : {item['self_ref']}"
    )
    return next(iter(pages))


def main():
    document = load(DOCLING)
    register = load(REGISTER)

    originals = document["texts"]
    by_ref = {item["self_ref"]: item for item in originals}
    positions = {
        item["self_ref"]: index
        for index, item in enumerate(originals)
    }

    new_join = {
        "page": 8,
        "references": ["#/texts/273", "#/texts/274"],
        "reason": (
            "Titre unique : Exhausting and Refreshing Cards."
        ),
        "status": "approved",
    }

    new_relabel = {
        "page": 14,
        "reference": "#/texts/492",
        "old_label": "section_header",
        "new_label": "caption",
        "reason": (
            "Attack Pool est un libellé de l'exemple de combat."
        ),
        "status": "approved",
    }

    excluded = {
        ref
        for operation in register["exclusions"]
        for ref in operation["references"]
    }

    joined = {
        ref
        for operation in register["joins"]
        for ref in operation["references"]
    }

    relabeled = {
        operation["reference"]
        for operation in register.get("relabels", [])
    }

    # Contrôle du titre coupé.
    title_refs = new_join["references"]

    for ref in title_refs:
        require(ref in by_ref, f"Référence absente : {ref}")
        require(
            page_of(by_ref[ref]) == 8,
            f"Page incorrecte : {ref}",
        )
        require(
            ref not in excluded | joined | relabeled,
            f"Conflit pour le titre : {ref}",
        )
        require(
            by_ref[ref]["label"] == "section_header",
            f"Étiquette inattendue : {ref}",
        )

    require(
        by_ref["#/texts/273"]["text"].strip()
        == "Exhausting and",
        "Premier fragment du titre inattendu",
    )

    require(
        by_ref["#/texts/274"]["text"].strip()
        == "Refreshing Cards",
        "Second fragment du titre inattendu",
    )

    require(
        positions["#/texts/274"]
        == positions["#/texts/273"] + 1,
        "Fragments du titre non contigus",
    )

    # Contrôle du reclassement Attack Pool.
    attack_ref = "#/texts/492"

    require(
        attack_ref in by_ref,
        "Attack Pool introuvable",
    )
    require(
        page_of(by_ref[attack_ref]) == 14,
        "Page incorrecte pour Attack Pool",
    )
    require(
        by_ref[attack_ref]["text"].strip() == "Attack Pool",
        "Texte Attack Pool inattendu",
    )
    require(
        by_ref[attack_ref]["label"] == "section_header",
        "Étiquette initiale Attack Pool inattendue",
    )
    require(
        attack_ref not in excluded | joined | relabeled,
        "Conflit avec Attack Pool",
    )

    # Defense Pool est déjà une légende.
    defense_ref = "#/texts/493"

    require(
        defense_ref in by_ref,
        "Defense Pool introuvable",
    )
    require(
        page_of(by_ref[defense_ref]) == 14,
        "Page incorrecte pour Defense Pool",
    )
    require(
        by_ref[defense_ref]["text"].strip() == "Defense Pool",
        "Texte Defense Pool inattendu",
    )
    require(
        by_ref[defense_ref]["label"] == "caption",
        "Defense Pool devrait déjà être une légende",
    )
    require(
        defense_ref not in excluded,
        "Defense Pool est exclu",
    )

    # Préservation des éléments de la page 21.
    protected = {
        "#/texts/777": "Record-Keeping and Storage",
        "#/texts/778": "Heirs of Blood Campaign Log",
        "#/texts/812": None,
    }

    for ref, expected_text in protected.items():
        require(ref in by_ref, f"Référence absente : {ref}")
        require(
            page_of(by_ref[ref]) == 21,
            f"Page incorrecte : {ref}",
        )
        require(
            ref not in excluded,
            f"Référence protégée exclue : {ref}",
        )

        if expected_text is not None:
            require(
                by_ref[ref]["text"].strip() == expected_text,
                f"Texte protégé inattendu : {ref}",
            )

    require(
        not BACKUP.exists(),
        f"Sauvegarde déjà présente : {BACKUP}",
    )

    # Écriture après validation complète.
    BACKUP.write_bytes(REGISTER.read_bytes())

    register["joins"].append(new_join)
    register.setdefault("relabels", []).append(new_relabel)

    REGISTER.write_text(
        json.dumps(register, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=== MISE À JOUR STRUCTURELLE 9.03 ===")
    print("Nouvelle fusion de titre : 1")
    print("Nouveau reclassement : 1")
    print("Fusions totales :", len(register["joins"]))
    print("Reclassements totaux :", len(register["relabels"]))
    print("Exclusions inchangées")
    print("Defense Pool : déjà classé caption")
    print("Sauvegarde :", BACKUP)
    print("Corpus normalisé inchangé")


if __name__ == "__main__":
    main()

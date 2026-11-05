
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DOCLING = ROOT / "data/processed/descent_rulebook_en.json"
REGISTER = ROOT / "validation/text_corrections.json"
BACKUP = ROOT / "validation/text_corrections.before_9_07.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_page(item):
    pages = {
        entry["page_no"]
        for entry in item.get("prov", [])
        if "page_no" in entry
    }
    require(
        len(pages) == 1,
        f"Provenance ambiguë : {item['self_ref']}"
    )
    return next(iter(pages))


def main():
    document = load(DOCLING)
    register = load(REGISTER)

    texts = document["texts"]
    by_ref = {item["self_ref"]: item for item in texts}
    positions = {
        item["self_ref"]: index
        for index, item in enumerate(texts)
    }

    require(
        len(by_ref) == len(texts),
        "Références Docling dupliquées"
    )

    new_join = {
        "page": 11,
        "references": [
            "#/texts/403",
            "#/texts/404"
        ],
        "reason": (
            "Réunir la définition complète du symbole SURGE "
            "dans un seul élément list_item."
        ),
        "status": "approved"
    }

    new_relabels = [
        {
            "page": 9,
            "reference": ref,
            "old_label": "text",
            "new_label": "list_item",
            "reason": (
                f"Étape {step} de la séquence Attack : "
                "harmonisation avec les deux premières étapes."
            ),
            "status": "approved"
        }
        for ref, step in [
            ("#/texts/304", 3),
            ("#/texts/306", 4),
            ("#/texts/308", 5),
        ]
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

    existing_relabeled = {
        op["reference"]
        for op in register.get("relabels", [])
    }

    existing_replaced = {
        op["reference"]
        for op in register["replacements"]
    }

    # Vérification de la définition de SURGE.
    first, second = new_join["references"]

    for ref in (first, second):
        require(ref in by_ref, f"Référence absente : {ref}")
        require(
            source_page(by_ref[ref]) == 11,
            f"Page incorrecte : {ref}"
        )
        require(
            ref not in existing_excluded | existing_joined,
            f"Fusion en conflit : {ref}"
        )

    require(
        positions[second] == positions[first] + 1,
        "Fragments SURGE non contigus dans Docling"
    )

    require(
        by_ref[first].get("label") == "list_item",
        "La première partie de SURGE n'est pas list_item"
    )

    require(
        by_ref[second].get("label") == "text",
        "La seconde partie de SURGE n'est pas text"
    )

    require(
        "surge" in by_ref[first]["text"].lower(),
        "Premier fragment SURGE inattendu"
    )

    require(
        by_ref[second]["text"].strip().startswith("abilities,"),
        "Second fragment SURGE inattendu"
    )

    require(
        first not in existing_relabeled
        and second not in existing_relabeled,
        "Reclassement existant sur les fragments SURGE"
    )

    require(
        first not in existing_replaced
        and second not in existing_replaced,
        "Correction textuelle existante sur SURGE"
    )

    # Vérification des étapes 3, 4 et 5 du combat.
    for op in new_relabels:
        ref = op["reference"]

        require(ref in by_ref, f"Référence absente : {ref}")

        require(
            source_page(by_ref[ref]) == op["page"],
            f"Page incorrecte : {ref}"
        )

        require(
            by_ref[ref].get("label") == op["old_label"],
            f"Étiquette inattendue : {ref}"
        )

        require(
            ref not in (
                existing_excluded
                | existing_relabeled
                | existing_replaced
            ),
            f"Conflit de reclassement : {ref}"
        )

        # Ces références sont les débuts de fusions déjà
        # approuvées. Elles doivent être conservées.
        matching_joins = [
            join
            for join in register["joins"]
            if join["references"][0] == ref
        ]

        require(
            len(matching_joins) == 1,
            f"Fusion attendue introuvable : {ref}"
        )

        require(
            matching_joins[0]["page"] == 9,
            f"Page de fusion incorrecte : {ref}"
        )

    # Protéger les deux premières étapes existantes.
    for ref in ("#/texts/302", "#/texts/303"):
        require(ref in by_ref, f"Référence absente : {ref}")
        require(
            source_page(by_ref[ref]) == 9,
            f"Page incorrecte : {ref}"
        )
        require(
            by_ref[ref].get("label") == "list_item",
            f"Étape initiale mal classée : {ref}"
        )
        require(
            ref not in existing_excluded,
            f"Étape initiale exclue : {ref}"
        )

    require(
        not BACKUP.exists(),
        f"Sauvegarde déjà existante : {BACKUP}"
    )

    # Aucun fichier n'est modifié avant ces contrôles.
    BACKUP.write_bytes(REGISTER.read_bytes())

    register["joins"].append(new_join)
    register.setdefault("relabels", []).extend(new_relabels)

    REGISTER.write_text(
        json.dumps(
            register,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print("=== MISE À JOUR DOCUMENTAIRE 9.07 ===")
    print("Nouvelle fusion :", 1)
    print("Nouveaux reclassements :", len(new_relabels))
    print("Fusions totales :", len(register["joins"]))
    print("Reclassements totaux :", len(register["relabels"]))
    print("Références exclues :", len(existing_excluded))
    print("Remplacements :", len(register["replacements"]))
    print("Sauvegarde :", BACKUP)
    print("Corpus normalisé inchangé")


if __name__ == "__main__":
    main()

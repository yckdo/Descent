
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCLING = ROOT / "data/processed/descent_rulebook_en.json"
REGISTER = ROOT / "validation/text_corrections.json"
BACKUP = ROOT / "validation/text_corrections.before_8_98.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def refs(start, end):
    return [f"#/texts/{i}" for i in range(start, end + 1)]


def join(page, start, end, reason):
    return {
        "page": page,
        "references": refs(start, end),
        "reason": reason,
        "status": "approved",
    }


def main():
    doc = load(DOCLING)
    register = load(REGISTER)

    originals = doc["texts"]
    by_ref = {item["self_ref"]: item for item in originals}
    positions = {
        item["self_ref"]: i
        for i, item in enumerate(originals)
    }

    new_joins = [
        join(11, 357, 360, "Exemple d'activation des monstres."),
        join(11, 361, 362, "Introduction des actions des monstres."),
        join(11, 363, 364, "Action Move."),
        join(11, 367, 370, "Action Monster Action."),
        join(11, 371, 372, "Action Open or Close a Door."),
        join(11, 373, 374, "Action Special."),
        join(11, 405, 406, "Résultat X du dé d'attaque."),
        join(11, 407, 408, "Résultats de portée des dés."),
        join(18, 682, 683, "Règle Pit."),
        join(18, 685, 686, "Règle Lava."),
        join(24, 900, 901, "Règle des conditions."),
    ]

    new_replacement = {
        "page": 24,
        "reference": "#/texts/900",
        "old": "[DAMAGE](",
        "new": "[DAMAGE] (",
        "reason": "Espace manquant avant la parenthèse.",
        "status": "approved",
    }

    existing_excluded = {
        ref
        for operation in register["exclusions"]
        for ref in operation["references"]
    }
    existing_joined = {
        ref
        for operation in register["joins"]
        for ref in operation["references"]
    }

    new_joined = [
        ref
        for operation in new_joins
        for ref in operation["references"]
    ]

    require(
        len(new_joined) == len(set(new_joined)),
        "Chevauchement entre nouvelles fusions"
    )

    for operation in new_joins:
        references = operation["references"]
        indexes = []

        for ref in references:
            require(ref in by_ref, f"Référence inconnue : {ref}")
            pages = {
                p.get("page_no")
                for p in by_ref[ref].get("prov", [])
            }
            require(
                pages == {operation["page"]},
                f"Page incorrecte : {ref}"
            )
            indexes.append(positions[ref])

        require(
            indexes == list(range(indexes[0], indexes[0] + len(indexes))),
            f"Fusion non contiguë : {references}"
        )

    require(
        not set(new_joined) & (existing_excluded | existing_joined),
        "Conflit avec une exclusion ou fusion existante"
    )

    replacement_ref = new_replacement["reference"]
    require(
        replacement_ref in by_ref,
        "Référence du remplacement absente"
    )
    require(
        replacement_ref not in existing_excluded,
        "Remplacement dans un élément exclu"
    )
    require(
        not any(
            op["reference"] == replacement_ref
            for op in register["replacements"]
        ),
        "Remplacement déjà enregistré"
    )

    # Dans le texte Docling original, la correction de
    # pictogramme n'est pas encore appliquée.
    source_text = by_ref[replacement_ref]["text"]
    require(
        "orn(" in source_text,
        "Pictogramme suivi de '(' introuvable dans Docling"
    )

    require(
        not BACKUP.exists(),
        f"Sauvegarde déjà existante : {BACKUP}"
    )

    BACKUP.write_bytes(REGISTER.read_bytes())

    register["joins"].extend(new_joins)
    register["replacements"].append(new_replacement)

    REGISTER.write_text(
        json.dumps(register, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print("=== MISE À JOUR DOCUMENTAIRE 8.98 ===")
    print("Nouvelles fusions :", len(new_joins))
    print("Nouveaux remplacements : 1")
    print("Fusions totales :", len(register["joins"]))
    print("Remplacements totaux :", len(register["replacements"]))
    print("Sauvegarde :", BACKUP)
    print("Corpus V2 inchangé")


if __name__ == "__main__":
    main()

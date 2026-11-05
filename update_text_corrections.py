
import json
from pathlib import Path

DOCLING = Path("data/processed/descent_rulebook_en.json")
REGISTER = Path("validation/text_corrections.json")
BACKUP = Path("validation/text_corrections.before_8_85.json")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


def refs(start, end):
    return [f"#/texts/{i}" for i in range(start, end + 1)]


def page_of(item):
    pages = {
        p["page_no"]
        for p in item.get("prov", [])
        if "page_no" in p
    }
    if len(pages) != 1:
        raise ValueError(
            f"Page ambiguë : {item['self_ref']}"
        )
    return next(iter(pages))


def main():
    doc = load(DOCLING)
    data = load(REGISTER)

    by_ref = {
        item["self_ref"]: item
        for item in doc["texts"]
    }

    # Toutes les références de la page 23.
    # L'index vérifié est conservé séparément.
    page23_refs = [
        item["self_ref"]
        for item in doc["texts"]
        if any(
            p.get("page_no") == 23
            for p in item.get("prov", [])
        )
    ]

    new_exclusions = [
        {
            "page": 6,
            "references": refs(170, 185),
            "reason": "Numéros isolés du Setup Diagram.",
            "status": "approved"
        },
        {
            "page": 10,
            "references": refs(328, 331),
            "reason": "Numéros de la Search Card Anatomy.",
            "status": "approved"
        },
        {
            "page": 11,
            "references": refs(376, 382),
            "reason": "Numéros de la Shop Item Card Anatomy.",
            "status": "approved"
        },
        {
            "page": 11,
            "references": refs(419, 420),
            "reason": "Fragments OCR du pied de page.",
            "status": "approved"
        },
        {
            "page": 17,
            "references": refs(591, 595),
            "reason": "Numéros isolés du schéma.",
            "status": "approved"
        },
        {
            "page": 17,
            "references": refs(641, 650),
            "reason": "Numéros de la Lieutenant Card Anatomy.",
            "status": "approved"
        },
        {
            "page": 23,
            "references": page23_refs,
            "reason": (
                "Index brut et crédits exclus du corpus "
                "de règles. L'index fidèle est conservé "
                "dans conceptual_index."
            ),
            "status": "approved"
        }
    ]

    new_replacement = {
        "page": 1,
        "reference": "#/texts/1",
        "old": "RULES OFPLAY",
        "new": "RULES OF PLAY",
        "reason": "Restauration de l'espace manquant.",
        "status": "approved"
    }

    new_relabels = [
        {
            "page": 17,
            "reference": "#/texts/596",
            "old_label": "text",
            "new_label": "section_header",
            "reason": "Titre Lieutenants.",
            "status": "approved"
        },
        {
            "page": 17,
            "reference": "#/texts/606",
            "old_label": "text",
            "new_label": "section_header",
            "reason": "Titre Familiars.",
            "status": "approved"
        }
    ]

    # Vérifier les références avant d'écrire.
    for operation in new_exclusions:
        for ref in operation["references"]:
            if ref not in by_ref:
                raise ValueError(f"Référence inconnue : {ref}")
            if page_of(by_ref[ref]) != operation["page"]:
                raise ValueError(f"Page incorrecte : {ref}")

    for operation in [new_replacement] + new_relabels:
        ref = operation["reference"]
        if ref not in by_ref:
            raise ValueError(f"Référence inconnue : {ref}")
        if page_of(by_ref[ref]) != operation["page"]:
            raise ValueError(f"Page incorrecte : {ref}")

    if new_replacement["old"] not in by_ref["#/texts/1"]["text"]:
        raise ValueError("Texte de couverture inattendu")

    for operation in new_relabels:
        if by_ref[operation["reference"]]["label"] != operation["old_label"]:
            raise ValueError(
                f"Type Docling inattendu : {operation['reference']}"
            )

    # Détecter les exclusions déjà enregistrées.
    existing_excluded = {
        ref
        for op in data["exclusions"]
        for ref in op["references"]
    }

    for operation in new_exclusions:
        overlap = existing_excluded.intersection(
            operation["references"]
        )
        if overlap:
            raise ValueError(
                f"Exclusions déjà présentes : {sorted(overlap)}"
            )

    if any(
        op["reference"] == new_replacement["reference"]
        for op in data["replacements"]
    ):
        raise ValueError("Remplacement déjà enregistré")

    existing_relabels = data.get("relabels", [])
    if existing_relabels:
        raise ValueError(
            "Des reclassements existent déjà : vérifier avant mise à jour"
        )

    # Sauvegarde de l'ancien registre.
    if BACKUP.exists():
        raise FileExistsError(
            f"Sauvegarde déjà présente : {BACKUP}"
        )
    BACKUP.write_bytes(REGISTER.read_bytes())

    # Mise à jour.
    data["exclusions"].extend(new_exclusions)
    data["replacements"].append(new_replacement)
    data["relabels"] = new_relabels

    save(REGISTER, data)

    print("=== REGISTRE DOCUMENTAIRE MIS À JOUR ===")
    print("Nouveaux groupes d'exclusion :", len(new_exclusions))
    print(
        "Nouvelles références exclues :",
        sum(len(op["references"]) for op in new_exclusions)
    )
    print("Nouveaux remplacements : 1")
    print("Reclassements de titres : 2")
    print("Références de page 23 :", len(page23_refs))
    print("Sauvegarde :", BACKUP)
    print("Registre :", REGISTER)


if __name__ == "__main__":
    main()

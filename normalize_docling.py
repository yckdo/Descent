
import json
import re
from collections import defaultdict
from pathlib import Path


# ============================================================
# NORMALISATION DOCLING V2 — DESCENT SECOND EDITION
# ============================================================
#
# Objectifs :
# - Préserver les exports Docling originaux
# - Appliquer les 77 corrections de pictogrammes
# - Appliquer les exclusions documentaires validées
# - Corriger les erreurs OCR enregistrées
# - Fusionner les fragments de texte validés
# - Reclasser les titres identifiés
# - Restaurer le titre du manuel
# - Conserver les références aux pages et éléments sources
# - Intégrer séparément les 71 entrées de l'index
# - Générer un JSON structuré et un Markdown lisible
#
# Aucun fichier source n'est modifié.
# Le corpus généré nécessite encore une validation finale.
# ============================================================


# ============================================================
# 1. FICHIERS
# ============================================================

ROOT = Path(__file__).resolve().parent

DOCLING = ROOT / "data/processed/descent_rulebook_en.json"

SYMBOL_AUDIT = ROOT / "validation/symbol_audit.json"

SYMBOLS = ROOT / "data/reference/symbols.json"

CORRECTIONS = ROOT / "validation/text_corrections.json"

INDEX = ROOT / "data/reference/index_page23.json"

OUTPUT_DIR = ROOT / "data/normalized"

OUTPUT_JSON = OUTPUT_DIR / "descent_rulebook.json"

OUTPUT_MD = OUTPUT_DIR / "descent_rulebook.md"


# ============================================================
# 2. FONCTIONS UTILITAIRES
# ============================================================

def load_json(path):
    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier introuvable : {path}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def require(condition, message):
    if not condition:
        raise ValueError(message)


def page_of(item):
    pages = {
        provenance["page_no"]
        for provenance in item.get("prov", [])
        if "page_no" in provenance
    }

    require(
        len(pages) == 1,
        "Provenance de page ambiguë : "
        + item.get("self_ref", "?")
    )

    return next(iter(pages))


def status_valid(operation):
    return operation.get("status") in (
        "approved",
        "visual_reviewed"
    )


def check_operation(operation, name):
    require(
        status_valid(operation),
        f"Opération non validée : {name}"
    )


# ============================================================
# 3. CHARGEMENT ET VALIDATION INITIALE
# ============================================================

def main():

    document = load_json(DOCLING)
    audit = load_json(SYMBOL_AUDIT)
    symbol_dict = load_json(SYMBOLS)["symbols"]
    corrections = load_json(CORRECTIONS)
    index_data = load_json(INDEX)

    original = document["texts"]

    by_ref = {
        item["self_ref"]: item
        for item in original
    }

    require(
        len(by_ref) == len(original),
        "Références Docling dupliquées"
    )

    require(
        len(original) == 919,
        "Nombre d'éléments Docling inattendu"
    )

    require(
        len(audit) == 77,
        "Le registre ne contient pas 77 pictogrammes"
    )

    columns = index_data["columns"]

    require(
        len(columns) == 3,
        "L'index doit contenir trois colonnes"
    )

    index_entries = sum(
        len(column["entries"])
        for column in columns
    )

    require(
        index_entries == 71,
        "L'index doit contenir 71 entrées"
    )

    # --------------------------------------------------------
    # Exclusions documentaires
    # --------------------------------------------------------

    excluded = set()

    for index, operation in enumerate(
        corrections["exclusions"]
    ):

        check_operation(
            operation,
            f"exclusions[{index}]"
        )

        for ref in operation["references"]:

            require(
                ref in by_ref,
                f"Référence exclue inconnue : {ref}"
            )

            require(
                page_of(by_ref[ref]) == operation["page"],
                f"Page incorrecte pour l'exclusion : {ref}"
            )

            require(
                ref not in excluded,
                f"Exclusion dupliquée : {ref}"
            )

            excluded.add(ref)

    # --------------------------------------------------------
    # Pictogrammes validés
    # --------------------------------------------------------

    symbols_by_ref = defaultdict(list)
    symbol_ids = set()

    for entry in audit:

        ref = entry["reference"]
        symbol_id = entry["id"]

        require(
            symbol_id not in symbol_ids,
            f"Identifiant de pictogramme dupliqué : {symbol_id}"
        )

        symbol_ids.add(symbol_id)

        require(
            ref in by_ref,
            f"Référence de pictogramme inconnue : {ref}"
        )

        require(
            ref not in excluded,
            f"Pictogramme dans un élément exclu : {ref}"
        )

        require(
            entry["status"] == "verified",
            f"Pictogramme non vérifié : {symbol_id}"
        )

        require(
            entry["expected_symbol"] in symbol_dict,
            f"Identifiant de symbole inconnu : {symbol_id}"
        )

        source = by_ref[ref]["text"]

        start = entry["char_start"]
        end = entry["char_end"]

        require(
            0 <= start < end <= len(source),
            f"Position invalide : {symbol_id}"
        )

        require(
            source[start:end] == entry["detected"],
            f"Texte source différent : {symbol_id}"
        )

        symbols_by_ref[ref].append(entry)

    # --------------------------------------------------------
    # Vérifier les conflits d'exclusion
    # --------------------------------------------------------

    join_refs = [
        ref
        for operation in corrections["joins"]
        for ref in operation["references"]
    ]

    replacement_refs = [
        operation["reference"]
        for operation in corrections["replacements"]
    ]

    relabel_refs = [
        operation["reference"]
        for operation in corrections.get("relabels", [])
    ]

    protected_refs = (
        set(join_refs)
        | set(replacement_refs)
        | set(relabel_refs)
        | set(symbols_by_ref)
    )

    conflicts = sorted(excluded & protected_refs)

    require(
        not conflicts,
        f"Exclusions en conflit : {conflicts}"
    )

    # ========================================================
    # 4. NORMALISER LES TEXTES ET LES PICTOGRAMMES
    # ========================================================

    elements = []

    for item in original:

        ref = item["self_ref"]

        if ref in excluded:
            continue

        content = item.get("text", "")
        source_content = content

        previous_start = len(content)

        # Appliquer les corrections de droite à gauche.
        # Les positions originales ne sont pas décalées.

        for symbol in sorted(
            symbols_by_ref.get(ref, []),
            key=lambda x: x["char_start"],
            reverse=True
        ):

            start = symbol["char_start"]
            end = symbol["char_end"]

            require(
                end <= previous_start,
                f"Pictogrammes chevauchants : {ref}"
            )

            previous_start = start

            replacement = (
                f"[{symbol['expected_symbol']}]"
            )

            # Cas particulier déjà identifié :
            # ornresults -> [SURGE] results

            if (
                symbol["expected_symbol"] == "SURGE"
                and source_content[end:].startswith("results")
            ):
                replacement += " "

            content = (
                content[:start]
                + replacement
                + content[end:]
            )

        elements.append({
            "page": page_of(item),
            "label": item.get("label", "text"),
            "text": content,
            "source_refs": [ref]
        })

    element_map = {
        element["source_refs"][0]: element
        for element in elements
    }

    # ========================================================
    # 5. APPLIQUER LES CORRECTIONS TEXTUELLES
    # ========================================================

    for index, operation in enumerate(
        corrections["replacements"]
    ):

        check_operation(
            operation,
            f"replacements[{index}]"
        )

        ref = operation["reference"]

        require(
            ref in element_map,
            f"Référence de remplacement absente : {ref}"
        )

        element = element_map[ref]

        require(
            element["page"] == operation["page"],
            f"Page incorrecte pour le remplacement : {ref}"
        )

        old = operation["old"]
        new = operation["new"]

        require(
            element["text"].count(old) == 1,
            f"Texte à remplacer absent ou ambigu : {ref}"
        )

        element["text"] = element["text"].replace(
            old,
            new,
            1
        )

    # ========================================================
    # 6. RESTAURER LE TITRE DE COUVERTURE
    # ========================================================

    cover = corrections["cover_title"]

    check_operation(
        cover,
        "cover_title"
    )

    cover_ref = cover["reference"]

    require(
        cover_ref in element_map,
        "Titre de couverture absent"
    )

    cover_element = element_map[cover_ref]

    require(
        cover_element["page"] == cover["page"],
        "Page incorrecte pour le titre"
    )

    cover_element["text"] = cover["normalized_text"]
    cover_element["label"] = "title"

    # ========================================================
    # 7. RECLASSER LES TITRES VALIDÉS
    # ========================================================

    relabels = corrections.get("relabels", [])
    applied_relabels = set()

    for index, operation in enumerate(relabels):

        check_operation(
            operation,
            f"relabels[{index}]"
        )

        ref = operation["reference"]

        require(
            ref not in applied_relabels,
            f"Reclassement dupliqué : {ref}"
        )

        applied_relabels.add(ref)

        require(
            ref in element_map,
            f"Référence à reclasser absente : {ref}"
        )

        element = element_map[ref]

        require(
            element["page"] == operation["page"],
            f"Page incorrecte pour le reclassement : {ref}"
        )

        require(
            element["label"] == operation["old_label"],
            f"Type initial incorrect : {ref}"
        )

        require(
            ref not in excluded,
            f"Impossible de reclasser un texte exclu : {ref}"
        )

        element["label"] = operation["new_label"]

    # ========================================================
    # 8. PRÉPARER LES FUSIONS DE PARAGRAPHES
    # ========================================================

    groups = {}
    consumed = set()

    positions = {
        element["source_refs"][0]: index
        for index, element in enumerate(elements)
    }

    for index, operation in enumerate(
        corrections["joins"]
    ):

        check_operation(
            operation,
            f"joins[{index}]"
        )

        refs = operation["references"]

        require(
            len(refs) >= 2,
            f"Fusion contenant moins de deux éléments : {refs}"
        )

        require(
            len(refs) == len(set(refs)),
            f"Référence répétée dans une fusion : {refs}"
        )

        for ref in refs:

            require(
                ref in element_map,
                f"Référence de fusion absente : {ref}"
            )

            require(
                ref not in consumed,
                f"Fusion en conflit : {ref}"
            )

            require(
                element_map[ref]["page"] == operation["page"],
                f"Page incorrecte pour la fusion : {ref}"
            )

            consumed.add(ref)

        ref_positions = [
            positions[ref]
            for ref in refs
        ]

        expected_positions = list(
            range(
                ref_positions[0],
                ref_positions[0] + len(refs)
            )
        )

        require(
            ref_positions == expected_positions,
            f"Fusion non contiguë ou désordonnée : {refs}"
        )

        groups[refs[0]] = refs

    # ========================================================
    # 9. APPLIQUER LES FUSIONS
    # ========================================================

    output_elements = []

    for element in elements:

        ref = element["source_refs"][0]

        if ref in groups:

            refs = groups[ref]

            merged = {
                "page": element["page"],
                "label": element["label"],
                "text": " ".join(
                    element_map[r]["text"].strip()
                    for r in refs
                ),
                "source_refs": list(refs)
            }

            output_elements.append(merged)

        elif ref in consumed:
            continue

        else:
            output_elements.append(element)

    # ========================================================
    # 10. CONTRÔLES D'INTÉGRITÉ
    # ========================================================

    expected_count = (
        len(original)
        - len(excluded)
        - sum(
            len(refs) - 1
            for refs in groups.values()
        )
    )

    require(
        len(output_elements) == expected_count,
        "Nombre d'éléments normalisés incohérent"
    )

    flattened_refs = [
        ref
        for element in output_elements
        for ref in element["source_refs"]
    ]

    require(
        len(flattened_refs) == len(set(flattened_refs)),
        "Références sources dupliquées"
    )

    require(
        set(flattened_refs) == set(by_ref) - excluded,
        "Des références ont été perdues"
    )

    # Vérification des occurrences OCR isolées.
    # Ne pas confondre avec "corner", "morning", etc.

    residual_orn = [
        element["source_refs"]
        for element in output_elements
        if re.search(r"\born\b", element["text"])
    ]

    require(
        not residual_orn,
        f"Occurrences 'orn' résiduelles : {residual_orn}"
    )

    # Vérifier les deux titres de la page 17.

    expected_titles = {
        "#/texts/596": "Lieutenants",
        "#/texts/606": "Familiars"
    }

    for ref, expected_text in expected_titles.items():

        require(
            ref in element_map,
            f"Titre manquant : {ref}"
        )

        element = element_map[ref]

        require(
            element["label"] == "section_header",
            f"Titre non reclassé : {ref}"
        )

        require(
            element["text"] == expected_text,
            f"Texte du titre inattendu : {ref}"
        )

    # ========================================================
    # 11. ORGANISER LE CORPUS PAR PAGE
    # ========================================================

    pages = defaultdict(list)

    for element in output_elements:
        pages[element["page"]].append(element)

    normalized = {
        "schema_version": "2.0",
        "source": str(
            DOCLING.relative_to(ROOT)
        ),
        "normalization": {
            "symbol_replacements": len(audit),
            "text_exclusions": len(excluded),
            "text_replacements": len(
                corrections["replacements"]
            ),
            "joins": len(groups),
            "relabels": len(relabels),
            "cover_title_restored": True,
            "index_entries": index_entries,
            "status": "requires_final_validation"
        },
        "pages": [
            {
                "page": number,
                "elements": pages[number]
            }
            for number in sorted(pages)
        ],
        "conceptual_index": index_data
    }

    # ========================================================
    # 12. GÉNÉRER LE MARKDOWN
    # ========================================================

    markdown = [
        "<!-- Descent V2 : corpus normalisé -->",
        "<!-- Validation finale requise -->",
        ""
    ]

    for page in normalized["pages"]:

        number = page["page"]

        markdown.append(
            f"<!-- PDF page {number} -->"
        )
        markdown.append("")

        for element in page["elements"]:

            # Les pieds de page restent dans le JSON.
            if element["label"] == "page_footer":
                continue

            refs = ", ".join(
                element["source_refs"]
            )

            markdown.append(
                f"<!-- source: {refs} -->"
            )

            content = element["text"].strip()

            if element["label"] == "title":

                markdown.append(
                    f"# {content}"
                )

            elif element["label"] == "section_header":

                markdown.append(
                    f"## {content}"
                )

            elif element["label"] == "list_item":

                markdown.append(
                    f"- {content}"
                )

            else:

                markdown.append(content)

            markdown.append("")

    # --------------------------------------------------------
    # Index reconstruit, conservé séparément
    # --------------------------------------------------------

    markdown.append(
        "## Index documentaire — page 23"
    )
    markdown.append("")

    for column in columns:

        for entry in column["entries"]:

            indent = (
                "  "
                if entry["level"] == 1
                else ""
            )

            markdown.append(
                f"{indent}- "
                f"{entry['title']} — p. {entry['page']}"
            )

    # ========================================================
    # 13. ENREGISTRER LES RÉSULTATS
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_JSON.write_text(
        json.dumps(
            normalized,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    OUTPUT_MD.write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8"
    )

    # ========================================================
    # 14. RAPPORT D'EXÉCUTION
    # ========================================================

    print("=== NORMALISATION DOCLING V2 ===")
    print("Éléments sources :", len(original))
    print("Références exclues :", len(excluded))
    print("Pictogrammes remplacés :", len(audit))

    print(
        "Remplacements textuels :",
        len(corrections["replacements"])
    )

    print("Fusions :", len(groups))
    print("Reclassements :", len(relabels))
    print("Éléments normalisés :", len(output_elements))
    print("Pages avec du texte :", len(pages))
    print("Entrées d'index :", index_entries)

    print(
        "Occurrences 'orn' isolées résiduelles :",
        len(residual_orn)
    )

    print("JSON :", OUTPUT_JSON)
    print("Markdown :", OUTPUT_MD)
    print("Statut : validation finale requise")


if __name__ == "__main__":
    main()

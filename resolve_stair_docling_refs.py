
def build_docling_lookup(evidence):
    """
    Associe chaque référence Docling aux extraits
    effectivement récupérés par STAIR.

    Ne suppose rien sur les identifiants Sxxx.
    """
    lookup = {}

    for item in evidence:
        for ref in item.get("source_refs", []):
            lookup.setdefault(ref, []).append(item)

    return lookup


def resolve_docling_refs(
    docling_refs,
    evidence,
    expected_section=None,
):
    """
    Résout une liste de références Docling.

    Une référence absente ou ambiguë provoque
    une erreur explicite.
    """
    lookup = build_docling_lookup(evidence)
    resolved = []

    for ref in docling_refs:
        matches = lookup.get(ref, [])

        if expected_section is not None:
            matches = [
                item for item in matches
                if item["section_id"] == expected_section
            ]

        if not matches:
            raise ValueError(
                f"Référence Docling introuvable : {ref}"
            )

        if len(matches) != 1:
            raise ValueError(
                f"Référence Docling ambiguë : {ref}"
            )

        resolved.append({
            "docling_ref": ref,
            "source_id": matches[0]["id"],
            "section_id": matches[0]["section_id"],
            "pdf_page": matches[0]["page"],
        })

    return resolved

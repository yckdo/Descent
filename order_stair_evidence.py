
def order_evidence_by_sections(evidence, ranked_sections, max_roots=3):
    """
    Organise les preuves dans l'ordre des sections STAIR.

    Les sections principales sont présentées d'abord.
    Les autres sections suivent dans leur ordre d'apparition
    dans les preuves initiales.

    À l'intérieur de chaque section, les éléments sont
    classés dans l'ordre des références Docling.

    Aucun extrait ni identifiant de citation n'est modifié.
    """

    if not isinstance(evidence, list):
        raise ValueError("Liste de preuves attendue.")

    if not isinstance(ranked_sections, list):
        raise ValueError("Liste de sections attendue.")

    if not isinstance(max_roots, int) or max_roots < 1:
        raise ValueError("max_roots invalide.")

    groups = {}
    section_order = []

    for section in ranked_sections[:max_roots]:
        section_id = section["id"]

        if section_id not in section_order:
            section_order.append(section_id)

    for item in evidence:
        key = item.get("section_id") or "non_rattache"

        groups.setdefault(key, []).append(item)

        if key not in section_order:
            section_order.append(key)

    def source_position(item):
        positions = []

        for ref in item["source_refs"]:
            try:
                positions.append(int(ref.rsplit("/", 1)[-1]))
            except (ValueError, IndexError):
                continue

        return min(positions) if positions else 999999

    ordered = []

    for section_id in section_order:
        section_items = groups.get(section_id, [])

        ordered.extend(
            sorted(section_items, key=source_position)
        )

    original_ids = sorted(item["id"] for item in evidence)
    ordered_ids = sorted(item["id"] for item in ordered)

    if original_ids != ordered_ids:
        raise ValueError(
            "Une preuve a été perdue ou dupliquée."
        )

    return ordered

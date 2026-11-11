
from answer_stair_ollama import (
    CORPUS_PATH,
    STRUCTURE_PATH,
    LINKS_PATH,
    load,
    sha256,
    format_context,
)
from retrieve_stair_section import (
    build_source_lookup,
    retrieve,
)
from retrieve_stair_hierarchy import (
    build_index_children,
    ordered_sections,
)


def retrieve_multiquery(
    ranked_sections,
    max_roots=2,
    max_context_chars=28000,
):
    """
    Récupère plusieurs sections STAIR classées.

    - Respecte les relations d'index validées.
    - Conserve les continuations entre pages.
    - Évite les extraits documentaires dupliqués.
    - Ne tronque pas les sections.
    - Attribue des citations Sxxx uniques.

    Aucun appel à Ollama.
    """

    if not isinstance(ranked_sections, list):
        raise ValueError("Classement STAIR invalide.")

    if not 1 <= max_roots <= 10:
        raise ValueError("max_roots invalide.")

    if not 1000 <= max_context_chars <= 30000:
        raise ValueError("Budget documentaire invalide.")

    corpus = load(CORPUS_PATH)
    structure = load(STRUCTURE_PATH)
    links = load(LINKS_PATH)

    if links["source"]["corpus_sha256"] != sha256(
        CORPUS_PATH
    ):
        raise ValueError("Version du corpus incohérente.")

    if links["source"]["structure_sha256"] != sha256(
        STRUCTURE_PATH
    ):
        raise ValueError("Version de la structure incohérente.")

    lookup = build_source_lookup(corpus)
    children = build_index_children(structure)

    evidence = []
    retrieved_sections = []
    selected_roots = []
    skipped_roots = []

    seen_elements = set()
    seen_sections = set()

    for candidate in ranked_sections:
        if len(selected_roots) >= max_roots:
            break

        root_id = candidate["id"]

        if root_id in seen_sections:
            continue

        section_ids = ordered_sections(
            root_id,
            children,
        )

        pending = []
        pending_sections = []
        pending_seen = set()

        for section_id in section_ids:
            if section_id in seen_sections:
                continue

            section, blocks, _ = retrieve(
                section_id,
                structure,
                links,
                lookup,
            )

            pending_sections.append({
                "id": section["id"],
                "title": section["title"],
                "pdf_page": section["pdf_page"],
            })

            for block in blocks:
                identity = tuple(block["source_refs"])

                if (
                    identity in seen_elements
                    or identity in pending_seen
                ):
                    continue

                pending_seen.add(identity)

                pending.append({
                    "page": block["page"],
                    "section_id": section_id,
                    "section_title": section["title"],
                    "text": block["text"].strip(),
                    "source_refs": block["source_refs"],
                })

        if not pending:
            continue

        tentative = list(evidence)

        for block in pending:
            tentative.append({
                **block,
                "id": f"S{len(tentative) + 1:03d}",
            })

        try:
            context = format_context(tentative)
        except ValueError:
            skipped_roots.append({
                "id": root_id,
                "reason": "limite de contexte",
            })
            continue

        if len(context) > max_context_chars:
            skipped_roots.append({
                "id": root_id,
                "reason": "budget documentaire",
            })
            continue

        evidence = tentative

        seen_elements.update(pending_seen)
        seen_sections.update(
            item["id"] for item in pending_sections
        )

        retrieved_sections.extend(pending_sections)
        selected_roots.append({
            "id": root_id,
            "title": candidate["title"],
            "combined_score": candidate.get(
                "combined_score"
            ),
        })

    return {
        "selected_roots": selected_roots,
        "sections": retrieved_sections,
        "evidence": evidence,
        "skipped_roots": skipped_roots,
    }

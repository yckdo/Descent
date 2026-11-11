
from answer_stair_ollama import (
    CORPUS_PATH,
    STRUCTURE_PATH,
    load,
    format_context,
)
from search_stair_content import search_content


def retrieve_hybrid(stair_result, queries, max_extra=5,
                    max_context_chars=28000):
    """
    Fusionne les extraits STAIR et les résultats de
    recherche textuelle Docling.

    Ne garantit pas la pertinence sémantique.
    """

    if not isinstance(stair_result, dict):
        raise ValueError("Résultat STAIR invalide.")

    if not 0 <= max_extra <= 20:
        raise ValueError("max_extra invalide.")

    if not 1000 <= max_context_chars <= 30000:
        raise ValueError("Budget documentaire invalide.")

    corpus = load(CORPUS_PATH)
    structure = load(STRUCTURE_PATH)

    # Références Docling vers sections STAIR.
    owners = {}

    for section in structure["sections"]:
        refs = (
            section.get("heading_refs", [])
            + section.get("content_refs", [])
        )

        for ref in refs:
            owners.setdefault(ref, []).append(section)

    # Labels des éléments normalisés.
    labels = {}

    for page in corpus["pages"]:
        for element in page["elements"]:
            for ref in element.get("source_refs", []):
                labels[ref] = element.get("label")

    evidence = [dict(item) for item in stair_result["evidence"]]

    seen_refs = {
        ref
        for item in evidence
        for ref in item["source_refs"]
    }

    added = []
    skipped = []

    results = search_content(queries, limit=30)

    for result in results:
        if len(added) >= max_extra:
            break

        refs = result["source_refs"]

        # Exclure tous les éléments déjà présents,
        # même en cas de références partielles communes.
        if any(ref in seen_refs for ref in refs):
            continue

        # Ne pas ajouter les titres isolés.
        if any(
            labels.get(ref) in {
                "section_header",
                "page_header",
                "page_footer",
            }
            for ref in refs
        ):
            continue

        # Conserver le rattachement s'il existe.
        matching_sections = []

        for ref in refs:
            matching_sections.extend(
                owners.get(ref, [])
            )

        if matching_sections:
            section = matching_sections[0]
            section_id = section["id"]
            section_title = section["title"]
        else:
            section_id = None
            section_title = "Passage Docling non rattaché"

        candidate = {
            "id": f"S{len(evidence) + 1:03d}",
            "page": result["page"],
            "section_id": section_id,
            "section_title": section_title,
            "text": result["text"].strip(),
            "source_refs": refs,
        }

        tentative = evidence + [candidate]

        try:
            context = format_context(tentative)
        except ValueError:
            skipped.append({
                "refs": refs,
                "reason": "limite du contexte",
            })
            continue

        if len(context) > max_context_chars:
            skipped.append({
                "refs": refs,
                "reason": "budget documentaire",
            })
            continue

        evidence.append(candidate)
        seen_refs.update(refs)

        added.append({
            "id": candidate["id"],
            "source_refs": refs,
            "section_id": section_id,
            "section_title": section_title,
            "score": result["score"],
        })

    return {
        "evidence": evidence,
        "selected_roots": stair_result["selected_roots"],
        "sections": stair_result["sections"],
        "added": added,
        "skipped": skipped,
    }

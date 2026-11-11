import re

from answer_stair_ollama import format_context


def merge_concept_evidence(
    evidence,
    complements,
    max_context_chars=28000,
):
    merged = [dict(item) for item in evidence]

    existing_refs = {
        ref
        for item in merged
        for ref in item.get("source_refs", [])
    }

    existing_numbers = [
        int(match.group(1))
        for item in merged
        if (match := re.fullmatch(
            r"S(\d+)", str(item.get("id", ""))
        ))
    ]

    next_number = max(existing_numbers, default=0) + 1

    added = []

    for item in complements:
        refs = item.get("source_refs", [])

        if not refs or any(
            ref in existing_refs for ref in refs
        ):
            continue

        candidate = {
            "id": f"S{next_number:03d}",
            "page": item["page"],
            "section_id": "concept_search",
            "section_title": "Recherche documentaire complémentaire",
            "text": item["text"],
            "source_refs": refs,
        }

        trial = merged + [candidate]

        try:
            context = format_context(trial)
        except (AssertionError, ValueError):
            continue

        if len(context) > max_context_chars:
            continue

        merged.append(candidate)
        added.append(candidate)

        existing_refs.update(refs)
        next_number += 1

    return {
        "evidence": merged,
        "added": added,
        "context": format_context(merged),
    }

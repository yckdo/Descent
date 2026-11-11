import json
import re
from functools import lru_cache
from pathlib import Path

from normalize_stair_concepts import extract_concepts, normalize_word


CORPUS_PATH = Path("data/normalized/descent_rulebook.json")

IGNORED_LABELS = {
    "section_header",
    "page_header",
    "page_footer",
}


def concept_terms(text):
    words = re.findall(r"[a-z]+", text.lower())
    return {
        normalize_word(word)
        for word in words
        if word
    }


@lru_cache(maxsize=1)
def load_passages():
    corpus = json.loads(
        CORPUS_PATH.read_text(encoding="utf-8")
    )

    passages = []

    for page in corpus["pages"]:
        for element in page["elements"]:
            text = element.get("text", "")

            if not isinstance(text, str) or not text.strip():
                continue

            if element.get("label") in IGNORED_LABELS:
                continue

            refs = element.get("source_refs", [])
            if not refs:
                continue

            passages.append({
                "page": element.get("page"),
                "source_refs": refs,
                "text": text,
                "terms": concept_terms(text),
            })

    return passages


def retrieve_concept_complements(
    queries,
    existing_evidence,
    max_extra=5,
):
    concepts = extract_concepts(queries)

    existing_refs = {
        ref
        for item in existing_evidence
        for ref in item.get("source_refs", [])
    }

    candidates = []

    for passage in load_passages():
        refs = passage["source_refs"]

        if any(ref in existing_refs for ref in refs):
            continue

        matches = set(concepts) & passage["terms"]

        if len(matches) < 2:
            continue

        candidates.append({
            "page": passage["page"],
            "source_refs": refs,
            "text": passage["text"],
            "matched_concepts": sorted(matches),
            "score": len(matches),
        })

    candidates.sort(
        key=lambda item: (
            -item["score"],
            len(item["text"]),
        )
    )

    return {
        "concepts": concepts,
        "evidence": candidates[:max_extra],
        "candidate_count": len(candidates),
    }

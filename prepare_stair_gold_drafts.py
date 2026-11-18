"""Build private STAIR evaluation drafts from retrieved local sections.

The manual is read locally and NEVER committed. Drafts are unreviewed.
"""
import argparse
import hashlib
import json
from pathlib import Path
from retrieve_stair_section import (
    ROOT, CORPUS_PATH, STRUCTURE_PATH, LINKS_PATH,
    build_source_lookup, retrieve, load, sha256,
)

PRIVATE_ROOT = ROOT / "validation" / "semantic_gold_drafts"


def build_draft(section_id, corpus, structure, links, max_blocks=6):
    if not isinstance(section_id, str) or not section_id:
        raise ValueError("Invalid section id")
    if not isinstance(max_blocks, int) or max_blocks not in range(1, 13):
        raise ValueError("max_blocks must be from 1 to 12")
    lookup = build_source_lookup(corpus)
    section, blocks, _ = retrieve(section_id, structure, links, lookup)
    blocks = [block for block in blocks if isinstance(block.get("text"), str) and block["text"].strip()][:max_blocks]
    if not blocks:
        raise ValueError("No textual evidence")
    evidence, hashes = [], {}
    for index, block in enumerate(blocks, 1):
        source_id = f"S{index:03d}"
        text = block["text"].strip()
        evidence.append({"id": source_id, "text": text, "page": block["page"],
                         "source_refs": block["source_refs"],
                         "section_id": section_id, "section_title": section["title"]})
        hashes[source_id] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {"case_id": "descent_" + section_id, "annotation_status": "pending_review",
            "reviewer": "", "evidence": evidence, "evidence_hashes": hashes,
            "proposals": {"rules": []}, "gold_rules": [],
            "review_notes": "Read source and adjacent rules independently of Qwen; verify exceptions and applicability."}


def private_path(path, *, root=ROOT):
    private_root = (root / "validation").resolve()
    path = path.resolve()
    if private_root not in path.parents:
        raise ValueError("Output must be inside private validation/")
    return path


def save_draft(draft, output, *, root=ROOT):
    path = private_path(output, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Do not overwrite any existing review.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(draft, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("section_ids", nargs="+")
    parser.add_argument("--max-blocks", type=int, default=6)
    args = parser.parse_args()
    corpus, structure, links = load(CORPUS_PATH), load(STRUCTURE_PATH), load(LINKS_PATH)
    if links["source"]["corpus_sha256"] != sha256(CORPUS_PATH):
        raise ValueError("Corpus SHA-256 mismatch")
    if links["source"]["structure_sha256"] != sha256(STRUCTURE_PATH):
        raise ValueError("Structure SHA-256 mismatch")
    for sid in args.section_ids:
        draft = build_draft(sid, corpus, structure, links, args.max_blocks)
        dest = save_draft(draft, PRIVATE_ROOT / (draft["case_id"] + ".json"))
        print(f"Draft created: {dest.name}, {len(draft['evidence'])} passages (pending_review)")


if __name__ == "__main__":
    main()

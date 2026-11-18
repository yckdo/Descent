import json
import tempfile
import unittest
from pathlib import Path
from prepare_stair_gold_drafts import build_draft, save_draft


def synthetic_stair():
    ref_h = "#/texts/1"
    ref_b = "#/texts/2"
    corpus = {"pages": [{"elements": [
        {"text": "Movement", "page": 1, "source_refs": [ref_h], "label": "section_header"},
        {"text": "A hero may move through an ally but cannot stop there.",
         "page": 1, "source_refs": [ref_b], "label": "text"},
    ]}]}
    structure = {"sections": [{
        "id": "sec_0001", "title": "Movement", "pdf_page": 1,
        "heading_refs": [ref_h], "content_refs": [ref_b],
        "content_element_count": 1,
    }]}
    links = {"links": []}
    return corpus, structure, links


class STAIRRealPipelineContractTests(unittest.TestCase):
    def test_retrieve_stair_into_draft(self):
        draft = build_draft("sec_0001", *synthetic_stair())
        self.assertEqual(draft["annotation_status"], "pending_review")
        self.assertEqual(draft["evidence"][0]["source_refs"], ["#/texts/2"])
        self.assertEqual(draft["evidence"][0]["page"], 1)
        self.assertEqual(draft["gold_rules"], [])
        self.assertEqual(draft["proposals"], {"rules": []})

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            build_draft("sec_unknown", *synthetic_stair())

    def test_private_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            draft = build_draft("sec_0001", *synthetic_stair())
            with self.assertRaises(ValueError):
                save_draft(draft, root / "docs" / "leak.json", root=root)

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            draft = build_draft("sec_0001", *synthetic_stair())
            dest = root / "validation" / "semantic_gold_drafts" / "test.json"
            save_draft(draft, dest, root=root)
            with self.assertRaises(FileExistsError):
                save_draft(draft, dest, root=root)
            self.assertEqual(json.loads(dest.read_text())["annotation_status"], "pending_review")

    def test_fingerprint_stable(self):
        import hashlib
        draft = build_draft("sec_0001", *synthetic_stair())
        source = draft["evidence"][0]
        self.assertEqual(draft["evidence_hashes"][source["id"]],
                         hashlib.sha256(source["text"].encode()).hexdigest())

    def test_bad_max_blocks(self):
        with self.assertRaises(ValueError):
            build_draft("sec_0001", *synthetic_stair(), max_blocks=0)


if __name__ == "__main__":
    unittest.main()

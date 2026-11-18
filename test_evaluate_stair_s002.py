import hashlib
import unittest

from evaluate_stair_s002 import run_case, REF, SECTION


TEXT = ("A figure can pass through a friendly figure. "
        "A figure cannot end movement in another figure's space.")


def example():
    return {
        "case_id": SECTION,
        "evidence": [{"id": "S002", "text": TEXT, "page": 8,
                      "source_refs": [REF]}],
        "evidence_hashes": {"S002": hashlib.sha256(TEXT.encode()).hexdigest()},
    }


class S002ExperimentTests(unittest.TestCase):
    def test_provisional_reasoning(self):
        result = run_case(example())
        self.assertEqual(result["logical_demonstration"]["traverse"]["status"], "supported")
        self.assertEqual(result["logical_demonstration"]["finish"]["status"], "refuted")
        self.assertFalse(result["automatic_approval"])
        self.assertEqual(result["reference_review_status"], "provisional")

    def test_wrong_docling_reference_rejected(self):
        case = example()
        case["evidence"][0]["source_refs"] = ["#/texts/999"]
        with self.assertRaises(ValueError):
            run_case(case)

    def test_wrong_page_rejected(self):
        case = example()
        case["evidence"][0]["page"] = 99
        with self.assertRaises(ValueError):
            run_case(case)

    def test_wrong_section_rejected(self):
        case = example()
        case["case_id"] = "other"
        with self.assertRaises(ValueError):
            run_case(case)

    def test_tampered_evidence_hash_rejected(self):
        case = example()
        case["evidence"][0]["text"] += "Modified."
        with self.assertRaises(ValueError):
            run_case(case)

    def test_no_model_call_without_extractor(self):
        result = run_case(example())
        self.assertEqual(result["agreement"]["false_negative"], 2)

    def test_extractor_cannot_approve(self):
        def model(messages):
            return {"rules": []}
        result = run_case(example(), extractor=model)
        self.assertFalse(result["automatic_approval"])


if __name__ == "__main__":
    unittest.main()

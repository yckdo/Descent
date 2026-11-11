import unittest

from validate_stair_evidence import audit_evidence


class TestEvidenceMissingSections(unittest.TestCase):

    def test_missing_section_id(self):
        evidence = [
            {
                "id": "S001",
                "page": 10,
                "section_id": None,
            },
            {
                "id": "S002",
                "page": 11,
                "section_id": "sec_test",
            },
        ]

        answer = {
            "points": [
                {
                    "text": "Réponse de test.",
                    "source_ids": ["S001", "S002"],
                }
            ]
        }

        result = audit_evidence(answer, evidence)

        self.assertTrue(result["valid"])
        self.assertEqual(
            result["cited_sections"],
            ["sec_test"],
        )
        self.assertEqual(
            result["points"][0]["sections"],
            ["sec_test"],
        )


if __name__ == "__main__":
    unittest.main()

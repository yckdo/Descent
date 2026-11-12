import unittest
import hashlib
import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from web_app import app


TEST_TOKEN = "descent-test-only-token"
TEST_HASH = hashlib.sha256(TEST_TOKEN.encode()).hexdigest()


class TestAPIFunctional(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def check_answer(self, question, expected_origin):
        with patch.dict(os.environ, {
            "DESCENT_BETA_REQUIRE_AUTH": "1",
            "DESCENT_BETA_TOKEN_HASHES": TEST_HASH,
        }):
            response = self.client.post(
                "/api/ask",
                json={"question": question},
                headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            )

        self.assertEqual(
            response.status_code,
            200,
            response.text,
        )

        data = response.json()

        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(
            data.get("answer_origin"),
            expected_origin,
        )

        self.assertTrue(data.get("points"))
        self.assertTrue(
            (data.get("citation_audit") or {}).get("valid")
        )

        for point in data["points"]:
            self.assertTrue(point.get("text"))
            self.assertTrue(point.get("source_ids"))
            self.assertTrue(point.get("pdf_pages"))

        return data

    def test_open_chat(self):
        data = self.check_answer(
            "Est-ce que mon héros peut attaquer deux fois pendant son tour ?",
            "generated",
        )
        print("\nChat ouvert :", len(data["points"]), "points")

    def test_boutique(self):
        data = self.check_answer(
            "Comment fonctionne la boutique ?",
            "reviewed",
        )

        coverage = data.get("coverage_audit") or {}

        self.assertEqual(coverage.get("rules_flagged"), 0)

        print("\nBoutique :", len(data["points"]), "points")


if __name__ == "__main__":
    unittest.main()

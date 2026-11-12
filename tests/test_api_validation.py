import unittest
import hashlib
import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from web_app import app


TEST_TOKEN = "descent-test-validation-only"
TEST_HASH = hashlib.sha256(TEST_TOKEN.encode()).hexdigest()


class TestAPIValidation(unittest.TestCase):

    def test_invalid_questions(self):
        cases = [
            ("question vide", {"question": ""}, 422),
            ("question courte", {"question": "a"}, 422),
            ("champ manquant", {}, 422),
            ("valeur numérique", {"question": 123}, 422),
            ("espaces", {"question": "   "}, 400),
        ]

        with patch.dict(os.environ, {
            "DESCENT_BETA_REQUIRE_AUTH": "1",
            "DESCENT_BETA_TOKEN_HASHES": TEST_HASH,
        }):
            with TestClient(app) as client:
                for name, payload, expected in cases:
                    with self.subTest(name=name):
                        response = client.post(
                            "/api/ask",
                            json=payload,
                            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
                        )
                        self.assertEqual(
                            response.status_code,
                            expected,
                        )

    def test_health(self):
        with TestClient(app) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json()["status"],
                "ok",
            )


if __name__ == "__main__":
    unittest.main()

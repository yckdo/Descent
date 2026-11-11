import hashlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from beta_feedback import install_beta_feedback


class BetaFeedbackTests(unittest.TestCase):
    def test_auth_feedback_and_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = "un-code-pilote-de-test"
            env = {
                "DESCENT_BETA_REQUIRE_AUTH": "1",
                "DESCENT_BETA_TOKEN_HASHES": hashlib.sha256(key.encode()).hexdigest(),
                "DESCENT_BETA_FEEDBACK_DB": str(Path(tmp) / "feedback.sqlite3"),
            }
            with patch.dict(os.environ, env):
                app = FastAPI()
                install_beta_feedback(app)
                with TestClient(app) as client:
                    body = {"verdict": "incorrect", "question": "Une règle est-elle correcte ?", "answer": {"points": [{"text": "Non", "source_ids": ["S001"]}]}, "comment": "À vérifier"}
                    self.assertEqual(client.post("/api/feedback", json=body).status_code, 401)
                    r = client.post("/api/feedback", json=body, headers={"Authorization": f"Bearer {key}"})
                    self.assertEqual(r.status_code, 201, r.text)
                    self.assertEqual(r.json()["status"], "recorded")
                    with sqlite3.connect(env["DESCENT_BETA_FEEDBACK_DB"]) as db:
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM incorrect_feedback").fetchone()[0], 1)
                    preflight = client.options("/api/feedback", headers={"Origin":"https://yckdo.github.io", "Access-Control-Request-Method":"POST", "Access-Control-Request-Headers":"authorization,content-type"})
                    self.assertEqual(preflight.status_code, 200, preflight.text)
                    self.assertEqual(preflight.headers.get("access-control-allow-origin"), "https://yckdo.github.io")


if __name__ == "__main__":
    unittest.main()

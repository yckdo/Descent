import unittest
from stair_reasoner import reason
from stair_shadow import compare_observation


class ReasoningTests(unittest.TestCase):
    def test_chain(self):
        spec = {"facts": [{"literal": "a", "source": "f"}],
                "rules": [{"id": "r1", "if": ["a"], "then": "b", "source": "s"},
                          {"id": "r2", "if": ["b"], "then": "c", "source": "s"}], "query": "c"}
        self.assertEqual(reason(spec)["status"], "supported")
        self.assertEqual(len(reason(spec)["proof_graph"]), 3)

    def test_refuted(self):
        self.assertEqual(reason({"facts": [{"literal": "!a", "source": "s"}], "query": "a"})["status"], "refuted")

    def test_contradicted(self):
        self.assertEqual(reason({"facts": [{"literal": "a", "source": "s"},
                                          {"literal": "!a", "source": "s"}], "query": "a"})["status"], "contradicted")

    def test_unknown(self):
        self.assertEqual(reason({"query": "a"})["status"], "uncertain")

    def test_cycle(self):
        self.assertEqual(reason({"query": "a", "rules": [
            {"id": "a", "if": ["b"], "then": "a", "source": "s"},
            {"id": "b", "if": ["a"], "then": "b", "source": "s"}]})["status"], "uncertain")

    def test_missing_source(self):
        with self.assertRaises(ValueError):
            reason({"query": "a", "facts": [{"literal": "a", "source": ""}]})

    def test_duplicate_id(self):
        r = {"id": "x", "if": ["a"], "then": "b", "source": "s"}
        with self.assertRaises(ValueError):
            reason({"query": "b", "rules": [r, r]})

    def test_disabled(self):
        self.assertEqual(compare_observation("original")["shadow"]["status"], "not_run")

    def test_no_spec(self):
        self.assertEqual(compare_observation("original", shadow_enabled=True)["shadow"]["status"], "no_spec")

    def test_failure_keeps_answer(self):
        self.assertEqual(compare_observation("original", {"query": ""}, shadow_enabled=True)["rag_response"], "original")

    def test_success_keeps_answer(self):
        self.assertEqual(compare_observation("original", {"query": "a"}, shadow_enabled=True)["rag_response"], "original")

    def test_success_status(self):
        self.assertEqual(compare_observation("original", {"query": "a"}, shadow_enabled=True)["shadow"]["reasoner_status"], "uncertain")


if __name__ == "__main__":
    unittest.main()

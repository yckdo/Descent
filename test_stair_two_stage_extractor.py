import unittest
from stair_two_stage_extractor import extract_two_stage, STATEMENT_SCHEMA

E = [{"id": "S002", "text": "A hero may pass through friendly figures. A figure cannot end movement in another figure's space.",
      "page": 8, "source_refs": ["#/texts/263"]}]
QUOTE = "A hero may pass through friendly figures."
STATEMENT = {"evidence_id": "S002", "quote": QUOTE,
             "interpretation": "A hero can pass through a friendly figure", "kind": "permission"}
RULE = {"id": "rule1", "if": ["hero_moves", "target_is_friendly"],
        "then": "may_pass_through", "evidence_id": "S002", "quote": QUOTE}


class TwoStageTests(unittest.TestCase):
    def test_schema(self):
        self.assertEqual(STATEMENT_SCHEMA["required"], ["statements"])

    def test_two_stage_happy_path_not_approved(self):
        calls = []
        def fake(messages, schema, key):
            calls.append(key)
            return {"statements": [STATEMENT]} if key == "statements" else {"rules": [RULE]}
        result = extract_two_stage(E, caller=fake)
        self.assertEqual(calls, ["statements", "rules"])
        self.assertEqual(result["diagnostic"]["stage2_accepted"], 1)
        self.assertFalse(result["diagnostic"]["semantically_verified"])
        self.assertEqual(result["candidates"][0]["review_status"], "proposed")

    def test_empty_comprehension_no_second_call(self):
        def fake(messages, schema, key):
            self.assertEqual(key, "statements")
            return {"statements": []}
        result = extract_two_stage(E, caller=fake)
        self.assertEqual(result["status"], "stage1_empty_or_invalid")

    def test_unanchored_comprehension_not_formalized(self):
        def fake(messages, schema, key):
            self.assertEqual(key, "statements")
            return {"statements": [dict(STATEMENT, quote="An invented source sentence.")]}
        self.assertEqual(extract_two_stage(E, caller=fake)["diagnostic"]["stage1_anchored"], 0)

    def test_second_stage_cannot_change_quote(self):
        def fake(messages, schema, key):
            if key == "statements":
                return {"statements": [STATEMENT]}
            return {"rules": [dict(RULE, quote="A figure cannot end movement in another figure's space.")]}
        result = extract_two_stage(E, caller=fake)
        self.assertEqual(result["diagnostic"]["stage2_accepted"], 0)
        self.assertEqual(result["diagnostic"]["stage2_rejected"], 1)

    def test_stage_one_malformed(self):
        with self.assertRaises(ValueError):
            extract_two_stage(E, caller=lambda *args: {})

    def test_stage_two_malformed(self):
        def fake(messages, schema, key):
            return {"statements": [STATEMENT]} if key == "statements" else {}
        with self.assertRaises(ValueError):
            extract_two_stage(E, caller=fake)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            extract_two_stage([])
        with self.assertRaises(ValueError):
            extract_two_stage([E[0], E[0]])

    def test_diagnostics_no_raw_quotes(self):
        def fake(messages, schema, key):
            return {"statements": [STATEMENT]} if key == "statements" else {"rules": [RULE]}
        result = extract_two_stage(E, caller=fake)
        self.assertNotIn(QUOTE, str(result["diagnostic"]))

    def test_stage_one_bad_id_type(self):
        bad = dict(STATEMENT, evidence_id=["S002"])
        def fake(messages, schema, key):
            self.assertEqual(key, "statements")
            return {"statements": [bad]}
        self.assertEqual(extract_two_stage(E, caller=fake)["diagnostic"]["stage1_rejected"], 1)


if __name__ == "__main__":
    unittest.main()

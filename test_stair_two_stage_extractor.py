import json
import unittest

from stair_two_stage_extractor import extract_two_stage, STATEMENT_SCHEMA, FORMALIZATION_SCHEMA

E = [{"id": "S002",
      "text": "A hero may pass through friendly figures. A figure cannot end movement in another figure's space.",
      "page": 8, "source_refs": ["#/texts/263"]}]
QUOTE = "A hero may pass through friendly figures."
OTHER_QUOTE = "A figure cannot end movement in another figure's space."
STATEMENT = {"evidence_id": "S002", "quote": QUOTE,
             "interpretation": "A hero can pass through a friendly figure", "kind": "permission"}
RULE = {"statement_id": "P001", "id": "rule1",
        "if": ["hero_moves", "target_is_friendly"], "then": "may_pass_through"}


def caller_for(statements, rules):
    def fake(messages, schema, key):
        if key == "statements":
            return {"statements": statements}
        assert schema == FORMALIZATION_SCHEMA
        assert "statement_id" in messages[1]["content"]
        return {"rules": rules}
    return fake


class TwoStageTests(unittest.TestCase):
    def test_schemas(self):
        self.assertEqual(STATEMENT_SCHEMA["required"], ["statements"])
        self.assertEqual(FORMALIZATION_SCHEMA["required"], ["rules"])
        self.assertNotIn("quote", FORMALIZATION_SCHEMA["properties"]["rules"]["items"]["properties"])
        self.assertNotIn("evidence_id", FORMALIZATION_SCHEMA["properties"]["rules"]["items"]["properties"])

    def test_happy_path_never_approved(self):
        result = extract_two_stage(E, caller=caller_for([STATEMENT], [RULE]))
        self.assertEqual(result["diagnostic"]["stage2_accepted"], 1)
        self.assertEqual(result["diagnostic"]["stage1_unrepresented_count"], 0)
        self.assertFalse(result["diagnostic"]["semantically_verified"])
        self.assertTrue(result["diagnostic"]["review_required"])
        self.assertEqual(result["candidates"][0]["quote"], QUOTE)
        self.assertEqual(result["candidates"][0]["source"], "S002")
        self.assertEqual(result["candidates"][0]["review_status"], "proposed")

    def test_exact_original_quote_not_supplied_by_stage_two(self):
        def fake(messages, schema, key):
            if key == "statements":
                return {"statements": [STATEMENT]}
            self.assertIn('"statement_id": "P001"', messages[1]["content"])
            return {"rules": [RULE]}
        result = extract_two_stage(E, caller=fake)
        self.assertEqual(result["candidates"][0]["quote"], QUOTE)

    def test_two_distinct_statements_sharing_a_quote(self):
        second = dict(STATEMENT, interpretation="Different rule", kind="condition")
        other_rule = dict(RULE, statement_id="P002", id="rule2",
                          then="second_effect")
        result = extract_two_stage(E, caller=caller_for([STATEMENT, second], [RULE, other_rule]))
        self.assertEqual(result["diagnostic"]["stage2_accepted"], 2)
        self.assertEqual(result["diagnostic"]["stage1_unrepresented_count"], 0)

    def test_missing_permission_detected(self):
        second = dict(STATEMENT, quote=OTHER_QUOTE, interpretation="Cannot end there", kind="prohibition")
        result = extract_two_stage(E, caller=caller_for([STATEMENT, second], [
            dict(RULE, statement_id="P002", id="rule2", then="cannot_end")
        ]))
        self.assertEqual(result["diagnostic"]["stage1_unrepresented_indices"], [1])
        self.assertEqual(result["diagnostic"]["stage1_unrepresented_kinds"], ["permission"])
        self.assertEqual(result["diagnostic"]["coverage_basis"], "stable_statement_id_only")

    def test_unknown_statement_id_cannot_borrow_quote(self):
        result = extract_two_stage(E, caller=caller_for([STATEMENT], [
            dict(RULE, statement_id="P999")
        ]))
        self.assertEqual(result["diagnostic"]["stage2_rejection_reasons"]["unknown_statement_id"], 1)
        self.assertEqual(result["diagnostic"]["stage1_unrepresented_count"], 1)
        self.assertEqual(result["candidates"], [])

    def test_duplicate_statement_id_is_blocked(self):
        result = extract_two_stage(E, caller=caller_for([STATEMENT], [RULE, dict(RULE, id="rule2")]))
        self.assertEqual(result["diagnostic"]["stage2_accepted"], 1)
        self.assertEqual(result["diagnostic"]["stage2_rejection_reasons"]["duplicate_statement_id"], 1)

    def test_duplicate_rule_ids_do_not_mark_both_statements_accepted(self):
        second = dict(STATEMENT, quote=OTHER_QUOTE, interpretation="Cannot end there", kind="prohibition")
        result = extract_two_stage(E, caller=caller_for([STATEMENT, second], [
            RULE, dict(RULE, statement_id="P002")
        ]))
        self.assertEqual(result["diagnostic"]["stage2_accepted"], 1)
        self.assertEqual(result["diagnostic"]["stage1_unrepresented_indices"], [2])

    def test_invalid_atom_is_rejected(self):
        result = extract_two_stage(E, caller=caller_for([STATEMENT], [
            dict(RULE, then="invalid atom")
        ]))
        self.assertEqual(result["diagnostic"]["stage2_rejection_reasons"]["invalid_structure_or_provenance"], 1)
        self.assertEqual(result["diagnostic"]["stage1_unrepresented_count"], 1)

    def test_empty_does_not_call_second_stage(self):
        def fake(messages, schema, key):
            self.assertEqual(key, "statements")
            return {"statements": []}
        self.assertEqual(extract_two_stage(E, caller=fake)["status"], "stage1_empty_or_invalid")

    def test_unanchored_first_stage_is_blocked(self):
        statement = dict(STATEMENT, quote="A sentence which has no source at all.")
        result = extract_two_stage(E, caller=caller_for([statement], []))
        self.assertEqual(result["diagnostic"]["stage1_anchored"], 0)

    def test_malformed_stage_one(self):
        with self.assertRaises(ValueError):
            extract_two_stage(E, caller=lambda *args: {})

    def test_malformed_stage_two(self):
        def fake(messages, schema, key):
            return {"statements": [STATEMENT]} if key == "statements" else {}
        with self.assertRaises(ValueError):
            extract_two_stage(E, caller=fake)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            extract_two_stage([])
        with self.assertRaises(ValueError):
            extract_two_stage([E[0], E[0]])

    def test_diagnostic_does_not_leak_passages(self):
        result = extract_two_stage(E, caller=caller_for([STATEMENT], [RULE]))
        self.assertNotIn(QUOTE, json.dumps(result["diagnostic"]))
        self.assertNotIn(OTHER_QUOTE, json.dumps(result["diagnostic"]))

    def test_stage_one_bad_id_type(self):
        bad = dict(STATEMENT, evidence_id=["S002"])
        result = extract_two_stage(E, caller=caller_for([bad], []))
        self.assertEqual(result["diagnostic"]["stage1_rejected"], 1)

    def test_model_cannot_override_source_fields(self):
        proposal = dict(RULE, evidence_id="S999", quote=OTHER_QUOTE)
        result = extract_two_stage(E, caller=caller_for([STATEMENT], [proposal]))
        self.assertEqual(result["candidates"][0]["source"], "S002")
        self.assertEqual(result["candidates"][0]["quote"], QUOTE)


    def test_expected_kinds_detect_stage_one_omission(self):
        result = extract_two_stage(
            E, caller=caller_for([STATEMENT], [RULE]),
            expected_kinds=("permission", "prohibition"),
        )
        diag = result["diagnostic"]
        self.assertEqual(diag["missing_expected_stage1_kinds"], ["prohibition"])
        self.assertEqual(diag["missing_expected_stage2_kinds"], ["prohibition"])
        self.assertFalse(diag["expected_kind_coverage"])
        self.assertFalse(diag["semantically_verified"])

    def test_expected_kinds_detect_stage_two_omission(self):
        prohibition = dict(STATEMENT, quote=OTHER_QUOTE,
                           interpretation="Cannot end there", kind="prohibition")
        result = extract_two_stage(
            E, caller=caller_for([STATEMENT, prohibition], [RULE]),
            expected_kinds=("permission", "prohibition"),
        )
        diag = result["diagnostic"]
        self.assertEqual(diag["missing_expected_stage1_kinds"], [])
        self.assertEqual(diag["missing_expected_stage2_kinds"], ["prohibition"])
        self.assertFalse(diag["expected_kind_coverage"])

    def test_expected_kinds_complete_is_not_semantic_approval(self):
        prohibition = dict(STATEMENT, quote=OTHER_QUOTE,
                           interpretation="Cannot end there", kind="prohibition")
        prohibition_rule = dict(RULE, statement_id="P002", id="rule2",
                                then="cannot_end")
        result = extract_two_stage(
            E, caller=caller_for([STATEMENT, prohibition], [RULE, prohibition_rule]),
            expected_kinds=("permission", "prohibition"),
        )
        diag = result["diagnostic"]
        self.assertEqual(diag["missing_expected_stage1_kinds"], [])
        self.assertEqual(diag["missing_expected_stage2_kinds"], [])
        self.assertTrue(diag["expected_kind_coverage"])
        self.assertFalse(diag["semantically_verified"])
        self.assertTrue(diag["review_required"])

    def test_empty_stage_one_flags_both_expected_kinds(self):
        result = extract_two_stage(
            E, caller=lambda messages, schema, key: {"statements": []},
            expected_kinds=("permission", "prohibition"),
        )
        self.assertEqual(
            result["diagnostic"]["missing_expected_stage1_kinds"],
            ["permission", "prohibition"],
        )
        self.assertFalse(result["diagnostic"]["expected_kind_coverage"])

    def test_duplicate_and_unknown_expected_kinds_rejected(self):
        for expected in [("permission", "permission"), ("unsupported",), "permission"]:
            with self.subTest(expected=expected):
                with self.assertRaises(ValueError):
                    extract_two_stage(E, caller=caller_for([], []),
                                      expected_kinds=expected)

    def test_expected_kind_diagnostics_contain_no_manual_text(self):
        prohibition = dict(STATEMENT, quote=OTHER_QUOTE,
                           interpretation="Cannot end there", kind="prohibition")
        result = extract_two_stage(
            E, caller=caller_for([STATEMENT, prohibition], [RULE]),
            expected_kinds=("permission", "prohibition"),
        )
        diagnostic = json.dumps(result["diagnostic"])
        self.assertNotIn(QUOTE, diagnostic)
        self.assertNotIn(OTHER_QUOTE, diagnostic)


if __name__ == "__main__":
    unittest.main()

import hashlib
import unittest

from stair_semantic_benchmark import evaluate_case, evaluate_suite


TEXT = ("If a hero is poisoned, the hero must check healing before the "
        "effect resolves. Unless the hero has an antidote, the check is required.")
EVIDENCE = [{
    "id": "S001", "text": TEXT,
    "page": 7, "source_refs": ["#/texts/40"],
}]
RULE = {
    "id": "r1", "if": ["hero_poisoned", "!hero_has_antidote"],
    "then": "healing_check_required", "evidence_id": "S001",
    "quote": "Unless the hero has an antidote, the check is required.",
}
GOLD = {
    "if": ["hero_poisoned", "!hero_has_antidote"],
    "then": "healing_check_required", "source": "S001",
}


def make_case(*, rules=None, gold=None, text=TEXT):
    evidence = [dict(EVIDENCE[0], text=text)]
    return {
        "case_id": "synthetic_001",
        "annotation_status": "synthetic_reference",
        "reviewer": "synthetic_test_author",
        "evidence": evidence,
        "evidence_hashes": {"S001": hashlib.sha256(text.encode("utf-8")).hexdigest()},
        "proposals": {"rules": [RULE] if rules is None else rules},
        "gold_rules": [GOLD] if gold is None else gold,
    }


class SemanticBenchmarkTests(unittest.TestCase):
    def test_perfect_agreement_not_approval(self):
        result = evaluate_case(make_case())
        self.assertEqual(result["result"], "exact_match")
        self.assertFalse(result["promotable"])

    def test_wrong_conclusion_false_positive_and_negative(self):
        altered = dict(RULE, then="healing_check_not_required")
        result = evaluate_case(make_case(rules=[altered]))
        self.assertEqual(result["false_positive"], 1)
        self.assertEqual(result["false_negative"], 1)

    def test_missing_exception_is_not_exact_match(self):
        altered = dict(RULE, **{"if": ["hero_poisoned"]})
        result = evaluate_case(make_case(rules=[altered]))
        self.assertEqual(result["result"], "mismatch")

    def test_missing_proposal_false_negative(self):
        result = evaluate_case(make_case(rules=[]))
        self.assertEqual(result["false_negative"], 1)

    def test_extra_proposal_false_positive(self):
        altered = dict(RULE, id="r2", then="extra_effect")
        result = evaluate_case(make_case(rules=[RULE, altered]))
        self.assertEqual(result["false_positive"], 1)

    def test_changed_evidence_hash_rejected(self):
        item = make_case()
        item["evidence"][0]["text"] += " Changed."
        with self.assertRaises(ValueError):
            evaluate_case(item)

    def test_requires_annotation_status(self):
        item = make_case()
        item["annotation_status"] = "model_labeled"
        with self.assertRaises(ValueError):
            evaluate_case(item)

    def test_suite_summary(self):
        result = evaluate_suite({"cases": [make_case()]})
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertTrue(result["all_rules_unapproved"])

    def test_duplicate_case_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_suite({"cases": [make_case(), make_case()]})

    def test_absence_of_gold_or_proposal(self):
        result = evaluate_case(make_case(gold=[], rules=[]))
        self.assertEqual(result["result"], "exact_match")
        self.assertFalse(result["promotable"])

    def test_cited_but_invalid_quote_is_rejected(self):
        item = make_case(rules=[dict(RULE, quote="This quote was never in the text")])
        result = evaluate_case(item)
        self.assertEqual(result["rejected_proposals"], 1)
        self.assertEqual(result["false_negative"], 1)


if __name__ == "__main__":
    unittest.main()

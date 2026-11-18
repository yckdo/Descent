import json
import unittest
from unittest.mock import patch
from stair_rule_extractor import RULE_RESPONSE_SCHEMA, _local_ollama, propose_candidates


class _HttpResponse:
    status = 200
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return json.dumps(self.payload).encode("utf-8")


class OllamaSchemaContractTests(unittest.TestCase):
    def test_required_rules_list(self):
        self.assertEqual(RULE_RESPONSE_SCHEMA["required"], ["rules"])

    def test_empty_dict_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "rules list missing"):
            propose_candidates(
                [{"id": "S002", "text": "A sufficiently long source passage.",
                  "source_refs": ["#/texts/263"]}],
                generator=lambda messages: {},
            )

    @patch("urllib.request.urlopen")
    def test_request_supplies_json_schema(self, mocked):
        mocked.return_value = _HttpResponse({
            "message": {"content": '{"rules": []}'},
            "done_reason": "stop",
        })
        result = _local_ollama(
            [{"role": "user", "content": "test"}],
            url="http://127.0.0.1:11434/api/chat",
            model="qwen2.5-coder:14b", timeout=3,
        )
        body = json.loads(mocked.call_args.args[0].data)
        self.assertEqual(body["format"], RULE_RESPONSE_SCHEMA)
        self.assertEqual(result, {"rules": []})

    @patch("urllib.request.urlopen")
    def test_empty_model_output_fails_closed(self, mocked):
        mocked.return_value = _HttpResponse({
            "message": {"content": "{}"},
            "done_reason": "stop",
        })
        with self.assertRaisesRegex(ValueError, "rules list missing"):
            _local_ollama(
                [{"role": "user", "content": "test"}],
                url="http://127.0.0.1:11434/api/chat",
                model="qwen2.5-coder:14b", timeout=3,
            )


if __name__ == "__main__":
    unittest.main()

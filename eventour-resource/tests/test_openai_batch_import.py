from __future__ import annotations

import unittest

from eventour_kg.classification.import_openai_batch_results import import_results


class OpenAIBatchImportTests(unittest.TestCase):
    def test_invalid_structured_output_returns_candidate_exception(self) -> None:
        entity_index = {
            "wd::Q123": {
                "item_qid": "Q123",
                "preferred_label": "Entity Example",
                "description": "example description",
                "city_id": "milan",
            }
        }
        batch_rows = [
            {
                "custom_id": "wd::Q123",
                "response": {
                    "request_id": "req_test",
                    "status_code": 200,
                    "body": {
                        "id": "resp_test",
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": '{"decision": "exclude"',
                                    }
                                ],
                            }
                        ],
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "total_tokens": 120,
                        },
                    },
                },
            }
        ]

        outputs = import_results(
            batch_rows,
            entity_index=entity_index,
            backend_name="openai:gpt-5-mini:batch",
        )

        self.assertEqual(len(outputs), 1)
        row = outputs[0]
        self.assertEqual(row["decision"], "candidate_exception")
        self.assertIsNone(row["eventour_category"])
        self.assertEqual(row["confidence"], 0.0)
        self.assertEqual(row["backend"], "openai:gpt-5-mini:batch")
        self.assertIn("invalid structured output", row["rationale"].lower())
        self.assertEqual(row["backend_metadata"]["response_id"], "resp_test")
        self.assertIn("parse_error", row["backend_metadata"])
        self.assertIn("output_text_preview", row["backend_metadata"])


if __name__ == "__main__":
    unittest.main()

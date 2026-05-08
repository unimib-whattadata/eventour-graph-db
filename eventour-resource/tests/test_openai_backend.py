from __future__ import annotations

import unittest

from eventour_kg.classification.openai_backend import OpenAIBackend


class _FakeContent:
    def __init__(self, *, type: str, text: str | None = None, refusal: str | None = None) -> None:
        self.type = type
        self.text = text
        self.refusal = refusal


class _FakeOutput:
    def __init__(self, *, type: str = "message", content: list[object] | None = None) -> None:
        self.type = type
        self.content = content or []


class _FakeIncompleteDetails:
    def __init__(self, *, reason: str | None = None) -> None:
        self.reason = reason

    def model_dump(self, exclude_none: bool = True) -> dict[str, str | None]:
        return {"reason": self.reason}


class _FakeUsage:
    def __init__(self, *, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def model_dump(self, exclude_none: bool = True) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
        }


class _FakeResponse:
    def __init__(self) -> None:
        self.id = "resp_test_empty"
        self.output_text = ""
        self.output = [_FakeOutput(content=[])]
        self.usage = _FakeUsage(input_tokens=10, output_tokens=0)
        self.status = "incomplete"
        self.error = None
        self.incomplete_details = _FakeIncompleteDetails(reason="max_output_tokens")
        self.model = "gpt-5-mini"

    def model_dump(self, exclude_none: bool = True) -> dict[str, object]:
        return {
            "id": self.id,
            "status": self.status,
            "incomplete_details": {"reason": "max_output_tokens"},
            "output": [{"type": "message", "content": []}],
        }


class _FakeResponsesClient:
    def create(self, **kwargs):  # noqa: ANN003
        return _FakeResponse()


class _FakeClient:
    def __init__(self) -> None:
        self.responses = _FakeResponsesClient()


class OpenAIBackendTests(unittest.TestCase):
    def test_missing_output_text_returns_candidate_exception_instead_of_crashing(self) -> None:
        backend = OpenAIBackend.__new__(OpenAIBackend)
        backend.model = "gpt-5-mini"
        backend.timeout_seconds = 60.0
        backend.max_output_tokens = 320
        backend.backend_name = "openai:gpt-5-mini"
        backend._client = _FakeClient()

        result = backend.classify(
            {
                "city_id": "milan",
                "preferred_label": "Entity Example",
                "description": "example description",
                "classification_payload": {
                    "city_name": "milan",
                    "entity_label": "Entity Example",
                    "entity_description": "example description",
                    "direct_class_labels": ["edificio"],
                    "class_ancestor_labels": ["struttura architettonica"],
                    "semantic_fact_texts": ["architetto: Someone"],
                },
            }
        )

        self.assertEqual(result.decision.value, "candidate_exception")
        self.assertIsNone(result.eventour_category)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("no structured output", result.rationale.lower())
        self.assertEqual(result.metadata["response_id"], "resp_test_empty")
        self.assertEqual(result.metadata["status"], "incomplete")
        self.assertEqual(result.metadata["incomplete_details"], {"reason": "max_output_tokens"})
        self.assertEqual(result.metadata["output_item_types"], ["message"])


if __name__ == "__main__":
    unittest.main()

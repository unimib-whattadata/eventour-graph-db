"""OpenAI-backed semantic classifier for Eventour."""

from __future__ import annotations

import json
import os
from typing import Any

from eventour_kg.classification.openai_structured import (
    coerce_result,
    extract_output_text,
    extract_refusal,
    parse_output_json,
    response_format,
    usage_to_dict,
)
from eventour_kg.classification.policy import ClassificationResult, Decision
from eventour_kg.classification.prompt_builder import build_prompt


DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 320
DEFAULT_TIMEOUT_SECONDS = 60.0


def _dump_object(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return value
    return str(value)


def _output_item_types(response: Any) -> list[str]:
    outputs = getattr(response, "output", None) or []
    item_types: list[str] = []
    for output in outputs:
        output_type = getattr(output, "type", None)
        if output_type:
            item_types.append(str(output_type))
    return item_types


def _content_item_types(response: Any) -> list[str]:
    outputs = getattr(response, "output", None) or []
    item_types: list[str] = []
    for output in outputs:
        for item in getattr(output, "content", None) or []:
            content_type = getattr(item, "type", None)
            if content_type:
                item_types.append(str(content_type))
    return item_types


class OpenAIBackend:
    """Call the OpenAI Responses API with Structured Outputs."""

    name = "openai"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The OpenAI backend requires the 'openai' Python package. "
                "Install project dependencies before using --backend openai."
            ) from exc

        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        self.model = model or os.getenv("EVENTOUR_OPENAI_MODEL") or DEFAULT_MODEL
        self.timeout_seconds = float(
            timeout_seconds
            or os.getenv("EVENTOUR_OPENAI_TIMEOUT")
            or DEFAULT_TIMEOUT_SECONDS
        )
        self.max_output_tokens = int(
            max_output_tokens
            or os.getenv("EVENTOUR_OPENAI_MAX_OUTPUT_TOKENS")
            or DEFAULT_MAX_OUTPUT_TOKENS
        )
        self.backend_name = f"{self.name}:{self.model}"
        client_kwargs: dict[str, Any] = {
            "api_key": resolved_api_key,
            "timeout": self.timeout_seconds,
        }
        resolved_base_url = base_url or os.getenv("EVENTOUR_OPENAI_BASE_URL")
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        self._client = OpenAI(**client_kwargs)

    def _response_metadata(self, response: Any) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "response_id": getattr(response, "id", None),
            "usage": usage_to_dict(getattr(response, "usage", None)),
            "model": self.model,
            "status": getattr(response, "status", None),
            "error": _dump_object(getattr(response, "error", None)),
            "incomplete_details": _dump_object(getattr(response, "incomplete_details", None)),
            "output_item_types": _output_item_types(response),
            "content_item_types": _content_item_types(response),
        }
        return {key: value for key, value in metadata.items() if value not in (None, [], {})}

    def _failure_result(self, *, response: Any, rationale: str, extra_metadata: dict[str, Any] | None = None) -> ClassificationResult:
        metadata = self._response_metadata(response)
        if extra_metadata:
            metadata.update({key: value for key, value in extra_metadata.items() if value is not None})

        dumped_response = _dump_object(response)
        if dumped_response is not None:
            dumped_text = json.dumps(dumped_response, ensure_ascii=False)
            metadata["raw_response_excerpt"] = dumped_text[:2000]

        return ClassificationResult(
            decision=Decision.CANDIDATE_EXCEPTION,
            eventour_category=None,
            confidence=0.0,
            rationale=rationale,
            backend=self.backend_name,
            metadata=metadata,
        )

    def classify(self, entity: dict[str, Any]) -> ClassificationResult:
        prompt = build_prompt(entity)
        response = self._client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            reasoning={"effort": "low"},
            text={"format": response_format(), "verbosity": "low"},
            max_output_tokens=self.max_output_tokens,
        )

        refusal = extract_refusal(response)
        if refusal:
            return self._failure_result(
                response=response,
                rationale=f"Model refusal: {refusal}",
                extra_metadata={
                    "refusal": refusal,
                },
            )

        output_text = extract_output_text(response)
        if not output_text:
            return self._failure_result(
                response=response,
                rationale="Model returned no structured output text; queued for review.",
            )

        try:
            payload = parse_output_json(output_text)
            result = coerce_result(payload, backend_name=self.backend_name)
        except Exception as exc:
            return self._failure_result(
                response=response,
                rationale="Model returned invalid structured output; queued for review.",
                extra_metadata={
                    "output_text_preview": output_text[:500],
                    "parse_error": str(exc),
                },
            )

        return ClassificationResult(
            decision=result.decision,
            eventour_category=result.eventour_category,
            confidence=result.confidence,
            rationale=result.rationale,
            backend=result.backend,
            metadata=self._response_metadata(response),
        )

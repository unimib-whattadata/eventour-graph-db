"""Shared helpers for OpenAI structured classification."""

from __future__ import annotations

import json
from typing import Any

from eventour_kg.classification.policy import ClassificationResult, Decision, taxonomy_category_ids


def response_format() -> dict[str, Any]:
    categories = sorted(taxonomy_category_ids())
    return {
        "type": "json_schema",
        "name": "eventour_semantic_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": [decision.value for decision in Decision],
                },
                "eventour_category": {
                    "anyOf": [
                        {"type": "string", "enum": categories},
                        {"type": "null"},
                    ]
                },
                "confidence": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": [
                "decision",
                "eventour_category",
                "confidence",
                "rationale",
            ],
            "additionalProperties": False,
        },
    }


def usage_to_dict(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump(exclude_none=True)
    if hasattr(usage, "to_dict"):
        return usage.to_dict()
    if isinstance(usage, dict):
        return usage
    return None


def estimate_text_tokens(text: str) -> int:
    return max(1, int(round(len(text) / 4.0)))


def extract_output_text(response: Any) -> str | None:
    if isinstance(response, dict):
        output_text = response.get("output_text")
        if output_text:
            return output_text
        outputs = response.get("output") or []
        fragments: list[str] = []
        for output in outputs:
            for item in output.get("content", []) or []:
                text = item.get("text")
                if text:
                    fragments.append(text)
        if fragments:
            return "".join(fragments)
        return None

    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    outputs = getattr(response, "output", None) or []
    fragments: list[str] = []
    for output in outputs:
        content_items = getattr(output, "content", None) or []
        for item in content_items:
            text = getattr(item, "text", None)
            if text:
                fragments.append(text)

    if fragments:
        return "".join(fragments)
    return None


def extract_refusal(response: Any) -> str | None:
    if isinstance(response, dict):
        outputs = response.get("output") or []
        for output in outputs:
            for item in output.get("content", []) or []:
                refusal = item.get("refusal")
                if refusal:
                    return str(refusal)
        return None

    outputs = getattr(response, "output", None) or []
    for output in outputs:
        content_items = getattr(output, "content", None) or []
        for item in content_items:
            refusal = getattr(item, "refusal", None)
            if refusal:
                return str(refusal)
    return None


def coerce_result(payload: dict[str, Any], *, backend_name: str) -> ClassificationResult:
    decision_raw = payload.get("decision")
    try:
        decision = Decision(decision_raw)
    except ValueError as exc:
        raise ValueError(f"Unsupported decision returned by model: {decision_raw}") from exc

    category = payload.get("eventour_category")
    allowed_categories = taxonomy_category_ids()
    if decision == Decision.KEEP_POI:
        if category not in allowed_categories:
            raise ValueError(f"Model returned invalid Eventour category: {category}")
    elif category is not None:
        raise ValueError("eventour_category must be null unless decision == keep_poi")

    try:
        confidence = float(payload.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid confidence value returned by model: {payload.get('confidence')}") from exc
    confidence = max(0.0, min(1.0, confidence))

    rationale = str(payload.get("rationale") or "").strip()
    if not rationale:
        raise ValueError("Model returned an empty rationale")

    return ClassificationResult(
        decision=decision,
        eventour_category=category,
        confidence=confidence,
        rationale=rationale,
        backend=backend_name,
    )


def parse_output_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenAI response was not valid JSON: {text}") from exc

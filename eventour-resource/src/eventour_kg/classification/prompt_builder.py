"""Render entity-level prompts for Eventour semantic classification."""

from __future__ import annotations

import json
from typing import Any

from eventour_kg.classification.evidence_cards import build_classification_payload
from eventour_kg.classification.policy import load_prompt_template


def _prompt_payload(entity: dict[str, Any]) -> dict[str, Any]:
    if entity.get("classification_payload"):
        return dict(entity["classification_payload"])
    if entity.get("direct_classes") or entity.get("class_ancestors") or entity.get("semantic_facts"):
        return build_classification_payload(entity)
    return {
        "city_name": entity.get("city_id"),
        "entity_label": entity.get("preferred_label"),
        "entity_description": entity.get("description"),
        "direct_class_labels": entity.get("direct_class_labels", []),
    }


def build_prompt(entity: dict[str, Any]) -> str:
    template = load_prompt_template().rstrip()
    payload = _prompt_payload(entity)
    return f"{template}\n\nEntity to classify:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"

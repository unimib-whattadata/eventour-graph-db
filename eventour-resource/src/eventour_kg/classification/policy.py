"""Eventour classification decisions and taxonomy helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any


class Decision(StrEnum):
    KEEP_POI = "keep_poi"
    KEEP_CONTEXT = "keep_context"
    CANDIDATE_EXCEPTION = "candidate_exception"
    EXCLUDE = "exclude"


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TAXONOMY_PATH = PROJECT_ROOT / "taxonomy" / "eventour_taxonomy_v1.json"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "entity_classification_prompt_v1.txt"

AUTO_ACCEPT_CONFIDENCE = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.60


@dataclass(frozen=True)
class ClassificationResult:
    decision: Decision
    eventour_category: str | None
    confidence: float
    rationale: str
    backend: str
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "decision": self.decision.value,
            "eventour_category": self.eventour_category,
            "confidence": round(float(self.confidence), 4),
            "rationale": self.rationale,
            "backend": self.backend,
        }
        if self.metadata:
            payload["backend_metadata"] = self.metadata
        return payload


def load_taxonomy() -> dict[str, Any]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def taxonomy_category_ids() -> set[str]:
    taxonomy = load_taxonomy()
    return {category["id"] for category in taxonomy["categories"]}


def should_review(
    result: ClassificationResult,
    *,
    entity_needs_label_enrichment: bool,
) -> bool:
    if entity_needs_label_enrichment:
        return True
    if result.decision == Decision.CANDIDATE_EXCEPTION:
        return True
    if result.confidence < AUTO_ACCEPT_CONFIDENCE:
        return True
    return False

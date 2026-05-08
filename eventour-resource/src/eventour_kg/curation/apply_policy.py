"""Apply deterministic curation policy to Wikidata classification rows."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from eventour_kg.curation import semantic_policy


_MAJORITY_DECISION_TO_LABEL = {
    "keep_poi": "primary_poi",
    "keep_context": "context_entity",
    "exclude": "exclude",
}

_FALLBACK_DECISION_TO_LABEL = {
    "keep_poi": "secondary_poi",
    "keep_context": "context_entity",
    "candidate_exception": "context_entity",
    "exclude": "exclude",
}


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_category(value: object) -> str | None:
    return _normalize_text(value)


def _normalize_row_key(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _normalize_text(row.get(key))
        if value is not None:
            return value
    return None


def _positive_semantic_signal(groups: Iterable[str]) -> bool:
    return any(
        semantic_policy.GROUP_RULES[group]["default_label"] != "exclude"
        for group in groups
        if group in semantic_policy.GROUP_RULES
    )


def load_adjudication_by_qid(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            item_qid = _normalize_row_key(row, "item_qid")
            if item_qid is None:
                continue
            rows[item_qid] = dict(row)
    return rows


def load_city_overrides_by_qid(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            item_qid = _normalize_row_key(row, "item_qid")
            if item_qid is None:
                continue
            rows[item_qid] = dict(row)
    return rows


def load_classification_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = line.strip()
            if not payload:
                continue
            rows.append(json.loads(payload))
    return rows


def _category_for_positive_label(label: str | None, category: str | None) -> str | None:
    if label in {"primary_poi", "secondary_poi", "secondary_cultural_poi"}:
        return category
    return None


def _apply_city_override(
    entity: dict[str, Any],
    override_row: dict[str, Any],
) -> dict[str, Any]:
    final_label = _normalize_row_key(override_row, "override_final_label", "final_label")
    if final_label is None:
        raise ValueError(f"Missing override final label for item_qid={entity.get('item_qid')}")
    final_category = _category_for_positive_label(
        final_label,
        _normalize_category(_normalize_row_key(override_row, "override_final_category", "final_category")),
    )
    reason = _normalize_row_key(override_row, "override_reason", "reason")
    notes = _normalize_row_key(override_row, "notes")
    note_parts = ["city override applied"]
    if reason is not None:
        note_parts.append(reason)
    if notes is not None:
        note_parts.append(notes)
    return {
        **entity,
        "final_label": final_label,
        "final_category": final_category,
        "curation_source": "city_override",
        "policy_group": None,
        "curation_notes": "; ".join(note_parts),
    }


def _apply_adjudication(
    entity: dict[str, Any],
    adjudication_row: dict[str, Any],
) -> dict[str, Any] | None:
    explicit_label = _normalize_row_key(adjudication_row, "adjudicated_final_label", "final_label")
    explicit_category = _normalize_category(
        _normalize_row_key(adjudication_row, "adjudicated_final_category", "final_category")
    )
    majority_decision = _normalize_row_key(adjudication_row, "human_decision_majority", "decision_majority")
    majority_category = _normalize_category(
        _normalize_row_key(adjudication_row, "human_category_majority", "category_majority")
    )

    if explicit_label is not None:
        final_category = _category_for_positive_label(
            explicit_label,
            explicit_category or majority_category or _normalize_category(entity.get("eventour_category")),
        )
        note_parts = ["explicit adjudication applied"]
        adjudication_notes = _normalize_row_key(adjudication_row, "adjudication_notes", "notes")
        if adjudication_notes is not None:
            note_parts.append(adjudication_notes)
        return {
            **entity,
            "final_label": explicit_label,
            "final_category": final_category,
            "curation_source": "adjudication",
            "policy_group": None,
            "curation_notes": "; ".join(note_parts),
        }

    if majority_decision is None:
        return None

    derived_label = _MAJORITY_DECISION_TO_LABEL.get(majority_decision)
    if derived_label is None:
        return None

    final_category = _category_for_positive_label(
        derived_label,
        majority_category or _normalize_category(entity.get("eventour_category")),
    )
    return {
        **entity,
        "final_label": derived_label,
        "final_category": final_category,
        "curation_source": "adjudication",
        "policy_group": None,
        "curation_notes": f"majority-derived adjudication default from {majority_decision}",
    }


def _apply_semantic_policy(entity: dict[str, Any]) -> dict[str, Any] | None:
    policy_result = semantic_policy.apply_semantic_policy(entity)
    final_label = _normalize_text(policy_result.get("final_label"))
    if final_label is None:
        return None
    policy_group = _normalize_text(policy_result.get("policy_group"))
    return {
        **entity,
        "final_label": final_label,
        "final_category": _category_for_positive_label(final_label, _normalize_category(entity.get("eventour_category"))),
        "curation_source": "semantic_policy",
        "policy_group": policy_group,
        "curation_notes": f"semantic policy matched {policy_group}" if policy_group else "semantic policy matched",
    }


def _apply_fallback(entity: dict[str, Any]) -> dict[str, Any]:
    decision = _normalize_text(entity.get("decision"))
    final_category = _normalize_category(entity.get("eventour_category"))

    if decision in _FALLBACK_DECISION_TO_LABEL:
        final_label = _FALLBACK_DECISION_TO_LABEL[decision]
        resolved_category = _category_for_positive_label(final_label, final_category)
        return {
            **entity,
            "final_label": final_label,
            "final_category": resolved_category,
            "curation_source": "fallback",
            "policy_group": None,
            "curation_notes": f"conservative fallback from classifier decision {decision}",
        }

    matched_groups = semantic_policy.match_policy_groups(entity)
    positive_signal = _positive_semantic_signal(matched_groups)
    return {
        **entity,
        "final_label": "context_entity" if positive_signal else "exclude",
        "final_category": None,
        "curation_source": "fallback",
        "policy_group": matched_groups[0] if matched_groups else None,
        "curation_notes": (
            "fallback for missing or unknown decision with cultural semantic signal"
            if positive_signal
            else "fallback for missing or unknown decision without semantic signal"
        ),
    }


def apply_curation(
    entity: dict[str, Any],
    *,
    adjudication_by_qid: dict[str, dict[str, Any]] | None = None,
    city_overrides_by_qid: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    item_qid = _normalize_row_key(entity, "item_qid")
    if item_qid is None:
        raise ValueError("Classification entity is missing item_qid")

    normalized_entity = dict(entity)

    if city_overrides_by_qid and item_qid in city_overrides_by_qid:
        return _apply_city_override(normalized_entity, city_overrides_by_qid[item_qid])

    if adjudication_by_qid and item_qid in adjudication_by_qid:
        adjudicated = _apply_adjudication(normalized_entity, adjudication_by_qid[item_qid])
        if adjudicated is not None:
            return adjudicated

    semantic_curated = _apply_semantic_policy(normalized_entity)
    if semantic_curated is not None:
        return semantic_curated

    return _apply_fallback(normalized_entity)


def apply_curation_to_records(
    entities: Iterable[dict[str, Any]],
    *,
    adjudication_by_qid: dict[str, dict[str, Any]] | None = None,
    city_overrides_by_qid: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return [
        apply_curation(
            entity,
            adjudication_by_qid=adjudication_by_qid,
            city_overrides_by_qid=city_overrides_by_qid,
        )
        for entity in entities
    ]


__all__ = [
    "apply_curation",
    "apply_curation_to_records",
    "load_adjudication_by_qid",
    "load_city_overrides_by_qid",
    "load_classification_jsonl",
]

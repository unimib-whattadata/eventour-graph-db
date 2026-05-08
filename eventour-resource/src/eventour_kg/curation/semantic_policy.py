"""Explicit version-1 semantic curation policy rules."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any


PRIORITY_ORDER = (
    "branded_venues",
    "hotels_lodging",
    "institutional_education",
    "libraries_archives",
    "named_urban_landmarks",
    "cinemas_theatres_performance",
    "historic_buildings_palazzi",
    "religious_sites",
)

LABEL_ORDER = {
    "exclude": 0,
    "context_entity": 1,
    "secondary_poi": 2,
    "primary_poi": 3,
}

GROUP_RULES: dict[str, dict[str, Any]] = {
    "religious_sites": {
        "default_label": "primary_poi",
        "label_cap": "primary_poi",
        "keywords": (
            "abbazia",
            "abbey",
            "basilica",
            "cappella",
            "cathedral",
            "cattedrale",
            "chapel",
            "chiesa",
            "church",
            "convent",
            "convento",
            "duomo",
            "monastero",
            "monastery",
            "moschea",
            "mosque",
            "oratorio",
            "oratory",
            "sanctuary",
            "santuario",
            "sinagoga",
            "synagogue",
        ),
    },
    "historic_buildings_palazzi": {
        "default_label": "primary_poi",
        "label_cap": "primary_poi",
        "keywords": (
            "castle",
            "castello",
            "historic building",
            "palace",
            "palazzo",
            "villa",
        ),
    },
    "cinemas_theatres_performance": {
        "default_label": "primary_poi",
        "label_cap": "primary_poi",
        "keywords": (
            "auditorium",
            "cinema",
            "concert hall",
            "movie theater",
            "movie theatre",
            "opera house",
            "opera",
            "playhouse",
            "teatro",
            "theater",
            "theatre",
        ),
    },
    "named_urban_landmarks": {
        "default_label": "primary_poi",
        "label_cap": "primary_poi",
        "keywords": (
            "arch",
            "city gate",
            "clock tower",
            "landmark",
            "memorial",
            "monument",
            "obelisk",
            "tower",
            "urban landmark",
        ),
    },
    "libraries_archives": {
        "default_label": "secondary_poi",
        "label_cap": "secondary_poi",
        "keywords": (
            "archive",
            "archivio",
            "biblioteca",
            "library",
            "mediatheque",
        ),
    },
    "institutional_education": {
        "default_label": "context_entity",
        "label_cap": "context_entity",
        "keywords": (
            "academy",
            "accademia",
            "college",
            "conservatory",
            "conservatorio",
            "department",
            "dipartimento",
            "faculty",
            "institute",
            "istituto",
            "liceo",
            "politecnico",
            "school",
            "scuola",
            "university",
            "universita",
        ),
    },
    "branded_venues": {
        "default_label": "exclude",
        "label_cap": "exclude",
        "keywords": (
            "boutique",
            "brand",
            "branded",
            "department store",
            "flagship",
            "mall",
            "retail",
            "shop",
            "shopping",
            "showroom",
            "store",
        ),
    },
    "hotels_lodging": {
        "default_label": "exclude",
        "label_cap": "exclude",
        "keywords": (
            "albergo",
            "aparthotel",
            "b&b",
            "bed and breakfast",
            "guesthouse",
            "hostel",
            "hotel",
            "inn",
            "locanda",
            "lodging",
            "ostello",
            "resort",
        ),
    },
}


def _normalize_text(value: object) -> str:
    return str(value or "").strip().lower()


def _extract_string_list(value: object, *, item_key: str | None = None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = _normalize_text(value)
        return [text] if text else []

    values: list[str] = []
    if isinstance(value, list):
        for item in value:
            if item_key is not None and isinstance(item, dict):
                text = _normalize_text(item.get(item_key))
            else:
                text = _normalize_text(item)
            if text:
                values.append(text)
    return values


def _signal_texts(entity: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "preferred_label": _extract_string_list(entity.get("preferred_label")),
        "description": _extract_string_list(entity.get("description")),
        "direct_class_labels": _extract_string_list(entity.get("direct_classes"), item_key="label")
        or _extract_string_list(entity.get("direct_class_labels")),
        "class_ancestor_labels": _extract_string_list(entity.get("class_ancestors"), item_key="label")
        or _extract_string_list(entity.get("class_ancestor_labels")),
        "semantic_fact_texts": _extract_string_list(entity.get("semantic_facts"), item_key="prompt_text")
        or _extract_string_list(entity.get("semantic_fact_texts")),
    }


@lru_cache(maxsize=None)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in keyword.split()]
    body = r"\s+".join(parts)
    return re.compile(rf"(?<!\w){body}(?!\w)")


def _contains_keyword(text: str, keyword: str) -> bool:
    return bool(_keyword_pattern(keyword).search(text))


def _matches_group(entity: dict[str, Any], group: str) -> bool:
    texts_by_signal = _signal_texts(entity)
    keywords = GROUP_RULES[group]["keywords"]
    for texts in texts_by_signal.values():
        for text in texts:
            if any(_contains_keyword(text, keyword) for keyword in keywords):
                return True
    return False


def match_policy_groups(entity: dict[str, Any]) -> list[str]:
    return [group for group in PRIORITY_ORDER if _matches_group(entity, group)]


def _most_restrictive_label(groups: list[str]) -> str | None:
    label_caps = [GROUP_RULES[group]["label_cap"] for group in groups]
    if not label_caps:
        return None
    return min(label_caps, key=lambda label: LABEL_ORDER[label])


def resolve_policy_groups(groups: list[str]) -> dict[str, Any]:
    matched_groups = [group for group in PRIORITY_ORDER if group in set(groups)]
    if not matched_groups:
        return {
            "matched_groups": [],
            "policy_group": None,
            "default_label": None,
            "label_cap": None,
            "final_label": None,
        }

    policy_group = matched_groups[0]
    default_label = GROUP_RULES[policy_group]["default_label"]
    label_cap = _most_restrictive_label(matched_groups)
    if label_cap is None:
        final_label = default_label
    else:
        final_label = min((default_label, label_cap), key=lambda label: LABEL_ORDER[label])

    return {
        "matched_groups": matched_groups,
        "policy_group": policy_group,
        "default_label": default_label,
        "label_cap": label_cap,
        "final_label": final_label,
    }


def apply_semantic_policy(entity: dict[str, Any]) -> dict[str, Any]:
    matched_groups = match_policy_groups(entity)
    result = resolve_policy_groups(matched_groups)
    result["matched_groups"] = matched_groups
    return result


__all__ = [
    "GROUP_RULES",
    "PRIORITY_ORDER",
    "apply_semantic_policy",
    "match_policy_groups",
    "resolve_policy_groups",
]

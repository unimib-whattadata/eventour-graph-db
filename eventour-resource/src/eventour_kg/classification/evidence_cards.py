"""Build evidence cards from cleaned Wikidata subgraphs."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
from typing import Any
import unicodedata


FACT_LIMIT = 8
MAX_FACTS_PER_PROPERTY = 2
MAX_LOCATION_FACTS = 2
MAX_FALLBACK_LOCATION_FACTS = 1

ALWAYS_DROP_SEMANTIC_FACT_PROPERTY_QIDS = {
    "P17",  # country
}

FALLBACK_ONLY_LOCATION_PROPERTY_QIDS = {
    "P131",   # located in the administrative territorial entity
    "P276",   # location
    "P6375",  # street address
    "P669",   # located on street
}

QID_LIKE_RE = re.compile(r"^[PQ]\d+$", re.IGNORECASE)
URL_LIKE_RE = re.compile(r"^https?://", re.IGNORECASE)
DATE_PREFIX_RE = re.compile(r"^-?\d{4}-\d{2}-\d{2}")

LOCATION_KEYWORDS = {
    "address",
    "administrative",
    "amministrativa",
    "capital",
    "citta",
    "city",
    "comune",
    "continent",
    "country",
    "district",
    "indirizzo",
    "location",
    "located",
    "luogo",
    "neighborhood",
    "paese",
    "parte di",
    "part of",
    "place",
    "quartiere",
    "regione",
    "region",
    "situato",
    "situata",
    "state",
    "street",
    "territorial",
    "territorio",
    "unita amministrativa",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    folded = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in folded if not unicodedata.combining(ch))
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return " ".join(ascii_value.split())


def token_set(value: str | None) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) > 2}


def is_qid_like(value: str | None) -> bool:
    return bool(value and QID_LIKE_RE.fullmatch(value.strip()))


def is_readable_text(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip()
    if not text:
        return False
    if is_qid_like(text):
        return False
    if URL_LIKE_RE.match(text):
        return False
    if "special:filepath/" in text.lower():
        return False
    if any(ch in text for ch in ("\n", "\r", "\t")):
        return False
    if not any(ch.isalpha() for ch in text):
        return False
    non_space = [ch for ch in text if not ch.isspace()]
    if not non_space:
        return False
    alpha_chars = sum(1 for ch in non_space if ch.isalpha())
    if alpha_chars / len(non_space) < 0.2:
        return False
    return True


def length_bucket(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return "poor"
    tokens = text.split()
    token_count = len(tokens)
    char_count = len(text)
    if 1 <= token_count <= 8 and 3 <= char_count <= 60:
        return "good"
    if 9 <= token_count <= 14 or 61 <= char_count <= 100:
        return "acceptable"
    return "poor"


def literal_length_bucket(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return "poor"
    if len(text) <= 60:
        return "good"
    if len(text) <= 100:
        return "acceptable"
    return "poor"


def _bucket_score(bucket: str) -> float:
    if bucket == "good":
        return 1.0
    if bucket == "acceptable":
        return 0.8
    return 0.45


def _value_display(claim: dict[str, Any]) -> str:
    value_type = effective_value_type(claim)
    if value_type == "wikibase-item":
        return (claim.get("value_label") or "").strip()
    literal = (claim.get("value_literal") or "").strip()
    if value_type == "time":
        date_match = DATE_PREFIX_RE.match(literal)
        if date_match:
            return date_match.group(0)
    return literal


def effective_value_type(claim: dict[str, Any]) -> str:
    value_type = str(claim.get("value_type") or "")
    if value_type == "wikibase-item":
        return "wikibase-item"
    if claim.get("value_lang"):
        return "monolingualtext"
    datatype = str(claim.get("value_datatype") or "")
    if datatype.endswith("#dateTime") or datatype.endswith("#date"):
        return "time"
    if any(datatype.endswith(suffix) for suffix in ("#decimal", "#integer", "#double", "#float", "#nonNegativeInteger")):
        return "quantity"
    if value_type:
        return value_type
    return "literal"


def label_quality(claim: dict[str, Any]) -> float:
    property_label = (claim.get("property_label") or "").strip()
    value_type = effective_value_type(claim)
    value_text = _value_display(claim)

    property_readable = is_readable_text(property_label)
    value_readable = is_readable_text(value_text)
    property_score = _bucket_score(length_bucket(property_label)) if property_readable else 0.0

    if value_type == "wikibase-item":
        value_score = _bucket_score(length_bucket(value_text)) if value_readable else 0.0
    elif value_type in {"monolingualtext", "string", "literal"}:
        value_score = _bucket_score(literal_length_bucket(value_text)) if value_readable else 0.0
    elif value_type == "time":
        value_score = 0.55 if value_text else 0.0
        value_readable = bool(value_text)
    elif value_type == "quantity":
        value_score = 0.35 if value_text else 0.0
        value_readable = bool(value_text)
    else:
        value_score = 0.25 if value_text else 0.0
        value_readable = bool(value_text)

    if property_readable and value_readable:
        return round((property_score + value_score) / 2.0, 4)
    if property_readable:
        return round(0.4 * property_score, 4)
    if value_readable:
        return round(0.25 * value_score, 4)
    return 0.0


def description_support(claim: dict[str, Any], *, label: str | None, description: str | None) -> float:
    reference_tokens = token_set(label) | token_set(description)
    if not reference_tokens:
        return 0.0
    property_overlap = token_set(claim.get("property_label")) & reference_tokens
    value_overlap = token_set(_value_display(claim)) & reference_tokens
    if value_overlap:
        return 0.2
    if property_overlap:
        return 0.1
    return 0.0


def object_key(claim: dict[str, Any]) -> str | None:
    if effective_value_type(claim) == "wikibase-item":
        value_qid = claim.get("value_qid")
        if value_qid:
            return str(value_qid)
        value_label = claim.get("value_label")
        if value_label:
            return f"label:{value_label}"
        return None
    value_literal = claim.get("value_literal")
    if value_literal:
        return f"literal:{value_literal}"
    return None


def _normalize_scores(raw_scores: dict[str, float]) -> dict[str, float]:
    if not raw_scores:
        return {}
    values = list(raw_scores.values())
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        return {key: 1.0 for key in raw_scores}
    return {
        key: round((value - min_value) / (max_value - min_value), 6)
        for key, value in raw_scores.items()
    }


def compute_specificity_maps(rows: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float]]:
    entity_count = len(rows)
    property_df: Counter[str] = Counter()
    object_df: Counter[str] = Counter()

    for row in rows:
        properties_seen = {claim.get("property_qid") for claim in row.get("claims", []) if claim.get("property_qid")}
        property_df.update(properties_seen)

        objects_seen = {key for claim in row.get("claims", []) if (key := object_key(claim))}
        object_df.update(objects_seen)

    property_raw = {
        property_qid: math.log((entity_count + 1) / (df + 1)) + 1
        for property_qid, df in property_df.items()
    }
    object_raw = {
        key: math.log((entity_count + 1) / (df + 1)) + 1
        for key, df in object_df.items()
    }
    return _normalize_scores(property_raw), _normalize_scores(object_raw)


def build_class_ancestor_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["direct_class_qid"]: row for row in rows if row.get("direct_class_qid")}


def build_property_catalog_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["property_qid"]: row for row in rows if row.get("property_qid")}


def _direct_classes(entity: dict[str, Any]) -> list[dict[str, str]]:
    direct_classes: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    qids = entity.get("direct_class_qids") or []
    labels = entity.get("direct_class_labels") or []
    for qid, label in zip(qids, labels, strict=False):
        qid_text = str(qid) if qid else ""
        label_text = str(label) if label else ""
        if not qid_text or (qid_text, label_text) in seen:
            continue
        seen.add((qid_text, label_text))
        direct_classes.append({"qid": qid_text, "label": label_text})
    for qid in qids[len(direct_classes):]:
        qid_text = str(qid) if qid else ""
        if not qid_text or (qid_text, "") in seen:
            continue
        seen.add((qid_text, ""))
        direct_classes.append({"qid": qid_text, "label": ""})
    return direct_classes


def _class_ancestors(
    direct_classes: list[dict[str, str]],
    *,
    class_ancestor_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for direct_class in direct_classes:
        bucket = class_ancestor_index.get(direct_class["qid"])
        if not bucket:
            continue
        for ancestor in bucket.get("ancestors", []):
            ancestor_qid = ancestor.get("qid")
            ancestor_label = ancestor.get("label") or ""
            if not ancestor_qid:
                continue
            item = merged.setdefault(
                ancestor_qid,
                {
                    "qid": ancestor_qid,
                    "label": ancestor_label,
                    "source_direct_class_qids": [],
                },
            )
            if ancestor_label and not item["label"]:
                item["label"] = ancestor_label
            if direct_class["qid"] not in item["source_direct_class_qids"]:
                item["source_direct_class_qids"].append(direct_class["qid"])
    return sorted(
        merged.values(),
        key=lambda row: (normalize_text(row.get("label")), row["qid"]),
    )


def _property_text(claim: dict[str, Any], property_catalog_index: dict[str, dict[str, Any]] | None) -> str:
    property_label = (claim.get("property_label") or "").strip()
    if property_label:
        return property_label
    if not property_catalog_index:
        return ""
    catalog_row = property_catalog_index.get(claim.get("property_qid"))
    return (catalog_row or {}).get("property_label") or ""


def is_location_context_fact(
    claim: dict[str, Any],
    *,
    property_catalog_index: dict[str, dict[str, Any]] | None = None,
) -> bool:
    property_text = _property_text(claim, property_catalog_index)
    property_description = ""
    if property_catalog_index and claim.get("property_qid") in property_catalog_index:
        property_description = property_catalog_index[claim["property_qid"]].get("property_description") or ""
    haystack = normalize_text(" ".join([property_text, property_description]))
    return any(keyword in haystack for keyword in LOCATION_KEYWORDS)


def _redundancy_penalty(
    claim: dict[str, Any],
    *,
    direct_class_labels: set[str],
    ancestor_labels: set[str],
    entity_label: str | None,
    entity_description: str | None,
) -> float:
    value_norm = normalize_text(_value_display(claim))
    prompt_norm = normalize_text(flatten_fact(claim))
    combined_entity = normalize_text(" ".join([entity_label or "", entity_description or ""]))

    if value_norm and (value_norm in direct_class_labels or value_norm in ancestor_labels):
        return 1.0
    if prompt_norm and prompt_norm in combined_entity:
        return 0.6
    if value_norm and value_norm in combined_entity:
        return 0.5
    if normalize_text(claim.get("property_label")) in combined_entity:
        return 0.2
    return 0.0


def flatten_fact(claim: dict[str, Any]) -> str:
    property_label = (claim.get("property_label") or "").strip() or str(claim.get("property_qid") or "")
    value_text = _value_display(claim)
    return f"{property_label}: {value_text}".strip()


def _tier_for_claim(claim: dict[str, Any]) -> str:
    readable_property = is_readable_text(claim.get("property_label"))
    value_type = effective_value_type(claim)
    value_text = _value_display(claim)
    readable_value = is_readable_text(value_text)
    literal_bucket = literal_length_bucket(value_text)

    if value_type == "wikibase-item" and readable_property and readable_value:
        return "A"
    if value_type in {"monolingualtext", "string", "literal"} and readable_property and literal_bucket != "poor":
        return "B"
    if value_type == "time" and readable_property and value_text:
        return "B"
    return "C"


def _claim_sort_key(
    claim: dict[str, Any],
    *,
    property_specificity: float,
    object_specificity: float,
    label_quality_score: float,
    description_support_score: float,
    redundancy_penalty_score: float,
) -> tuple[Any, ...]:
    tier_rank = {"A": 2, "B": 1, "C": 0}[claim["tier"]]
    return (
        tier_rank,
        property_specificity,
        object_specificity,
        label_quality_score,
        description_support_score,
        -redundancy_penalty_score,
        normalize_text(claim.get("prompt_text")),
    )


def _build_semantic_fact_candidates(
    entity: dict[str, Any],
    *,
    direct_class_labels: set[str],
    ancestor_labels: set[str],
    property_idf: dict[str, float],
    object_idf: dict[str, float],
    property_catalog_index: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_prompt_texts: set[str] = set()

    for claim in entity.get("claims", []):
        property_qid = claim.get("property_qid")
        if property_qid == "P31":
            continue

        property_label = _property_text(claim, property_catalog_index)
        materialized_claim = {**claim, "property_label": property_label}
        prompt_text = flatten_fact(materialized_claim)
        normalized_prompt = normalize_text(prompt_text)
        if not normalized_prompt or normalized_prompt in seen_prompt_texts:
            continue
        seen_prompt_texts.add(normalized_prompt)

        value_norm = normalize_text(_value_display(materialized_claim))
        if value_norm and (value_norm in direct_class_labels or value_norm in ancestor_labels):
            continue

        property_specificity = round(property_idf.get(str(property_qid), 0.0), 6)
        object_specificity = round(object_idf.get(object_key(materialized_claim) or "", 0.0), 6)
        label_quality_score = label_quality(materialized_claim)
        description_support_score = description_support(
            materialized_claim,
            label=entity.get("preferred_label"),
            description=entity.get("description"),
        )
        redundancy_penalty_score = _redundancy_penalty(
            materialized_claim,
            direct_class_labels=direct_class_labels,
            ancestor_labels=ancestor_labels,
            entity_label=entity.get("preferred_label"),
            entity_description=entity.get("description"),
        )
        tier = _tier_for_claim(materialized_claim)

        candidates.append(
            {
                **materialized_claim,
                "prompt_text": prompt_text,
                "tier": tier,
                "rank_features": {
                    "property_specificity": property_specificity,
                    "object_specificity": object_specificity,
                    "label_quality": round(label_quality_score, 4),
                    "description_support": round(description_support_score, 4),
                    "redundancy_penalty": round(redundancy_penalty_score, 4),
                },
                "sort_key": _claim_sort_key(
                    {"tier": tier, "prompt_text": prompt_text},
                    property_specificity=property_specificity,
                    object_specificity=object_specificity,
                    label_quality_score=label_quality_score,
                    description_support_score=description_support_score,
                    redundancy_penalty_score=redundancy_penalty_score,
                ),
            }
        )

    candidates.sort(key=lambda row: row["sort_key"], reverse=True)
    return candidates


def semantic_fact_policy(claim: dict[str, Any]) -> str:
    property_qid = str(claim.get("property_qid") or "")
    if property_qid in ALWAYS_DROP_SEMANTIC_FACT_PROPERTY_QIDS:
        return "drop"
    if property_qid in FALLBACK_ONLY_LOCATION_PROPERTY_QIDS:
        return "fallback_location"
    return "normal"


def _select_semantic_facts(
    candidates: list[dict[str, Any]],
    *,
    property_catalog_index: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    property_counts: defaultdict[str, int] = defaultdict(int)
    seen_prompt_texts: set[str] = set()
    seen_values: set[str] = set()
    location_fact_count = 0

    fallback_candidates: list[dict[str, Any]] = []

    def try_select(candidate: dict[str, Any], *, fallback_location_budget: int | None = None) -> bool:
        nonlocal location_fact_count

        if len(selected) >= FACT_LIMIT:
            return False

        normalized_prompt = normalize_text(candidate["prompt_text"])
        normalized_value = normalize_text(_value_display(candidate))
        if normalized_prompt in seen_prompt_texts:
            return False
        if normalized_value and normalized_value in seen_values:
            return False
        if candidate["rank_features"]["redundancy_penalty"] >= 1.0:
            return False

        property_qid = str(candidate.get("property_qid") or "")
        if property_counts[property_qid] >= MAX_FACTS_PER_PROPERTY:
            return False

        is_location_fact = is_location_context_fact(candidate, property_catalog_index=property_catalog_index)
        if is_location_fact and location_fact_count >= MAX_LOCATION_FACTS:
            return False
        if is_location_fact and fallback_location_budget is not None and fallback_location_budget <= 0:
            return False

        property_counts[property_qid] += 1
        if is_location_fact:
            location_fact_count += 1
        seen_prompt_texts.add(normalized_prompt)
        if normalized_value:
            seen_values.add(normalized_value)

        selected.append(
            {
                "property_qid": candidate.get("property_qid"),
                "property_label": candidate.get("property_label"),
                "value_type": candidate.get("value_type"),
                "value_qid": candidate.get("value_qid"),
                "value_label": candidate.get("value_label"),
                "value_literal": candidate.get("value_literal"),
                "tier": candidate["tier"],
                "rank_features": candidate["rank_features"],
                "prompt_text": candidate["prompt_text"],
            }
        )
        return True

    for candidate in candidates:
        policy = semantic_fact_policy(candidate)
        if policy == "drop":
            continue
        if policy == "fallback_location":
            fallback_candidates.append(candidate)
            continue
        try_select(candidate)

    if not selected:
        fallback_budget = MAX_FALLBACK_LOCATION_FACTS
        for candidate in fallback_candidates:
            if fallback_budget <= 0 or len(selected) >= FACT_LIMIT:
                break
            if try_select(candidate, fallback_location_budget=fallback_budget):
                fallback_budget -= 1

    return selected


def build_classification_payload(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "city_name": card.get("city_id"),
        "entity_label": card.get("preferred_label"),
        "entity_description": card.get("description"),
        "direct_class_labels": [item.get("label") for item in card.get("direct_classes", []) if item.get("label")],
        "class_ancestor_labels": [item.get("label") for item in card.get("class_ancestors", []) if item.get("label")],
        "semantic_fact_texts": [item.get("prompt_text") for item in card.get("semantic_facts", []) if item.get("prompt_text")],
    }


def build_evidence_card(
    entity: dict[str, Any],
    *,
    class_ancestor_index: dict[str, dict[str, Any]],
    property_idf: dict[str, float],
    object_idf: dict[str, float],
    property_catalog_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    direct_classes = _direct_classes(entity)
    class_ancestors = _class_ancestors(direct_classes, class_ancestor_index=class_ancestor_index)
    direct_class_labels = {normalize_text(item.get("label")) for item in direct_classes if item.get("label")}
    ancestor_labels = {normalize_text(item.get("label")) for item in class_ancestors if item.get("label")}

    candidates = _build_semantic_fact_candidates(
        entity,
        direct_class_labels=direct_class_labels,
        ancestor_labels=ancestor_labels,
        property_idf=property_idf,
        object_idf=object_idf,
        property_catalog_index=property_catalog_index,
    )
    semantic_facts = _select_semantic_facts(candidates, property_catalog_index=property_catalog_index)

    card = {
        "city_id": entity.get("city_id"),
        "source_id": entity.get("source_id"),
        "item_qid": entity.get("item_qid"),
        "item_uri": entity.get("item_uri"),
        "preferred_label": entity.get("preferred_label"),
        "description": entity.get("description"),
        "longitude": entity.get("longitude"),
        "latitude": entity.get("latitude"),
        "direct_classes": direct_classes,
        "class_ancestors": class_ancestors,
        "semantic_facts": semantic_facts,
        "classification_payload": {},
    }
    card["classification_payload"] = build_classification_payload(card)
    return card


def build_evidence_cards(
    rows: list[dict[str, Any]],
    *,
    class_ancestor_index: dict[str, dict[str, Any]],
    property_catalog_index: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    property_idf, object_idf = compute_specificity_maps(rows)
    return [
        build_evidence_card(
            row,
            class_ancestor_index=class_ancestor_index,
            property_idf=property_idf,
            object_idf=object_idf,
            property_catalog_index=property_catalog_index,
        )
        for row in rows
    ]


def build_evidence_report(cards: list[dict[str, Any]]) -> dict[str, Any]:
    semantic_fact_counts = [len(card.get("semantic_facts", [])) for card in cards]
    ancestor_counts = [len(card.get("class_ancestors", [])) for card in cards]
    tier_counts: Counter[str] = Counter()
    for card in cards:
        tier_counts.update(fact.get("tier") for fact in card.get("semantic_facts", []) if fact.get("tier"))
    return {
        "entity_count": len(cards),
        "average_semantic_fact_count": round(sum(semantic_fact_counts) / len(semantic_fact_counts), 4) if semantic_fact_counts else 0.0,
        "max_semantic_fact_count": max(semantic_fact_counts) if semantic_fact_counts else 0,
        "entities_with_no_semantic_facts": sum(1 for count in semantic_fact_counts if count == 0),
        "average_ancestor_count": round(sum(ancestor_counts) / len(ancestor_counts), 4) if ancestor_counts else 0.0,
        "max_ancestor_count": max(ancestor_counts) if ancestor_counts else 0,
        "tier_distribution": dict(sorted(tier_counts.items())),
    }

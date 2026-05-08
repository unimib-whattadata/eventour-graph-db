"""Build adjudication rows from merged annotations and the master package."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from eventour_kg.evaluation.analyze_annotations import load_annotation_records


ANNOTATORS = ("serena", "blerina", "fabio")
ADJUDICATION_FIELDNAMES = (
    "sample_id",
    "item_qid",
    "preferred_label",
    "serena_decision",
    "blerina_decision",
    "fabio_decision",
    "serena_category",
    "blerina_category",
    "fabio_category",
    "human_decision_majority",
    "human_category_majority",
    "adjudicated_final_label",
    "adjudicated_final_category",
    "adjudication_notes",
    "llm_decision",
    "llm_eventour_category",
    "llm_confidence",
    "llm_needs_review",
)


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _majority_vote(values: list[str | None]) -> str | None:
    observed = [_normalize_text(value) for value in values]
    counts = Counter(value for value in observed if value is not None)
    if not counts:
        return None
    ranked = counts.most_common()
    top_value, top_count = ranked[0]
    if top_count <= len(values) / 2:
        return None
    if len(ranked) > 1 and top_count == ranked[1][1]:
        return None
    return top_value


def load_merged_annotation_rows(path: Path) -> list[dict[str, str | None]]:
    return load_annotation_records(path)


def load_annotation_package_master(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload["items"] if isinstance(payload, dict) else payload
    master_by_sample_id: dict[str, dict[str, object]] = {}
    for item in items:
        sample_id = _normalize_text(item.get("sample_id"))
        if sample_id is None:
            continue
        master_by_sample_id[sample_id] = item
    return master_by_sample_id


def build_adjudication_rows(
    annotations: list[dict[str, object]],
    *,
    master_by_sample_id: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for annotation in annotations:
        sample_id = _normalize_text(annotation.get("sample_id"))
        if sample_id is None:
            continue
        if sample_id not in master_by_sample_id:
            raise KeyError(f"Missing master annotation package record for sample_id={sample_id}")
        master = master_by_sample_id[sample_id]
        decision_majority = _majority_vote(
            [_normalize_text(annotation.get(f"{annotator}_decision")) for annotator in ANNOTATORS]
        )
        keep_poi_categories = [
            _normalize_text(annotation.get(f"{annotator}_category"))
            for annotator in ANNOTATORS
            if _normalize_text(annotation.get(f"{annotator}_decision")) == "keep_poi"
        ]
        category_majority = _majority_vote(keep_poi_categories) if decision_majority == "keep_poi" else None
        rows.append(
            {
                "sample_id": sample_id,
                "item_qid": _normalize_text(annotation.get("item_qid")) or _normalize_text(master.get("item_qid")) or "",
                "preferred_label": _normalize_text(annotation.get("preferred_label"))
                or _normalize_text(master.get("preferred_label"))
                or "",
                "serena_decision": _normalize_text(annotation.get("serena_decision")) or "",
                "blerina_decision": _normalize_text(annotation.get("blerina_decision")) or "",
                "fabio_decision": _normalize_text(annotation.get("fabio_decision")) or "",
                "serena_category": _normalize_text(annotation.get("serena_category")) or "",
                "blerina_category": _normalize_text(annotation.get("blerina_category")) or "",
                "fabio_category": _normalize_text(annotation.get("fabio_category")) or "",
                "human_decision_majority": decision_majority or "",
                "human_category_majority": category_majority or "",
                "adjudicated_final_label": "",
                "adjudicated_final_category": "",
                "adjudication_notes": "",
                "llm_decision": _normalize_text(master.get("llm_decision")) or "",
                "llm_eventour_category": _normalize_text(master.get("llm_eventour_category")) or "",
                "llm_confidence": master.get("llm_confidence", ""),
                "llm_needs_review": master.get("llm_needs_review", ""),
            }
        )
    return rows


def write_adjudication_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADJUDICATION_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ADJUDICATION_FIELDNAMES})

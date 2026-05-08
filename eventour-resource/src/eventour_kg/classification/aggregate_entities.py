"""Aggregate normalized Wikidata rows into one record per entity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from eventour_kg.extraction.source_records import write_jsonl


QID_LABEL_RE = re.compile(r"^Q\d+$")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _is_qid_like(value: str | None) -> bool:
    if not value:
        return False
    return bool(QID_LABEL_RE.fullmatch(value.strip()))


def _pick_best_label(rows: list[dict[str, Any]]) -> tuple[str | None, bool]:
    labels = []
    for row in rows:
        label = row.get("preferred_label")
        if label:
            labels.append(label)

    for label in labels:
        if not _is_qid_like(label):
            return label, False

    return (labels[0], True) if labels else (None, True)


def _pick_first_non_empty(values: list[str | None]) -> str | None:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def aggregate_entities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        qid = row.get("external_id")
        if not qid:
            continue
        grouped.setdefault(qid, []).append(row)

    aggregated: list[dict[str, Any]] = []
    for item_qid, entity_rows in grouped.items():
        best_label, needs_label_enrichment = _pick_best_label(entity_rows)
        descriptions = [row.get("extras", {}).get("item_description") for row in entity_rows]
        description = _pick_first_non_empty(descriptions)
        longitudes = [row.get("longitude") for row in entity_rows if row.get("longitude") is not None]
        latitudes = [row.get("latitude") for row in entity_rows if row.get("latitude") is not None]
        item_uris = [row.get("extras", {}).get("item_uri") for row in entity_rows]

        direct_classes_map: dict[str, dict[str, str | None]] = {}
        for row in entity_rows:
            extras = row.get("extras", {})
            class_qid = extras.get("direct_class_qid")
            class_label = extras.get("direct_class_label")
            class_uri = extras.get("direct_class_uri")
            if class_qid is None:
                continue
            direct_classes_map[class_qid] = {
                "qid": class_qid,
                "label": class_label,
                "uri": class_uri,
            }

        direct_classes = sorted(
            direct_classes_map.values(),
            key=lambda item: ((item.get("label") or ""), (item.get("qid") or "")),
        )

        aggregated.append(
            {
                "city_id": entity_rows[0].get("city_id"),
                "source_id": "wikidata",
                "item_qid": item_qid,
                "item_uri": _pick_first_non_empty(item_uris),
                "preferred_label": best_label,
                "needs_label_enrichment": needs_label_enrichment,
                "description": description,
                "longitude": longitudes[0] if longitudes else None,
                "latitude": latitudes[0] if latitudes else None,
                "row_count": len(entity_rows),
                "direct_class_count": len(direct_classes),
                "direct_classes": direct_classes,
                "direct_class_qids": [item["qid"] for item in direct_classes],
                "direct_class_labels": [item["label"] for item in direct_classes if item.get("label")],
            }
        )

    return sorted(
        aggregated,
        key=lambda item: (
            _is_qid_like(item.get("preferred_label")),
            (item.get("preferred_label") or ""),
            item["item_qid"],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate normalized Wikidata rows into one record per entity.")
    parser.add_argument("--input", required=True, help="Normalized Wikidata JSONL input path")
    parser.add_argument("--out", required=True, help="Aggregated JSONL output path")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    aggregated = aggregate_entities(rows)
    write_jsonl(aggregated, Path(args.out))
    print(f"Wrote {len(aggregated)} aggregated entity records to {args.out}")


if __name__ == "__main__":
    main()

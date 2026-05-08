"""Import downloaded WDQS results into Eventour source-record and normalized layers."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from eventour_kg.extraction.source_records import write_jsonl
from eventour_kg.extraction.wikidata import parse_wkt_point, qid_from_uri
from eventour_kg.normalization.source_normalizer import normalize_label, slug_text


def _read_delimited(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [dict(row) for row in reader]


def _read_sparql_json(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    bindings = payload.get("results", {}).get("bindings", [])
    rows: list[dict[str, str]] = []
    for binding in bindings:
        row: dict[str, str] = {}
        for key, value in binding.items():
            row[key] = value.get("value", "")
        rows.append(row)
    return rows


def read_wikidata_rows(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".tsv":
        return _read_delimited(path, "\t")
    if suffix == ".csv":
        return _read_delimited(path, ",")
    if suffix == ".json":
        return _read_sparql_json(path)
    raise ValueError(f"Unsupported Wikidata result format: {path}")


def _pick(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def build_source_record(city_id: str, row: dict[str, str]) -> dict[str, Any]:
    item_uri = _pick(row, "item")
    direct_class_uri = _pick(row, "directClass")
    item_qid = qid_from_uri(item_uri)
    direct_class_qid = qid_from_uri(direct_class_uri)
    longitude, latitude = parse_wkt_point(_pick(row, "coord"))

    item_label = normalize_label(_pick(row, "itemLabel"))
    item_description = normalize_label(_pick(row, "itemDescription"))
    direct_class_label = normalize_label(_pick(row, "directClassLabel"))

    return {
        "city_id": city_id,
        "source_id": "wikidata",
        "dataset_label": "Wikidata candidates",
        "domain": "poi",
        "entity_family": "wikidata_candidate",
        "integration_role": "candidate_poi_source",
        "record_id": f"wikidata:{item_qid or 'unknown'}",
        "external_id": item_qid,
        "preferred_label": item_label,
        "geometry_type": "Point",
        "longitude": longitude,
        "latitude": latitude,
        "raw_geometry": {
            "type": "Point",
            "coordinates": [longitude, latitude]
        } if longitude is not None and latitude is not None else None,
        "raw_properties": {
            "item_uri": item_uri,
            "item_qid": item_qid,
            "item_description": item_description,
            "direct_class_uri": direct_class_uri,
            "direct_class_qid": direct_class_qid,
            "direct_class_label": direct_class_label,
        },
    }


def build_normalized_record(source_record: dict[str, Any]) -> dict[str, Any]:
    raw = source_record["raw_properties"]
    label = normalize_label(source_record.get("preferred_label"))
    description = normalize_label(raw.get("item_description"))
    direct_class_label = normalize_label(raw.get("direct_class_label"))

    return {
        "city_id": source_record["city_id"],
        "source_id": "wikidata",
        "record_id": source_record["record_id"],
        "external_id": source_record["external_id"],
        "domain": "poi",
        "entity_family": "wikidata_candidate",
        "integration_role": "candidate_poi_source",
        "preferred_label": label,
        "normalized_label": slug_text(label),
        "display_address": None,
        "normalized_address": None,
        "source_category": direct_class_label,
        "normalized_source_category": slug_text(direct_class_label),
        "status": None,
        "municipality": None,
        "nil_id": None,
        "nil_name": None,
        "geometry_type": source_record.get("geometry_type"),
        "longitude": source_record.get("longitude"),
        "latitude": source_record.get("latitude"),
        "extras": {
            "item_qid": raw.get("item_qid"),
            "item_uri": raw.get("item_uri"),
            "item_description": description,
            "direct_class_qid": raw.get("direct_class_qid"),
            "direct_class_uri": raw.get("direct_class_uri"),
            "direct_class_label": direct_class_label,
        },
    }


def import_wikidata_results(city_id: str, input_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_wikidata_rows(input_path)
    source_records = [build_source_record(city_id, row) for row in rows]
    normalized_records = [build_normalized_record(row) for row in source_records]
    return source_records, normalized_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Import WDQS export files into Eventour intermediate layers.")
    parser.add_argument("city_id", help="City profile identifier, e.g. milan")
    parser.add_argument("--input", required=True, help="Path to the downloaded WDQS result file (.csv, .tsv, .json)")
    parser.add_argument("--source-out", required=True, help="JSONL output path for source records")
    parser.add_argument("--normalized-out", required=True, help="JSONL output path for normalized records")
    args = parser.parse_args()

    source_records, normalized_records = import_wikidata_results(args.city_id, Path(args.input))
    write_jsonl(source_records, Path(args.source_out))
    write_jsonl(normalized_records, Path(args.normalized_out))
    print(f"Wrote {len(source_records)} source records to {args.source_out}")
    print(f"Wrote {len(normalized_records)} normalized records to {args.normalized_out}")


if __name__ == "__main__":
    main()

"""Normalize source records into canonical intermediate fields using explicit mappings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from eventour_kg.config.loaders import load_city_profile
from eventour_kg.config.source_mappings import FieldMapping, load_source_mappings
from eventour_kg.extraction.source_records import geojson_source_records, write_jsonl


SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^0-9A-Za-zÀ-ÿ]+", re.UNICODE)


def _first_value(properties: dict[str, Any], field_names: tuple[str, ...]) -> Any:
    for field_name in field_names:
        value = properties.get(field_name)
        if value not in (None, ""):
            return value
    return None


def _normalize_space(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip()


def normalize_label(value: str | None) -> str | None:
    if not value:
        return None
    return _normalize_space(str(value))


def slug_text(value: str | None) -> str | None:
    if not value:
        return None
    collapsed = PUNCT_RE.sub(" ", value.lower())
    return _normalize_space(collapsed)


def render_template(template: str | None, properties: dict[str, Any]) -> str | None:
    if not template:
        return None

    rendered = template
    for key, value in properties.items():
        rendered = rendered.replace("{" + str(key) + "}", "" if value is None else str(value))
    rendered = re.sub(r"\{[^{}]+\}", "", rendered)
    rendered = _normalize_space(rendered)
    return rendered or None


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_record(record: dict[str, Any], mapping: FieldMapping) -> dict[str, Any]:
    properties = record["raw_properties"]

    label = normalize_label(
        _first_value(properties, mapping.label_fields) or render_template(mapping.label_template, properties)
    ) or record.get("preferred_label")
    address = normalize_label(
        _first_value(properties, mapping.address_fields) or render_template(mapping.address_template, properties)
    )
    category = normalize_label(
        _first_value(properties, mapping.category_fields)
    ) or mapping.category_literal
    status = normalize_label(_first_value(properties, mapping.status_fields))
    municipality = normalize_label(_first_value(properties, mapping.municipality_fields))
    nil_id = _first_value(properties, mapping.nil_id_fields)
    nil_name = normalize_label(_first_value(properties, mapping.nil_name_fields))

    longitude = parse_float(_first_value(properties, mapping.longitude_fields))
    latitude = parse_float(_first_value(properties, mapping.latitude_fields))
    if longitude is None:
        longitude = record.get("longitude")
    if latitude is None:
        latitude = record.get("latitude")

    extras: dict[str, Any] = {}
    for field_name, field_keys in (mapping.extra_fields or {}).items():
        extras[field_name] = _first_value(properties, field_keys)

    return {
        "city_id": record["city_id"],
        "source_id": record["source_id"],
        "record_id": record["record_id"],
        "external_id": record.get("external_id"),
        "domain": record["domain"],
        "entity_family": record["entity_family"],
        "integration_role": record["integration_role"],
        "preferred_label": label,
        "normalized_label": slug_text(label),
        "display_address": address,
        "normalized_address": slug_text(address),
        "source_category": category,
        "normalized_source_category": slug_text(category),
        "status": status,
        "municipality": municipality,
        "nil_id": None if nil_id in (None, "") else str(nil_id),
        "nil_name": nil_name,
        "geometry_type": record.get("geometry_type"),
        "longitude": longitude,
        "latitude": latitude,
        "extras": extras
    }


def normalize_source(city_id: str, source_id: str, mapping_version: str = "milan_v1") -> list[dict[str, Any]]:
    profile = load_city_profile(city_id)
    source = next((item for item in profile.sources if item.source_id == source_id), None)
    if source is None:
        raise ValueError(f"Unknown source_id: {source_id}")
    if source.format != "geojson":
        raise ValueError(f"Normalization currently supports GeoJSON sources only: {source_id}")

    mappings = load_source_mappings(mapping_version)
    mapping = mappings.get(source_id)
    if mapping is None:
        raise ValueError(f"No mapping found for source_id: {source_id}")

    records = geojson_source_records(city_id, source_id)
    return [normalize_record(record, mapping) for record in records]


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize configured source records using explicit field mappings.")
    parser.add_argument("city_id", help="City profile identifier, e.g. milan")
    parser.add_argument("--source", required=True, help="Configured source_id to normalize")
    parser.add_argument("--mapping-version", default="milan_v1", help="Source mapping version file name")
    parser.add_argument("--out", help="Optional JSONL output path")
    args = parser.parse_args()

    rows = normalize_source(args.city_id, args.source, mapping_version=args.mapping_version)
    if args.out:
        write_jsonl(rows, Path(args.out))
        print(f"Wrote {len(rows)} normalized records to {args.out}")
        return

    print(json.dumps(rows[:3], indent=2, ensure_ascii=False))
    print(f"records={len(rows)}")


if __name__ == "__main__":
    main()

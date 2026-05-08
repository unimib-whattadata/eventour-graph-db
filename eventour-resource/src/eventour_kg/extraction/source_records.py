"""Convert configured local sources into provenance-preserving source records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eventour_kg.config.loaders import load_city_profile
from eventour_kg.extraction.geojson import load_geojson


ID_CANDIDATE_KEYS = (
    "id",
    "ID",
    "Id",
    "id_amat",
    "obj_id",
    "objID",
    "OBJ_ID",
    "OBJECTID",
    "objectid",
    "objectID",
    "fid",
    "FID",
    "osm_id",
    "stop_id",
    "station_id",
    "N.",
    "codice",
    "Codice",
    "CODICE",
)

SOURCE_ID_CANDIDATE_KEYS = {
    "benches": ("obj_id", "codice"),
    "picnic_tables": ("obj_id", "codice"),
    "trees": ("obj_id", "codice"),
}

NAME_CANDIDATE_KEYS = (
    "name",
    "Name",
    "nome",
    "Nome",
    "NOME",
    "denominazione",
    "Denominazione",
    "descrizione",
    "Descrizione",
    "stop_name",
)


def _pick_first(properties: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = properties.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _pick_external_id(source_id: str, properties: dict[str, Any]) -> str | None:
    source_specific_keys = SOURCE_ID_CANDIDATE_KEYS.get(source_id)
    if source_specific_keys:
        value = _pick_first(properties, source_specific_keys)
        if value not in (None, ""):
            return value
    return _pick_first(properties, ID_CANDIDATE_KEYS)


def _extract_point(geometry: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if not geometry or geometry.get("type") != "Point":
        return None, None

    coordinates = geometry.get("coordinates") or []
    if len(coordinates) < 2:
        return None, None

    return float(coordinates[0]), float(coordinates[1])


def geojson_source_records(city_id: str, source_id: str) -> list[dict[str, Any]]:
    profile = load_city_profile(city_id)
    source = next((item for item in profile.sources if item.source_id == source_id), None)
    if source is None:
        raise ValueError(f"Unknown source_id: {source_id}")
    if source.format != "geojson":
        raise ValueError(f"Source is not GeoJSON: {source_id}")

    payload = load_geojson(source.path)
    features = payload.get("features", [])
    rows: list[dict[str, Any]] = []

    for index, feature in enumerate(features):
        properties = feature.get("properties", {}) if isinstance(feature, dict) else {}
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        longitude, latitude = _extract_point(geometry)
        external_id = _pick_external_id(source.source_id, properties)
        label = _pick_first(properties, NAME_CANDIDATE_KEYS)
        local_id = external_id or str(index)

        rows.append(
            {
                "city_id": city_id,
                "source_id": source.source_id,
                "dataset_label": source.label,
                "domain": source.domain,
                "entity_family": source.entity_family,
                "integration_role": source.integration_role,
                "record_id": f"{source.source_id}:{local_id}",
                "external_id": external_id,
                "preferred_label": label,
                "geometry_type": (geometry or {}).get("type"),
                "longitude": longitude,
                "latitude": latitude,
                "raw_geometry": geometry,
                "raw_properties": properties,
            }
        )

    return rows


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export GeoJSON features as Eventour source records.")
    parser.add_argument("city_id", help="City profile identifier, e.g. milan")
    parser.add_argument("--source", required=True, help="Configured source_id to export")
    parser.add_argument("--out", help="Optional JSONL output path")
    args = parser.parse_args()

    rows = geojson_source_records(args.city_id, args.source)
    if args.out:
        write_jsonl(rows, Path(args.out))
        print(f"Wrote {len(rows)} source records to {args.out}")
        return

    print(json.dumps(rows[:3], indent=2, ensure_ascii=False))
    print(f"records={len(rows)}")


if __name__ == "__main__":
    main()

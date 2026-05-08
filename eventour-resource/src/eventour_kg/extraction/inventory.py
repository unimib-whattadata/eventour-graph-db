"""Inspect configured city sources and print a compact inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eventour_kg.config.loaders import load_city_profile, validate_city_profile
from eventour_kg.extraction.geojson import summarize_geojson
from eventour_kg.extraction.gtfs import summarize_gtfs_dir


def build_inventory(city_id: str) -> dict[str, object]:
    profile = load_city_profile(city_id)
    errors = validate_city_profile(city_id)
    sources = []

    for source in profile.sources:
        if not source.enabled:
            continue

        source_info: dict[str, object] = {
            "source_id": source.source_id,
            "label": source.label,
            "format": source.format,
            "domain": source.domain,
            "entity_family": source.entity_family,
            "integration_role": source.integration_role,
            "priority": source.priority,
            "path": str(source.path),
        }

        if source.format == "geojson":
            source_info.update(summarize_geojson(source.path))
        elif source.format == "gtfs_dir":
            source_info["files"] = summarize_gtfs_dir(source.path)

        sources.append(source_info)

    return {
        "city_id": profile.city_id,
        "city_name": profile.city_name,
        "dataset_root": str(profile.dataset_root),
        "errors": errors,
        "sources": sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Eventour KG source inventory.")
    parser.add_argument("city_id", help="City profile identifier, e.g. milan")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text summary")
    args = parser.parse_args()

    inventory = build_inventory(args.city_id)
    if args.json:
        print(json.dumps(inventory, indent=2, ensure_ascii=False))
        return

    print(f"City: {inventory['city_name']} ({inventory['city_id']})")
    if inventory["errors"]:
        print("Validation errors:")
        for error in inventory["errors"]:
            print(f"- {error}")

    for source in inventory["sources"]:
        summary = f"{source['source_id']} [{source['format']}] -> {source['integration_role']}"
        if "feature_count" in source:
            summary += f" | features={source['feature_count']}"
        print(summary)


if __name__ == "__main__":
    main()

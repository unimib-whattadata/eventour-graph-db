"""Batch-normalize all mapped GeoJSON sources for a configured city."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eventour_kg.config.loaders import load_city_profile
from eventour_kg.config.source_mappings import load_source_mappings
from eventour_kg.extraction.source_records import write_jsonl
from eventour_kg.normalization.source_normalizer import normalize_source


def normalize_city(city_id: str, mapping_version: str = "milan_v1") -> dict[str, object]:
    profile = load_city_profile(city_id)
    mappings = load_source_mappings(mapping_version)
    output_dir = Path(profile.dataset_root).parents[0] / "implementation" / "data" / "cities" / city_id / "normalized"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, object]] = []
    for source in profile.sources:
        if source.format != "geojson":
            continue
        if source.source_id not in mappings:
            continue

        rows = normalize_source(city_id, source.source_id, mapping_version=mapping_version)
        output_path = output_dir / f"{source.source_id}_normalized.jsonl"
        write_jsonl(rows, output_path)
        summary.append(
            {
                "source_id": source.source_id,
                "path": str(output_path),
                "records": len(rows),
                "entity_family": source.entity_family,
                "integration_role": source.integration_role,
            }
        )

    return {
        "city_id": city_id,
        "mapping_version": mapping_version,
        "normalized_sources": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize all mapped GeoJSON sources for a city.")
    parser.add_argument("city_id", help="City profile identifier, e.g. milan")
    parser.add_argument("--mapping-version", default="milan_v1", help="Source mapping version file name")
    parser.add_argument("--summary-out", help="Optional JSON summary output path")
    args = parser.parse_args()

    summary = normalize_city(args.city_id, mapping_version=args.mapping_version)
    if args.summary_out:
        output_path = Path(args.summary_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote normalization summary to {output_path}")
        return

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

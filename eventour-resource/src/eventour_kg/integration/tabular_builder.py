from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from eventour_kg.integration.tabular_mappings import DATASET_MAPPERS, map_feature_row
from eventour_kg.integration.tabular_schema import CANONICAL_COLUMNS


DEFAULT_DATASET_NAMES = tuple(sorted(DATASET_MAPPERS))


@dataclass(frozen=True)
class BuildOutputs:
    output_csv: Path
    summary_json: Path
    total_rows: int


def build_integrated_superset(
    datasets_dir: Path | str,
    output_csv: Path | str,
    summary_json: Path | str,
    dataset_names: Sequence[str] | None = None,
) -> BuildOutputs:
    datasets_dir = Path(datasets_dir)
    output_csv = Path(output_csv)
    summary_json = Path(summary_json)
    dataset_names = tuple(dataset_names) if dataset_names is not None else DEFAULT_DATASET_NAMES

    rows: list[dict[str, object]] = []
    rows_per_dataset: Counter[str] = Counter()
    rows_per_entity_family: Counter[str] = Counter()
    geometry_availability: Counter[str] = Counter()
    identifier_coverage: Counter[str] = Counter()

    for dataset_name in dataset_names:
        dataset_path = datasets_dir / dataset_name
        if not dataset_path.exists():
            raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

        feature_collection = _read_feature_collection(dataset_path)
        for feature in feature_collection["features"]:
            row = map_feature_row(dataset_name, feature)
            rows.append(row)
            rows_per_dataset[dataset_name] += 1

            entity_family = row.get("entity_family")
            if entity_family:
                rows_per_entity_family[str(entity_family)] += 1

            geometry_key = "with_geometry" if row.get("geometry_type") else "without_geometry"
            geometry_availability[geometry_key] += 1

            for field in ("source_record_key", "stable_identifier", "secondary_identifier", "composite_identifier"):
                if row.get(field) is not None:
                    identifier_coverage[field] += 1

    _write_csv(output_csv, rows)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total_rows": len(rows),
        "rows_per_dataset": dict(rows_per_dataset),
        "rows_per_entity_family": dict(rows_per_entity_family),
        "geometry_availability": {
            "with_geometry": geometry_availability.get("with_geometry", 0),
            "without_geometry": geometry_availability.get("without_geometry", 0),
        },
        "identifier_coverage": {
            "source_record_key": identifier_coverage.get("source_record_key", 0),
            "stable_identifier": identifier_coverage.get("stable_identifier", 0),
            "secondary_identifier": identifier_coverage.get("secondary_identifier", 0),
            "composite_identifier": identifier_coverage.get("composite_identifier", 0),
        },
    }
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return BuildOutputs(output_csv=output_csv, summary_json=summary_json, total_rows=len(rows))


def _read_feature_collection(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"Expected FeatureCollection in {path}")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError(f"Expected features list in {path}")
    return payload


def _write_csv(output_csv: Path, rows: list[dict[str, object]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CANONICAL_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

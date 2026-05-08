"""CLI entry point for the integrated tabular superset builder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eventour_kg.integration.tabular_builder import build_integrated_superset


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_paths(city_id: str) -> tuple[Path, Path, Path]:
    implementation_root = _repo_root()
    datasets_dir = implementation_root.parent / "datasets"
    integrated_dir = implementation_root / "data" / "cities" / city_id / "integrated"
    output_csv = integrated_dir / f"{city_id}_integrated_superset.csv"
    summary_json = integrated_dir / f"{city_id}_integrated_superset_summary.json"
    return datasets_dir, output_csv, summary_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the Eventour integrated tabular superset.")
    parser.add_argument("city_id", nargs="?", default="milan", help="City profile identifier, e.g. milan")
    parser.add_argument("--datasets-dir", help="Directory containing the inventoried GeoJSON datasets")
    parser.add_argument("--output-csv", help="Output CSV path")
    parser.add_argument("--summary-json", help="Output summary JSON path")
    args = parser.parse_args(argv)

    default_datasets_dir, default_output_csv, default_summary_json = _default_paths(args.city_id)
    datasets_dir = Path(args.datasets_dir) if args.datasets_dir else default_datasets_dir
    output_csv = Path(args.output_csv) if args.output_csv else default_output_csv
    summary_json = Path(args.summary_json) if args.summary_json else default_summary_json

    outputs = build_integrated_superset(
        datasets_dir=datasets_dir,
        output_csv=output_csv,
        summary_json=summary_json,
    )
    print(
        json.dumps(
            {
                "city_id": args.city_id,
                "output_csv": str(outputs.output_csv),
                "summary_json": str(outputs.summary_json),
                "total_rows": outputs.total_rows,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

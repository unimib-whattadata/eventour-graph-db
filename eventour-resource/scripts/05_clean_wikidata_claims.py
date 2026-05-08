#!/usr/bin/env python
"""Verify or regenerate the cleaned Wikidata subgraph layer."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconstruction-root", default="curation/reconstruction/milan")
    parser.add_argument("--regenerate", action="store_true")
    args = parser.parse_args()

    base = ROOT / args.reconstruction_root / "intermediate"
    raw = base / "wikidata_entity_subgraphs.jsonl"
    catalog = base / "wikidata_property_catalog.jsonl"
    cleaned = base / "wikidata_entity_subgraphs_cleaned.jsonl"
    report = base / "wikidata_entity_subgraphs_cleaned_report.json"

    if args.regenerate:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "eventour_kg.normalization.clean_wikidata_subgraph",
                "--input",
                str(raw),
                "--property-catalog",
                str(catalog),
                "--out",
                str(cleaned),
                "--report-out",
                str(report),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )

    for path in (raw, catalog, cleaned, report):
        if not path.exists():
            raise SystemExit(f"Missing cleanup artifact: {path.relative_to(ROOT)}")

    print(f"Raw subgraph rows: {count_jsonl(raw)}")
    print(f"Property catalog rows: {count_jsonl(catalog)}")
    print(f"Cleaned subgraph rows: {count_jsonl(cleaned)}")
    print(f"Cleanup report: {report.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

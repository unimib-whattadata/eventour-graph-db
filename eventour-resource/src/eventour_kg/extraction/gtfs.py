"""Minimal GTFS inspection utilities."""

from __future__ import annotations

import csv
from pathlib import Path


GTFS_CORE_FILES = (
    "agency.txt",
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "shapes.txt",
    "transfers.txt",
)


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        row_count = sum(1 for _ in reader)
    return max(row_count - 1, 0)


def summarize_gtfs_dir(gtfs_dir: Path) -> dict[str, int]:
    summary: dict[str, int] = {}
    for filename in GTFS_CORE_FILES:
        file_path = gtfs_dir / filename
        if file_path.exists():
            summary[filename] = count_csv_rows(file_path)
    return summary

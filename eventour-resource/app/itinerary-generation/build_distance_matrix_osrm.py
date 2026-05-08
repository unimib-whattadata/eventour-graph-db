#!/usr/bin/env python
"""Inspect the released OSRM distance-matrix generation artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "dynamic-planning" / "2-Generazione-Matrice-Distanze-Docker.ipynb"
POI_INPUT = ROOT / "dynamic-planning" / "pois_with_wikidata.csv"
DISTANCE_OUTPUT = ROOT / "dynamic-planning" / "poi_distances_with_types_and_wikidata_POI_final_subset_20ina_POIs.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Only verify required files.")
    args = parser.parse_args()

    required = (NOTEBOOK, POI_INPUT, DISTANCE_OUTPUT)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing OSRM distance-matrix artifacts:\n" + "\n".join(f"- {item}" for item in missing))

    if args.check_only:
        print("All OSRM distance-matrix artifacts are present.")
        return

    print("OSRM distance-matrix workflow artifact:")
    print(f"- Notebook: {NOTEBOOK.relative_to(ROOT)}")
    print(f"- POI input: {POI_INPUT.relative_to(ROOT)}")
    print(f"- Released distance matrix: {DISTANCE_OUTPUT.relative_to(ROOT)}")
    print("Run the notebook with a local OSRM service to regenerate the distance matrix.")


if __name__ == "__main__":
    main()

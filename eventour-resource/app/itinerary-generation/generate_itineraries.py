#!/usr/bin/env python
"""Inspect the released itinerary-generation workflow artifacts.

The executable research workflow is preserved as numbered notebooks in
`dynamic-planning/`. This command provides a stable CLI entry point for the
resource package by checking that the required notebooks and input CSV files are
present and by printing the execution order.
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent

WORKFLOW = (
    ("1-Selezione-POIs-Knowledge-Graph.ipynb", "Select POIs from the knowledge graph"),
    ("2-Generazione-Matrice-Distanze-Docker.ipynb", "Generate the OSRM walking-distance matrix"),
    ("3-Dataset_Fine_Tuning_Generator.ipynb", "Generate itinerary fine-tuning examples"),
    ("4-MISTRAL_FINETUNATO_ITINERARY_MCQs.ipynb", "Generate itinerary questions/facts for gamification"),
    ("5-Model_FInetuning.ipynb", "Fine-tune the itinerary-selection model"),
)

INPUTS = (
    "dynamic-planning/pois_with_wikidata.csv",
    "dynamic-planning/poi_distances_with_types_and_wikidata_POI_final_subset_20ina_POIs.csv",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Only verify required files.")
    args = parser.parse_args()

    missing: list[str] = []
    for notebook, _ in WORKFLOW:
        path = ROOT / "dynamic-planning" / notebook
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    for rel in INPUTS:
        if not (ROOT / rel).exists():
            missing.append(rel)

    if missing:
        raise SystemExit("Missing itinerary-generation artifacts:\n" + "\n".join(f"- {item}" for item in missing))

    if args.check_only:
        print("All itinerary-generation workflow artifacts are present.")
        return

    print("Itinerary-generation workflow:")
    for index, (notebook, description) in enumerate(WORKFLOW, start=1):
        print(f"{index}. dynamic-planning/{notebook} - {description}")
    print("\nRequired input CSV files:")
    for rel in INPUTS:
        print(f"- {rel}")


if __name__ == "__main__":
    main()

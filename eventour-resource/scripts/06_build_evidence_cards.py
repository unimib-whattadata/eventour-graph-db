#!/usr/bin/env python
"""Verify or regenerate the Wikidata evidence cards used for semantic curation."""

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
    cleaned = base / "wikidata_entity_subgraphs_cleaned.jsonl"
    ancestors = base / "wikidata_class_ancestors.jsonl"
    catalog = base / "wikidata_property_catalog.jsonl"
    evidence = base / "wikidata_entity_evidence.jsonl"
    report = base / "wikidata_entity_evidence_report.json"

    if args.regenerate:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "eventour_kg.classification.build_evidence_cards",
                "--input",
                str(cleaned),
                "--class-ancestors",
                str(ancestors),
                "--property-catalog",
                str(catalog),
                "--out",
                str(evidence),
                "--report-out",
                str(report),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )

    for path in (cleaned, ancestors, catalog, evidence, report):
        if not path.exists():
            raise SystemExit(f"Missing evidence-card artifact: {path.relative_to(ROOT)}")

    print(f"Evidence cards: {count_jsonl(evidence)}")
    print(f"Evidence report: {report.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

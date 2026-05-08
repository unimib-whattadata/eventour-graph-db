#!/usr/bin/env python
"""Verify released Wikidata candidate-extraction artifacts and export query paths."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", default="milan")
    parser.add_argument("--reconstruction-root", default="curation/reconstruction/milan")
    args = parser.parse_args()

    base = ROOT / args.reconstruction_root / "intermediate"
    raw_query = base / "wikidata_candidates.rq"
    normalized = base / "wikidata_normalized.jsonl"
    aggregated = base / "wikidata_entities_aggregated.jsonl"

    for path in (raw_query, normalized, aggregated):
        if not path.exists():
            raise SystemExit(f"Missing Wikidata candidate artifact: {path.relative_to(ROOT)}")

    print(f"City: {args.city}")
    print(f"Candidate SPARQL query: {raw_query.relative_to(ROOT)}")
    print(f"Normalized candidate rows: {count_jsonl(normalized)}")
    print(f"Aggregated unique entities: {count_jsonl(aggregated)}")


if __name__ == "__main__":
    main()

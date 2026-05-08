#!/usr/bin/env python
"""Verify released Wikidata one-hop subgraph artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconstruction-root", default="curation/reconstruction/milan")
    args = parser.parse_args()

    root = ROOT / args.reconstruction_root
    subgraphs = root / "intermediate" / "wikidata_entity_subgraphs.jsonl"
    raw_dir = root / "raw" / "wikidata_subgraphs"
    manifest = raw_dir / "manifest.jsonl"

    for path in (subgraphs, raw_dir):
        if not path.exists():
            raise SystemExit(f"Missing subgraph artifact: {path.relative_to(ROOT)}")

    print(f"Raw WDQS batch directory: {raw_dir.relative_to(ROOT)}")
    print(f"Raw batch files: {len(list(raw_dir.glob('batch_*.json')))}")
    if manifest.exists():
        print(f"Batch manifest: {manifest.relative_to(ROOT)}")
    print(f"Entity subgraph rows: {count_jsonl(subgraphs)}")


if __name__ == "__main__":
    main()

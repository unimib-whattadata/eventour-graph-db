#!/usr/bin/env python
"""Validate and optionally serialize the released VoID/DCAT metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="metadata/eventour-catalog.ttl")
    parser.add_argument("--output", default="metadata/eventour-catalog.nt")
    args = parser.parse_args()

    graph = Graph()
    graph.parse(ROOT / args.input, format="turtle")
    graph.serialize(ROOT / args.output, format="nt")
    print(f"Validated {args.input}: {len(graph)} metadata triples.")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

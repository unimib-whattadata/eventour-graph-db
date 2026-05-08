#!/usr/bin/env python
"""Build the curated Wikidata semantic-place RDF layer from released decisions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rdflib import Graph


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eventour_kg.rdf.wikidata_export import export_curated_wikidata_rows  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="curation/final/final-wikidata-places.jsonl")
    parser.add_argument("--nil-links", default="data/work/eventour_wikidata_nil_links.nt")
    parser.add_argument("--output", default="data/work/eventour_wikidata_place_layer.nt")
    args = parser.parse_args()

    graph = export_curated_wikidata_rows(load_jsonl(ROOT / args.input))

    nil_links = ROOT / args.nil_links
    if nil_links.exists():
        graph.parse(nil_links, format="nt")
    else:
        print(f"Warning: NIL-link file not found: {nil_links.relative_to(ROOT)}")
        print("Run scripts/09_assign_nil_areas.py first to reproduce the NIL-enriched layer.")

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(output, format="nt")
    print(f"Wrote {output.relative_to(ROOT)} with {len(graph)} triples.")


if __name__ == "__main__":
    main()

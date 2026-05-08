"""Materialize evidence cards from cleaned Wikidata subgraphs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eventour_kg.classification.evidence_cards import (
    build_class_ancestor_index,
    build_evidence_cards,
    build_evidence_report,
    build_property_catalog_index,
    load_jsonl,
)
from eventour_kg.extraction.source_records import write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Eventour evidence cards from cleaned Wikidata subgraphs.")
    parser.add_argument("--input", required=True, help="Cleaned subgraph JSONL input path")
    parser.add_argument("--class-ancestors", required=True, help="Class ancestor catalog JSONL path")
    parser.add_argument("--out", required=True, help="Evidence-card JSONL output path")
    parser.add_argument("--report-out", help="Optional summary JSON output path")
    parser.add_argument("--property-catalog", help="Optional property catalog JSONL path")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    class_ancestor_index = build_class_ancestor_index(load_jsonl(Path(args.class_ancestors)))
    property_catalog_index = None
    if args.property_catalog:
        property_catalog_index = build_property_catalog_index(load_jsonl(Path(args.property_catalog)))

    cards = build_evidence_cards(
        rows,
        class_ancestor_index=class_ancestor_index,
        property_catalog_index=property_catalog_index,
    )
    write_jsonl(cards, Path(args.out))

    if args.report_out:
        report = build_evidence_report(cards)
        Path(args.report_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(cards)} evidence cards to {args.out}")
    if args.report_out:
        print(f"Wrote evidence-card report to {args.report_out}")


if __name__ == "__main__":
    main()

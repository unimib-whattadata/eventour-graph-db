"""Build ontology, per-source, and merged RDF graphs for a city."""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph

from eventour_kg.rdf.gtfs_export import export_gtfs_structure_graph
from eventour_kg.rdf.local_export import export_normalized_rows, load_jsonl
from eventour_kg.rdf.ontology import build_eventour_ontology_graph
from eventour_kg.rdf.serialize import serialize_graph
from eventour_kg.rdf.wikidata_export import export_curated_wikidata_rows


def _write_graph_pair(graph: Graph, base_path: Path) -> None:
    serialize_graph(graph, base_path.with_suffix(".ttl"), format="turtle")
    serialize_graph(graph, base_path.with_suffix(".jsonld"), format="json-ld")


def build_city_kg(
    *,
    normalized_dir: Path,
    gtfs_dir: Path,
    out_dir: Path,
    wikidata_curated_path: Path | None = None,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir = out_dir / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)

    ontology_graph = build_eventour_ontology_graph()
    _write_graph_pair(ontology_graph, out_dir / "eventour_ontology")

    merged = Graph()
    merged += ontology_graph
    source_graph_count = 0

    for normalized_path in sorted(normalized_dir.glob("*_normalized.jsonl")):
        rows = load_jsonl(normalized_path)
        if not rows:
            continue
        source_graph = export_normalized_rows(rows)
        source_id = normalized_path.name.removesuffix("_normalized.jsonl")
        _write_graph_pair(source_graph, source_dir / source_id)
        merged += source_graph
        source_graph_count += 1

    gtfs_graph = export_gtfs_structure_graph(gtfs_dir)
    _write_graph_pair(gtfs_graph, source_dir / "gtfs_structure")
    merged += gtfs_graph
    source_graph_count += 1

    _write_graph_pair(merged, out_dir / "milan_local_kg")

    eventour_merged = Graph()
    eventour_merged += merged

    wikidata_graph_included = False
    if wikidata_curated_path is not None and wikidata_curated_path.exists():
        wikidata_rows = load_jsonl(wikidata_curated_path)
        if wikidata_rows:
            wikidata_graph = export_curated_wikidata_rows(wikidata_rows)
            _write_graph_pair(wikidata_graph, source_dir / "wikidata_curated")
            eventour_merged += wikidata_graph
            source_graph_count += 1
            wikidata_graph_included = True
            _write_graph_pair(eventour_merged, out_dir / "milan_eventour_kg")

    return {
        "out_dir": str(out_dir),
        "source_graph_count": source_graph_count,
        "merged_triple_count": len(eventour_merged),
        "local_triple_count": len(merged),
        "wikidata_graph_included": wikidata_graph_included,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Eventour local RDF graph for one city.")
    parser.add_argument("--normalized-dir", required=True, help="Directory containing normalized JSONL sources")
    parser.add_argument("--gtfs-dir", required=True, help="GTFS directory path")
    parser.add_argument("--out-dir", required=True, help="Output RDF directory")
    parser.add_argument("--wikidata-curated-input", help="Curated Wikidata JSONL input")
    args = parser.parse_args()

    summary = build_city_kg(
        normalized_dir=Path(args.normalized_dir),
        gtfs_dir=Path(args.gtfs_dir),
        out_dir=Path(args.out_dir),
        wikidata_curated_path=Path(args.wikidata_curated_input) if args.wikidata_curated_input else None,
    )
    print(summary)


if __name__ == "__main__":
    main()

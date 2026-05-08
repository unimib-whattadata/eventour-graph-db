"""Serialization helpers for RDF graphs."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph


def serialize_graph(graph: Graph, output_path: Path, *, format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output_path, format=format)

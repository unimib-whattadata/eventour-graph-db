#!/usr/bin/env python
"""Merge ontology, municipal, NIL, and Wikidata layers into one N-Triples file."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUTS = (
    "ontology/eventour.nt",
    "data/work/eventour_municipal_backbone.nt",
    "data/work/eventour_municipal_nil_inferred.nt",
    "data/work/eventour_wikidata_place_layer.nt",
)


def copy_bytes(source: Path, out) -> None:
    with source.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
        out.write(b"\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/work/eventour_reconstructed_kg.nt")
    parser.add_argument("--inputs", nargs="*", default=list(DEFAULT_INPUTS))
    args = parser.parse_args()

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("wb") as out:
        for rel in args.inputs:
            path = ROOT / rel
            if not path.exists():
                raise SystemExit(f"Required merge input not found: {rel}")
            if path.suffix == ".ttl":
                raise SystemExit(
                    f"{rel} is Turtle. Convert it to N-Triples first or omit it from --inputs."
                )
            print(f"Adding {rel}")
            copy_bytes(path, out)

    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

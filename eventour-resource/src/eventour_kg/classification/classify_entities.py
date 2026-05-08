"""Run semantic classification for Eventour entity-level classification inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eventour_kg.classification.backends import get_backend
from eventour_kg.classification.policy import should_review
from eventour_kg.classification.prompt_builder import build_prompt
from eventour_kg.extraction.source_records import write_jsonl


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def classify_entities(
    entities: list[dict[str, Any]],
    *,
    backend_name: str,
    include_prompt: bool = False,
) -> list[dict[str, Any]]:
    backend = get_backend(backend_name)
    outputs: list[dict[str, Any]] = []

    for entity in entities:
        result = backend.classify(entity)
        row = {
            **entity,
            **result.to_dict(),
            "needs_review": should_review(
                result,
                entity_needs_label_enrichment=bool(entity.get("needs_label_enrichment")),
            ),
        }
        if include_prompt:
            row["prompt"] = build_prompt(entity)
        outputs.append(row)

    return outputs


def split_by_decision(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        decision = row["decision"]
        grouped.setdefault(decision, []).append(row)
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify Eventour entity records or evidence-card inputs.")
    parser.add_argument("--input", required=True, help="Entity or evidence-card JSONL input path")
    parser.add_argument("--out", required=True, help="Classification JSONL output path")
    parser.add_argument("--review-out", required=True, help="Review queue JSONL output path")
    parser.add_argument("--backend", default="heuristic", help="Classifier backend name")
    parser.add_argument("--split-dir", help="Optional directory to write one JSONL file per decision")
    parser.add_argument("--include-prompt", action="store_true", help="Include rendered prompt text in each output row")
    parser.add_argument("--limit", type=int, help="Optional number of input entities to classify")
    args = parser.parse_args()

    entities = load_jsonl(Path(args.input))
    if args.limit is not None:
        entities = entities[: args.limit]
    outputs = classify_entities(
        entities,
        backend_name=args.backend,
        include_prompt=args.include_prompt,
    )
    write_jsonl(outputs, Path(args.out))

    review_rows = [row for row in outputs if row["needs_review"]]
    write_jsonl(review_rows, Path(args.review_out))

    if args.split_dir:
        split_dir = Path(args.split_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        for decision, rows in split_by_decision(outputs).items():
            write_jsonl(rows, split_dir / f"{decision}.jsonl")

    print(f"Wrote {len(outputs)} classifications to {args.out}")
    print(f"Wrote {len(review_rows)} review records to {args.review_out}")


if __name__ == "__main__":
    main()

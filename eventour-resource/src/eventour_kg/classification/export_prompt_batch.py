"""Export prompt packages for aggregated Wikidata entities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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


def export_prompt_batch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        item_qid = row.get("item_qid")
        if not item_qid:
            raise ValueError("Aggregated entity row is missing item_qid; cannot build stable prompt batch.")
        output.append(
            {
                "item_qid": item_qid,
                "preferred_label": row.get("preferred_label"),
                "needs_label_enrichment": row.get("needs_label_enrichment"),
                "prompt": build_prompt(row),
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Export prompt packages for aggregated Wikidata entities.")
    parser.add_argument("--input", required=True, help="Aggregated Wikidata JSONL input path")
    parser.add_argument("--out", required=True, help="Prompt-batch JSONL output path")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    output = export_prompt_batch(rows)
    write_jsonl(output, Path(args.out))
    print(f"Wrote {len(output)} prompt packages to {args.out}")


if __name__ == "__main__":
    main()

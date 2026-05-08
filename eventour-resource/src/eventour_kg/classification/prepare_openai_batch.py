"""Prepare Tier-safe OpenAI Batch API request files for Eventour classification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eventour_kg.classification.openai_structured import estimate_text_tokens, response_format
from eventour_kg.extraction.source_records import write_jsonl


DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 320
DEFAULT_MAX_BATCH_INPUT_TOKENS = 4_500_000


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def make_batch_request(
    row: dict[str, Any],
    *,
    model: str,
    max_output_tokens: int,
) -> dict[str, Any]:
    prompt = row["prompt"]
    item_qid = row.get("item_qid")
    if not item_qid:
        raise ValueError("Prompt batch row is missing item_qid; cannot build stable batch custom_id.")
    return {
        "custom_id": f"wd::{item_qid}",
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "reasoning": {"effort": "low"},
            "text": {"format": response_format(), "verbosity": "low"},
            "max_output_tokens": max_output_tokens,
        },
    }


def chunk_requests(
    rows: list[dict[str, Any]],
    *,
    model: str,
    max_output_tokens: int,
    max_batch_input_tokens: int,
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    manifest_entries: list[dict[str, Any]] = []
    current_batch: list[dict[str, Any]] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current_batch, current_tokens
        if not current_batch:
            return
        batch_index = len(batches)
        batches.append(current_batch)
        manifest_entries.append(
            {
                "batch_index": batch_index,
                "request_count": len(current_batch),
                "estimated_input_tokens": current_tokens,
            }
        )
        current_batch = []
        current_tokens = 0

    for row in rows:
        request = make_batch_request(row, model=model, max_output_tokens=max_output_tokens)
        estimated_tokens = estimate_text_tokens(row["prompt"])
        if current_batch and current_tokens + estimated_tokens > max_batch_input_tokens:
            flush()
        current_batch.append(request)
        current_tokens += estimated_tokens

    flush()
    return batches, manifest_entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare OpenAI Batch API request files.")
    parser.add_argument("--input", required=True, help="Prompt-batch JSONL input path")
    parser.add_argument("--out-dir", required=True, help="Directory for batch JSONL files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model name")
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument(
        "--max-batch-input-tokens",
        type=int,
        default=DEFAULT_MAX_BATCH_INPUT_TOKENS,
        help="Conservative estimated input-token ceiling per batch file",
    )
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    batches, manifest_entries = chunk_requests(
        rows,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
        max_batch_input_tokens=args.max_batch_input_tokens,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for entry, batch_rows in zip(manifest_entries, batches, strict=True):
        batch_path = out_dir / f"openai_batch_{entry['batch_index']:03d}.jsonl"
        write_jsonl(batch_rows, batch_path)
        entry["path"] = str(batch_path)

    manifest = {
        "input_path": str(Path(args.input)),
        "model": args.model,
        "max_output_tokens": args.max_output_tokens,
        "max_batch_input_tokens": args.max_batch_input_tokens,
        "total_requests": len(rows),
        "estimated_total_input_tokens": sum(entry["estimated_input_tokens"] for entry in manifest_entries),
        "batch_count": len(manifest_entries),
        "batches": manifest_entries,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(manifest_entries)} batch files to {out_dir}")
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()

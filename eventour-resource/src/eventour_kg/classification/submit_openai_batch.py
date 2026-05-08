"""Submit a prepared batch request file to the OpenAI Batch API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload and submit one OpenAI batch request file.")
    parser.add_argument("--input", required=True, help="Prepared batch JSONL path")
    parser.add_argument("--metadata-out", required=True, help="Where to write submission metadata JSON")
    parser.add_argument("--completion-window", default="24h", help="OpenAI batch completion window")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The OpenAI SDK is required to submit a batch.") from exc

    client = OpenAI(api_key=api_key)
    input_path = Path(args.input)
    with input_path.open("rb") as handle:
        file_obj = client.files.create(file=handle, purpose="batch")

    batch = client.batches.create(
        input_file_id=file_obj.id,
        endpoint="/v1/responses",
        completion_window=args.completion_window,
        metadata={"source_file": str(input_path)},
    )

    payload = {
        "input_path": str(input_path),
        "input_file_id": file_obj.id,
        "batch_id": batch.id,
        "status": getattr(batch, "status", None),
        "completion_window": args.completion_window,
    }
    Path(args.metadata_out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Fetch OpenAI batch status and optionally download output artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def _write_response_content(content_obj: object, output_path: Path) -> None:
    if hasattr(content_obj, "text"):
        payload = content_obj.text
        output_path.write_text(payload, encoding="utf-8")
        return
    if hasattr(content_obj, "read"):
        data = content_obj.read()
        if isinstance(data, bytes):
            output_path.write_bytes(data)
        else:
            output_path.write_text(str(data), encoding="utf-8")
        return
    output_path.write_text(str(content_obj), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OpenAI batch status and download artifacts.")
    parser.add_argument("--batch-id", required=True, help="OpenAI batch id")
    parser.add_argument("--status-out", required=True, help="Where to write the batch status JSON")
    parser.add_argument("--output-jsonl", help="Optional path to download the batch output file")
    parser.add_argument("--error-jsonl", help="Optional path to download the batch error file")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The OpenAI SDK is required to fetch batch artifacts.") from exc

    client = OpenAI(api_key=api_key)
    batch = client.batches.retrieve(args.batch_id)

    if hasattr(batch, "model_dump"):
        status_payload = batch.model_dump(exclude_none=True)
    elif hasattr(batch, "to_dict"):
        status_payload = batch.to_dict()
    else:
        status_payload = {"batch_id": args.batch_id, "repr": repr(batch)}

    status_path = Path(args.status_out)
    status_path.write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    output_file_id = status_payload.get("output_file_id")
    if args.output_jsonl and output_file_id:
        content = client.files.content(output_file_id)
        _write_response_content(content, Path(args.output_jsonl))

    error_file_id = status_payload.get("error_file_id")
    if args.error_jsonl and error_file_id:
        content = client.files.content(error_file_id)
        _write_response_content(content, Path(args.error_jsonl))

    print(
        json.dumps(
            {
                "batch_id": args.batch_id,
                "status_out": args.status_out,
                "output_file_id": output_file_id,
                "error_file_id": error_file_id,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

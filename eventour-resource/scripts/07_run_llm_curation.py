#!/usr/bin/env python
"""Verify released LLM curation inputs and outputs.

The public release includes the prompt template, JSON schema, prepared batch
requests, raw batch outputs, and parsed model decisions. Re-running this step
against an LLM provider is optional and requires user credentials.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> None:
    required = [
        ROOT / "curation/llm-curation/prompt-template.md",
        ROOT / "curation/llm-curation/structured-output-schema.json",
        ROOT / "curation/llm-curation/raw-model-outputs.jsonl",
        ROOT / "curation/reconstruction/milan/intermediate/wikidata_entity_classification_openai_full.jsonl",
    ]
    for path in required:
        if not path.exists():
            raise SystemExit(f"Missing LLM curation artifact: {path.relative_to(ROOT)}")

    print("LLM prompt and structured-output schema are present.")
    print(f"Raw model output rows: {count_jsonl(required[2])}")
    print(f"Parsed model decisions: {count_jsonl(required[3])}")
    print("Optional rerun scripts are available under src/eventour_kg/classification/.")


if __name__ == "__main__":
    main()

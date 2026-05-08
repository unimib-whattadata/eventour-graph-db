"""Import OpenAI Batch API results into Eventour classification artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eventour_kg.classification.openai_structured import (
    coerce_result,
    extract_output_text,
    extract_refusal,
    parse_output_json,
)
from eventour_kg.classification.policy import ClassificationResult, Decision, should_review
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


def load_entity_index(path: Path) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(path)
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_qid = row.get("item_qid")
        if item_qid:
            index[f"wd::{item_qid}"] = row
    return index


def import_results(
    batch_rows: list[dict[str, Any]],
    *,
    entity_index: dict[str, dict[str, Any]],
    backend_name: str,
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    missing_custom_ids: list[str] = []
    for row in batch_rows:
        custom_id = row.get("custom_id")
        entity_row = entity_index.get(custom_id)
        if entity_row is None:
            if custom_id:
                missing_custom_ids.append(custom_id)
            continue

        response_wrapper = row.get("response") or {}
        response_body = response_wrapper.get("body") or {}
        error = row.get("error")
        metadata = {
            "batch_custom_id": custom_id,
            "request_id": response_wrapper.get("request_id"),
            "status_code": response_wrapper.get("status_code"),
            "error": error,
            "response_id": response_body.get("id"),
            "usage": response_body.get("usage"),
        }

        if error:
            result = ClassificationResult(
                decision=Decision.CANDIDATE_EXCEPTION,
                eventour_category=None,
                confidence=0.0,
                rationale=f"Batch request error: {error}",
                backend=backend_name,
                metadata=metadata,
            )
        else:
            refusal = extract_refusal(response_body)
            if refusal:
                result = ClassificationResult(
                    decision=Decision.CANDIDATE_EXCEPTION,
                    eventour_category=None,
                    confidence=0.0,
                    rationale=f"Model refusal: {refusal}",
                    backend=backend_name,
                    metadata=metadata,
                )
            else:
                output_text = extract_output_text(response_body)
                if not output_text:
                    result = ClassificationResult(
                        decision=Decision.CANDIDATE_EXCEPTION,
                        eventour_category=None,
                        confidence=0.0,
                        rationale="No structured output text found in batch response.",
                        backend=backend_name,
                        metadata=metadata,
                    )
                else:
                    try:
                        payload = parse_output_json(output_text)
                        base_result = coerce_result(payload, backend_name=backend_name)
                        result = ClassificationResult(
                            decision=base_result.decision,
                            eventour_category=base_result.eventour_category,
                            confidence=base_result.confidence,
                            rationale=base_result.rationale,
                            backend=base_result.backend,
                            metadata=metadata,
                        )
                    except Exception as exc:
                        parse_metadata = {
                            **metadata,
                            "output_text_preview": output_text[:500],
                            "parse_error": str(exc),
                        }
                        result = ClassificationResult(
                            decision=Decision.CANDIDATE_EXCEPTION,
                            eventour_category=None,
                            confidence=0.0,
                            rationale="Invalid structured output in batch response.",
                            backend=backend_name,
                            metadata=parse_metadata,
                        )

        outputs.append(
            {
                **entity_row,
                **result.to_dict(),
                "needs_review": should_review(
                    result,
                    entity_needs_label_enrichment=bool(entity_row.get("needs_label_enrichment")),
                ),
            }
        )

    if missing_custom_ids:
        sample = ", ".join(sorted(missing_custom_ids)[:5])
        raise RuntimeError(
            "Some batch results could not be matched back to entity records. "
            f"Missing custom_id count: {len(missing_custom_ids)}. Sample: {sample}"
        )

    return outputs


def split_by_decision(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["decision"], []).append(row)
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import OpenAI Batch API classification results.")
    parser.add_argument("--input", required=True, help="Downloaded OpenAI batch result JSONL")
    parser.add_argument(
        "--entities",
        required=True,
        help="Aggregated entity JSONL used to reconstruct rich classification records",
    )
    parser.add_argument("--out", required=True, help="Output classification JSONL path")
    parser.add_argument("--review-out", required=True, help="Output review queue JSONL path")
    parser.add_argument("--split-dir", help="Optional directory to split rows by decision")
    parser.add_argument("--backend-name", default="openai:gpt-5-mini:batch", help="Backend label stored in outputs")
    args = parser.parse_args()

    entity_index = load_entity_index(Path(args.entities))
    batch_rows = load_jsonl(Path(args.input))
    outputs = import_results(
        batch_rows,
        entity_index=entity_index,
        backend_name=args.backend_name,
    )
    write_jsonl(outputs, Path(args.out))
    review_rows = [row for row in outputs if row["needs_review"]]
    write_jsonl(review_rows, Path(args.review_out))

    if args.split_dir:
        split_dir = Path(args.split_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        for decision, rows in split_by_decision(outputs).items():
            write_jsonl(rows, split_dir / f"{decision}.jsonl")

    print(f"Wrote {len(outputs)} imported classifications to {args.out}")
    print(f"Wrote {len(review_rows)} review records to {args.review_out}")


if __name__ == "__main__":
    main()

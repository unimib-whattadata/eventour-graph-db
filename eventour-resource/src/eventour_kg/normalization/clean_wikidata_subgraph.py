"""Apply a universal cleanup policy to raw Wikidata entity subgraphs."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from eventour_kg.extraction.source_records import write_jsonl


FALLBACK_DROP_PROPERTIES = {
    "P625": "raw coordinates duplicated outside claims",
    "P373": "commons category editorial metadata",
    "P910": "topic's main category editorial metadata",
    "P935": "commons gallery editorial metadata",
    "P143": "imported from Wikimedia project editorial metadata",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_property_catalog(path: Path) -> dict[str, dict[str, Any]]:
    catalog = load_jsonl(path)
    return {
        row["property_qid"]: row
        for row in catalog
        if row.get("property_qid")
    }


def claim_signature(claim: dict[str, Any]) -> tuple[Any, ...]:
    return (
        claim.get("property_qid"),
        claim.get("value_type"),
        claim.get("value_qid"),
        claim.get("value_uri"),
        claim.get("value_literal"),
        claim.get("value_datatype"),
        claim.get("value_lang"),
    )


def should_drop_claim(
    claim: dict[str, Any],
    *,
    property_catalog: dict[str, dict[str, Any]],
) -> tuple[bool, str]:
    property_qid = claim.get("property_qid")
    catalog_entry = property_catalog.get(property_qid or "")
    if catalog_entry and catalog_entry.get("cleanup_action") == "drop":
        return True, str(catalog_entry.get("cleanup_reason") or "catalog cleanup")

    if property_qid in FALLBACK_DROP_PROPERTIES:
        return True, FALLBACK_DROP_PROPERTIES[property_qid]

    value_uri = claim.get("value_uri") or ""
    value_datatype = claim.get("value_datatype") or ""
    if "commons.wikimedia.org/wiki/Special:FilePath/" in value_uri:
        return True, "media file link"
    if value_datatype == "http://www.opengis.net/ont/geosparql#wktLiteral":
        return True, "raw coordinate literal"

    return False, "kept"


def clean_row(
    row: dict[str, Any],
    *,
    property_catalog: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], Counter[str]]:
    seen_signatures: set[tuple[Any, ...]] = set()
    kept_claims: list[dict[str, Any]] = []
    dropped_reasons: Counter[str] = Counter()

    for claim in row.get("claims", []):
        drop, reason = should_drop_claim(claim, property_catalog=property_catalog)
        if drop:
            dropped_reasons[reason] += 1
            continue

        signature = claim_signature(claim)
        if signature in seen_signatures:
            dropped_reasons["duplicate claim"] += 1
            continue
        seen_signatures.add(signature)
        kept_claims.append(claim)

    cleaned_row = {
        **row,
        "raw_claim_count": row.get("claim_count", 0),
        "claim_count": len(kept_claims),
        "claims": kept_claims,
        "cleanup_summary": {
            "dropped_claim_count": int(sum(dropped_reasons.values())),
            "dropped_reasons": dict(dropped_reasons),
        },
    }
    return cleaned_row, dropped_reasons


def clean_rows(
    rows: list[dict[str, Any]],
    *,
    property_catalog: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cleaned_rows: list[dict[str, Any]] = []
    overall_reasons: Counter[str] = Counter()
    total_before = 0
    total_after = 0

    for row in rows:
        total_before += row.get("claim_count", 0)
        cleaned_row, dropped_reasons = clean_row(row, property_catalog=property_catalog)
        total_after += cleaned_row["claim_count"]
        overall_reasons.update(dropped_reasons)
        cleaned_rows.append(cleaned_row)

    report = {
        "entity_count": len(rows),
        "claim_count_before": total_before,
        "claim_count_after": total_after,
        "claims_dropped": total_before - total_after,
        "drop_reason_counts": dict(overall_reasons),
    }
    return cleaned_rows, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply universal cleanup rules to raw Wikidata subgraphs.")
    parser.add_argument("--input", required=True, help="Raw entity subgraph JSONL input path")
    parser.add_argument("--property-catalog", required=True, help="Property catalog JSONL path")
    parser.add_argument("--out", required=True, help="Cleaned entity subgraph JSONL output path")
    parser.add_argument("--report-out", help="Optional cleanup report JSON output path")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    property_catalog = load_property_catalog(Path(args.property_catalog))
    cleaned_rows, report = clean_rows(rows, property_catalog=property_catalog)
    write_jsonl(cleaned_rows, Path(args.out))

    if args.report_out:
        Path(args.report_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(cleaned_rows)} cleaned subgraph rows to {args.out}")
    if args.report_out:
        print(f"Wrote cleanup report to {args.report_out}")


if __name__ == "__main__":
    main()

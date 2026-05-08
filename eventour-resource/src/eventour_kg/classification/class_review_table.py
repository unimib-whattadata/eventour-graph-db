"""Generate class-level review tables from normalized Wikidata candidate records."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_review_rows(rows: list[dict]) -> list[dict[str, object]]:
    by_class: dict[tuple[str | None, str | None], dict[str, object]] = {}

    for row in rows:
        extras = row.get("extras", {})
        class_qid = extras.get("direct_class_qid")
        class_label = extras.get("direct_class_label")
        key = (class_qid, class_label)

        bucket = by_class.setdefault(
            key,
            {
                "direct_class_qid": class_qid,
                "direct_class_label": class_label,
                "count": 0,
                "sample_item_qid": row.get("external_id"),
                "sample_item_label": row.get("preferred_label"),
                "decision": "",
                "eventour_category": "",
                "needs_review": "yes",
                "notes": "",
            },
        )
        bucket["count"] += 1

    return sorted(
        by_class.values(),
        key=lambda item: (-int(item["count"]), item["direct_class_label"] or ""),
    )


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "direct_class_qid",
        "direct_class_label",
        "count",
        "sample_item_qid",
        "sample_item_label",
        "decision",
        "eventour_category",
        "needs_review",
        "notes",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a class-review CSV from normalized Wikidata candidates.")
    parser.add_argument("--input", required=True, help="Normalized Wikidata JSONL input path")
    parser.add_argument("--out", required=True, help="CSV output path")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    review_rows = build_review_rows(rows)
    write_csv(review_rows, Path(args.out))
    print(f"Wrote {len(review_rows)} class review rows to {args.out}")


if __name__ == "__main__":
    main()

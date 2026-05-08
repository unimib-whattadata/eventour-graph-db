#!/usr/bin/env python
"""Verify released human-evaluation and final Wikidata adjudication artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def count_final_labels(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                counts[json.loads(line).get("final_label", "UNKNOWN")] += 1
    return counts


def main() -> None:
    adjudication = ROOT / "curation/human-evaluation/adjudication.csv"
    agreement = ROOT / "curation/human-evaluation/agreement-report.json"
    final = ROOT / "curation/final/final-wikidata-places.jsonl"
    summary = ROOT / "curation/reconstruction/milan/final/wikidata_decisions/wikidata_curated_summary.json"

    for path in (adjudication, agreement, final, summary):
        if not path.exists():
            raise SystemExit(f"Missing adjudication artifact: {path.relative_to(ROOT)}")

    summary_data = json.loads(summary.read_text(encoding="utf-8"))
    print(f"Adjudication CSV: {adjudication.relative_to(ROOT)}")
    print(f"Agreement report: {agreement.relative_to(ROOT)}")
    final_label_counts = count_final_labels(final)
    retained = sum(count for label, count in final_label_counts.items() if label != "exclude")
    print(f"Final curated Wikidata records: {count_jsonl(final)}")
    print(f"Final retained Wikidata places: {retained}")
    print(f"Final label counts: {dict(final_label_counts)}")
    print(json.dumps(summary_data, indent=2, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()

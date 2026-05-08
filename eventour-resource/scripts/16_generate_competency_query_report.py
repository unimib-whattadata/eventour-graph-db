#!/usr/bin/env python
"""Generate the competency-query documentation from query and result files."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUERY_DIR = ROOT / "queries" / "competency"
RESULT_DIR = ROOT / "queries" / "expected-results"
DOC_PATH = ROOT / "docs" / "competency-queries.md"


def load_runtime_rows() -> list[dict[str, str]]:
    with (RESULT_DIR / "runtime-summary.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def query_file_for(cq_id: str) -> Path:
    matches = sorted(QUERY_DIR.glob(f"{cq_id}_*.rq"))
    if not matches:
        raise FileNotFoundError(f"No query file found for {cq_id}")
    return matches[0]


def ensure_result_file(row: dict[str, str]) -> Path:
    cq_id = row["query"]
    result_file = RESULT_DIR / f"{cq_id}_results.csv"
    if result_file.exists():
        return result_file

    with result_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query", "result_count", "runtime_seconds", "notes"])
        writer.writeheader()
        writer.writerow(
            {
                "query": cq_id,
                "result_count": row["result_count"],
                "runtime_seconds": row["runtime_seconds"],
                "notes": row["notes"],
            }
        )
    return result_file


def csv_preview(path: Path, *, max_rows: int = 20) -> str:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) <= max_rows + 1:
        return "\n".join(lines)
    preview = lines[: max_rows + 1]
    preview.append(f"... ({len(lines) - 1} data rows total)")
    return "\n".join(preview)


def main() -> None:
    runtime_rows = load_runtime_rows()

    lines: list[str] = [
        "# Competency Queries",
        "",
        "This page embeds the competency questions, the exact SPARQL query files, and the recorded results used for the Eventour Milan release. Result counts and runtimes are copied from `queries/expected-results/runtime-summary.csv`; per-query result files are stored in `queries/expected-results/`.",
        "",
        "## Summary",
        "",
        "| Query | Purpose | Result count | Runtime (s) | Notes |",
        "|---|---|---:|---:|---|",
    ]

    for row in runtime_rows:
        lines.append(
            f"| {row['query']} | {row['purpose']} | {row['result_count']} | {row['runtime_seconds']} | {row['notes']} |"
        )

    lines.extend(
        [
            "",
            "## Detailed Queries and Results",
            "",
        ]
    )

    for row in runtime_rows:
        cq_id = row["query"]
        query_path = query_file_for(cq_id)
        result_path = ensure_result_file(row)
        rel_query = query_path.relative_to(ROOT)
        rel_result = result_path.relative_to(ROOT)

        lines.extend(
            [
                f"### {cq_id}: {row['purpose']}",
                "",
                f"- Query file: `{rel_query}`",
                f"- Result file: `{rel_result}`",
                f"- Result count: `{row['result_count']}`",
                f"- Runtime: `{row['runtime_seconds']}` seconds",
                f"- Notes: `{row['notes']}`",
                "",
                "Result:",
                "",
                "```csv",
                csv_preview(result_path),
                "```",
                "",
                "SPARQL:",
                "",
                "```sparql",
                query_path.read_text(encoding="utf-8").strip(),
                "```",
                "",
            ]
        )

    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {DOC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

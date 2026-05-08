"""Fetch one-hop class ancestors for observed Wikidata direct classes."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from eventour_kg.extraction.source_records import write_jsonl
from eventour_kg.extraction.wikidata import (
    build_class_ancestor_query,
    qid_from_uri,
)


WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
DEFAULT_BATCH_SIZE = 50
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 4
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_USER_AGENT = "EventourKG/0.1 (research pipeline; class ancestor fetcher)"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _post_sparql(query: str, *, timeout_seconds: int, user_agent: str) -> dict[str, Any]:
    payload = urlencode({"query": query, "format": "json"}).encode("utf-8")
    request = Request(
        WDQS_ENDPOINT,
        data=payload,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": user_agent,
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def execute_query_with_retry(
    query: str,
    *,
    timeout_seconds: int,
    max_retries: int,
    sleep_seconds: float,
    user_agent: str,
) -> dict[str, Any]:
    attempt = 0
    while True:
        try:
            return _post_sparql(query, timeout_seconds=timeout_seconds, user_agent=user_agent)
        except HTTPError as exc:
            if attempt >= max_retries:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else sleep_seconds * (2 ** attempt)
            time.sleep(delay)
            attempt += 1
        except URLError:
            if attempt >= max_retries:
                raise
            time.sleep(sleep_seconds * (2 ** attempt))
            attempt += 1


def _binding_value(binding: dict[str, Any], key: str) -> str | None:
    value = binding.get(key)
    if not value:
        return None
    return value.get("value")


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def collect_direct_classes(rows: list[dict[str, Any]]) -> dict[str, str | None]:
    direct_classes: dict[str, str | None] = {}
    for row in rows:
        for qid, label in zip(row.get("direct_class_qids", []), row.get("direct_class_labels", []), strict=False):
            if qid and qid not in direct_classes:
                direct_classes[qid] = label
        # fallback if labels shorter than qids array
        for qid in row.get("direct_class_qids", []):
            if qid and qid not in direct_classes:
                direct_classes[qid] = None
    return direct_classes


def parse_ancestor_bindings(bindings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ancestors_by_class: dict[str, dict[str, Any]] = {}

    for binding in bindings:
        direct_uri = _binding_value(binding, "directClass")
        direct_qid = qid_from_uri(direct_uri)
        if not direct_qid:
            continue

        bucket = ancestors_by_class.setdefault(
            direct_qid,
            {
                "direct_class_qid": direct_qid,
                "direct_class_uri": direct_uri,
                "direct_class_label": _binding_value(binding, "directClassLabel"),
                "ancestors": [],
            },
        )

        ancestor_uri = _binding_value(binding, "ancestorClass")
        ancestor_qid = qid_from_uri(ancestor_uri)
        if not ancestor_qid:
            continue
        bucket["ancestors"].append(
            {
                "qid": ancestor_qid,
                "uri": ancestor_uri,
                "label": _binding_value(binding, "ancestorClassLabel"),
            }
        )

    return ancestors_by_class


def fetch_class_ancestors(
    direct_class_index: dict[str, str | None],
    *,
    language: str,
    batch_size: int,
    timeout_seconds: int,
    max_retries: int,
    sleep_seconds: float,
    user_agent: str,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {
        qid: {
            "direct_class_qid": qid,
            "direct_class_uri": f"http://www.wikidata.org/entity/{qid}",
            "direct_class_label": label,
            "ancestors": [],
        }
        for qid, label in direct_class_index.items()
    }

    for batch_qids in chunked(sorted(direct_class_index), batch_size):
        query = build_class_ancestor_query(batch_qids, language=language)
        response = execute_query_with_retry(
            query,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            sleep_seconds=sleep_seconds,
            user_agent=user_agent,
        )
        parsed = parse_ancestor_bindings(response.get("results", {}).get("bindings", []))
        for direct_qid, bucket in parsed.items():
            merged_bucket = merged.setdefault(direct_qid, bucket)
            if bucket.get("direct_class_label"):
                merged_bucket["direct_class_label"] = bucket["direct_class_label"]

            seen = {(item["qid"], item.get("label")) for item in merged_bucket["ancestors"]}
            for ancestor in bucket["ancestors"]:
                key = (ancestor["qid"], ancestor.get("label"))
                if key in seen:
                    continue
                seen.add(key)
                merged_bucket["ancestors"].append(ancestor)

        time.sleep(sleep_seconds)

    rows = []
    for qid, bucket in merged.items():
        bucket["ancestor_count"] = len(bucket["ancestors"])
        bucket["ancestor_labels"] = [item["label"] for item in bucket["ancestors"] if item.get("label")]
        rows.append(bucket)
    return sorted(rows, key=lambda row: ((row.get("direct_class_label") or ""), row["direct_class_qid"]))


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = [row["ancestor_count"] for row in rows]
    return {
        "direct_class_count": len(rows),
        "classes_with_ancestors": sum(1 for count in counts if count > 0),
        "total_ancestor_edges": sum(counts),
        "max_ancestor_count": max(counts) if counts else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch one-hop class ancestors for direct Wikidata classes.")
    parser.add_argument("--input", required=True, help="Input JSONL with direct_class_qids/direct_class_labels fields")
    parser.add_argument("--out", required=True, help="Class ancestor catalog JSONL output path")
    parser.add_argument("--report-out", help="Optional summary JSON output path")
    parser.add_argument("--language", default="it", help="Preferred label language")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    direct_class_index = collect_direct_classes(rows)
    output_rows = fetch_class_ancestors(
        direct_class_index,
        language=args.language,
        batch_size=args.batch_size,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        sleep_seconds=args.sleep_seconds,
        user_agent=args.user_agent,
    )
    write_jsonl(output_rows, Path(args.out))

    if args.report_out:
        Path(args.report_out).write_text(json.dumps(build_report(output_rows), indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(output_rows)} class ancestor rows to {args.out}")
    if args.report_out:
        print(f"Wrote class ancestor report to {args.report_out}")


if __name__ == "__main__":
    main()

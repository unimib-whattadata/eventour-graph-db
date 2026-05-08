"""Build a reusable property catalog from extracted Wikidata entity subgraphs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from eventour_kg.extraction.source_records import write_jsonl
from eventour_kg.extraction.wikidata import (
    build_property_catalog_query,
    qid_from_uri,
    term_from_uri,
)


WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
DEFAULT_BATCH_SIZE = 50
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 4
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_USER_AGENT = "EventourKG/0.1 (research pipeline; property catalog fetcher)"

DROP_PROPERTY_TYPES = {
    "ExternalId",
    "CommonsMedia",
    "Url",
    "GlobeCoordinate",
    "GeoShape",
    "TabularData",
}

UNIVERSAL_EDITORIAL_PROPERTIES = {
    "P373": "commons category",
    "P910": "topic's main category",
    "P935": "commons gallery",
    "P143": "imported from Wikimedia project",
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


def summarize_properties(subgraph_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}

    for row in subgraph_rows:
        item_qid = row.get("item_qid")
        for claim in row.get("claims", []):
            property_qid = claim.get("property_qid")
            if not property_qid:
                continue

            bucket = summary.setdefault(
                property_qid,
                {
                    "property_qid": property_qid,
                    "property_uri": claim.get("property_uri"),
                    "observed_claim_count": 0,
                    "observed_entity_qids": set(),
                    "observed_labels": Counter(),
                    "sample_value_types": Counter(),
                    "sample_datatypes": Counter(),
                },
            )
            bucket["observed_claim_count"] += 1
            if item_qid:
                bucket["observed_entity_qids"].add(item_qid)
            label = claim.get("property_label")
            if label:
                bucket["observed_labels"][label] += 1
            value_type = claim.get("value_type")
            if value_type:
                bucket["sample_value_types"][value_type] += 1
            value_datatype = claim.get("value_datatype")
            if value_datatype:
                bucket["sample_datatypes"][value_datatype] += 1

    return summary


def parse_property_metadata(bindings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        property_uri = _binding_value(binding, "property")
        property_qid = qid_from_uri(property_uri)
        if not property_qid:
            continue
        property_type_uri = _binding_value(binding, "propertyType")
        metadata[property_qid] = {
            "property_label": _binding_value(binding, "propertyLabel"),
            "property_description": _binding_value(binding, "propertyDescription"),
            "property_type_uri": property_type_uri,
            "property_type_name": term_from_uri(property_type_uri),
            "property_type_label": _binding_value(binding, "propertyTypeLabel"),
        }
    return metadata


def fetch_property_metadata(
    property_qids: list[str],
    *,
    language: str,
    batch_size: int,
    timeout_seconds: int,
    max_retries: int,
    sleep_seconds: float,
    user_agent: str,
) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for batch_qids in chunked(property_qids, batch_size):
        query = build_property_catalog_query(batch_qids, language=language)
        response = execute_query_with_retry(
            query,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            sleep_seconds=sleep_seconds,
            user_agent=user_agent,
        )
        bindings = response.get("results", {}).get("bindings", [])
        metadata.update(parse_property_metadata(bindings))
        time.sleep(sleep_seconds)
    return metadata


def classify_property(
    *,
    property_qid: str,
    property_type_name: str | None,
) -> tuple[str, str]:
    if property_type_name in DROP_PROPERTY_TYPES:
        return "drop", f"property type {property_type_name}"
    if property_qid in UNIVERSAL_EDITORIAL_PROPERTIES:
        return "drop", f"editorial property {UNIVERSAL_EDITORIAL_PROPERTIES[property_qid]}"
    return "keep_candidate", "not matched by universal cleanup rules"


def build_catalog_rows(
    property_summary: dict[str, dict[str, Any]],
    *,
    metadata_index: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    metadata_index = metadata_index or {}
    rows: list[dict[str, Any]] = []
    fetched_at = datetime.now(UTC).isoformat()

    for property_qid, summary in property_summary.items():
        metadata = metadata_index.get(property_qid, {})
        observed_labels = summary["observed_labels"]
        observed_label = observed_labels.most_common(1)[0][0] if observed_labels else None
        property_label = metadata.get("property_label") or observed_label
        property_type_name = metadata.get("property_type_name")
        cleanup_action, cleanup_reason = classify_property(
            property_qid=property_qid,
            property_type_name=property_type_name,
        )

        rows.append(
            {
                "property_qid": property_qid,
                "property_uri": summary.get("property_uri"),
                "property_label": property_label,
                "property_description": metadata.get("property_description"),
                "property_type_uri": metadata.get("property_type_uri"),
                "property_type_name": property_type_name,
                "property_type_label": metadata.get("property_type_label"),
                "observed_claim_count": summary["observed_claim_count"],
                "observed_entity_count": len(summary["observed_entity_qids"]),
                "observed_labels": [label for label, _count in observed_labels.most_common(5)],
                "sample_value_types": [value for value, _count in summary["sample_value_types"].most_common(5)],
                "sample_datatypes": [value for value, _count in summary["sample_datatypes"].most_common(5)],
                "cleanup_action": cleanup_action,
                "cleanup_reason": cleanup_reason,
                "catalog_generated_at": fetched_at,
            }
        )

    return sorted(rows, key=lambda row: (-row["observed_claim_count"], row["property_qid"]))


def build_catalog_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    action_counts = Counter(row["cleanup_action"] for row in rows)
    type_counts = Counter(row["property_type_name"] or "UNKNOWN" for row in rows)
    return {
        "property_count": len(rows),
        "cleanup_action_counts": dict(action_counts),
        "property_type_counts": dict(type_counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a property catalog from Wikidata entity subgraphs.")
    parser.add_argument("--input", required=True, help="Entity subgraph JSONL input path")
    parser.add_argument("--out", required=True, help="Property catalog JSONL output path")
    parser.add_argument("--report-out", help="Optional summary JSON output path")
    parser.add_argument("--fetch-metadata", action="store_true", help="Fetch Wikidata property metadata from WDQS")
    parser.add_argument("--language", default="it", help="Preferred label language")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()

    subgraph_rows = load_jsonl(Path(args.input))
    property_summary = summarize_properties(subgraph_rows)

    metadata_index: dict[str, dict[str, Any]] = {}
    if args.fetch_metadata:
        metadata_index = fetch_property_metadata(
            sorted(property_summary),
            language=args.language,
            batch_size=args.batch_size,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
            sleep_seconds=args.sleep_seconds,
            user_agent=args.user_agent,
        )

    catalog_rows = build_catalog_rows(property_summary, metadata_index=metadata_index)
    write_jsonl(catalog_rows, Path(args.out))

    if args.report_out:
        report = build_catalog_report(catalog_rows)
        Path(args.report_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(catalog_rows)} property catalog rows to {args.out}")
    if args.report_out:
        print(f"Wrote property catalog report to {args.report_out}")


if __name__ == "__main__":
    main()

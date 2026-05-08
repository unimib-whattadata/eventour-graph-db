"""Fetch raw 1-hop Wikidata entity subgraphs in small resumable batches."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from eventour_kg.config.loaders import load_city_profile
from eventour_kg.extraction.source_records import write_jsonl
from eventour_kg.extraction.wikidata import build_entity_subgraph_query, qid_from_uri


WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
DEFAULT_BATCH_SIZE = 20
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 4
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_USER_AGENT = "EventourKG/0.1 (research pipeline; entity subgraph fetcher)"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def append_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


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


def parse_subgraph_bindings(bindings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    claims_by_item: dict[str, list[dict[str, Any]]] = {}
    for binding in bindings:
        item_qid = qid_from_uri(_binding_value(binding, "item"))
        if not item_qid:
            continue

        property_uri = _binding_value(binding, "property")
        property_qid = qid_from_uri(property_uri)
        property_label = _binding_value(binding, "propertyLabel")
        value_entity_uri = _binding_value(binding, "valueEntity")
        value_entity_qid = qid_from_uri(value_entity_uri)
        value_entity_label = _binding_value(binding, "valueEntityLabel")
        value_literal = _binding_value(binding, "valueLiteral")
        value_datatype = _binding_value(binding, "valueDatatype")
        value_lang = _binding_value(binding, "valueLang")

        if value_entity_qid:
            value_type = "wikibase-item"
        elif value_literal is not None:
            value_type = "literal"
        else:
            value_type = "unknown"

        claims_by_item.setdefault(item_qid, []).append(
            {
                "property_qid": property_qid,
                "property_uri": property_uri,
                "property_label": property_label,
                "value_type": value_type,
                "value_qid": value_entity_qid,
                "value_uri": value_entity_uri,
                "value_label": value_entity_label,
                "value_literal": value_literal,
                "value_datatype": value_datatype,
                "value_lang": value_lang,
            }
        )
    return claims_by_item


def build_entity_subgraph_rows(
    batch_qids: list[str],
    *,
    entity_index: dict[str, dict[str, Any]],
    claims_by_item: dict[str, list[dict[str, Any]]],
    fetched_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item_qid in batch_qids:
        entity = entity_index[item_qid]
        claims = claims_by_item.get(item_qid, [])
        rows.append(
            {
                "city_id": entity.get("city_id"),
                "source_id": "wikidata",
                "item_qid": item_qid,
                "item_uri": entity.get("item_uri"),
                "preferred_label": entity.get("preferred_label"),
                "description": entity.get("description"),
                "longitude": entity.get("longitude"),
                "latitude": entity.get("latitude"),
                "direct_class_qids": entity.get("direct_class_qids", []),
                "direct_class_labels": entity.get("direct_class_labels", []),
                "claim_count": len(claims),
                "claims": claims,
                "fetched_at": fetched_at,
            }
        )
    return rows


def load_completed_qids(path: Path) -> set[str]:
    completed: set[str] = set()
    for row in load_jsonl(path):
        item_qid = row.get("item_qid")
        if item_qid:
            completed.add(item_qid)
    return completed


def load_next_batch_index(path: Path) -> int:
    next_index = 0
    for row in load_jsonl(path):
        batch_index = row.get("batch_index")
        if isinstance(batch_index, int):
            next_index = max(next_index, batch_index + 1)
    return next_index


def fetch_subgraphs(
    city_id: str,
    *,
    entities_input: Path,
    output_path: Path,
    raw_dir: Path,
    batch_size: int,
    timeout_seconds: int,
    max_retries: int,
    sleep_seconds: float,
    user_agent: str,
) -> None:
    profile = load_city_profile(city_id)
    entities = load_jsonl(entities_input)
    entity_index = {row["item_qid"]: row for row in entities if row.get("item_qid")}
    completed = load_completed_qids(output_path)
    pending_qids = [qid for qid in entity_index if qid not in completed]
    batches = chunked(pending_qids, batch_size)

    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / "manifest.jsonl"
    next_batch_index = load_next_batch_index(manifest_path)

    print(f"city={city_id} total_entities={len(entity_index)} completed={len(completed)} pending={len(pending_qids)}")
    for offset, batch_qids in enumerate(batches):
        batch_index = next_batch_index + offset
        query = build_entity_subgraph_query(batch_qids, language=profile.language_priority[0] if profile.language_priority else "en")
        raw_path = raw_dir / f"batch_{batch_index:04d}.json"
        fetched_at = datetime.now(UTC).isoformat()
        try:
            response = execute_query_with_retry(
                query,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                sleep_seconds=sleep_seconds,
                user_agent=user_agent,
            )
            raw_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
            bindings = response.get("results", {}).get("bindings", [])
            claims_by_item = parse_subgraph_bindings(bindings)
            rows = build_entity_subgraph_rows(
                batch_qids,
                entity_index=entity_index,
                claims_by_item=claims_by_item,
                fetched_at=fetched_at,
            )
            append_jsonl(rows, output_path)
            append_jsonl(
                [
                    {
                        "batch_index": batch_index,
                        "status": "completed",
                        "fetched_at": fetched_at,
                        "qid_count": len(batch_qids),
                        "binding_count": len(bindings),
                        "output_row_count": len(rows),
                        "raw_path": str(raw_path),
                        "qids": batch_qids,
                    }
                ],
                manifest_path,
            )
            print(f"batch={batch_index} qids={len(batch_qids)} bindings={len(bindings)}")
            time.sleep(sleep_seconds)
        except Exception as exc:
            append_jsonl(
                [
                    {
                        "batch_index": batch_index,
                        "status": "failed",
                        "fetched_at": fetched_at,
                        "qid_count": len(batch_qids),
                        "raw_path": str(raw_path),
                        "qids": batch_qids,
                        "error": repr(exc),
                    }
                ],
                manifest_path,
            )
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch raw Wikidata entity subgraphs in resumable batches.")
    parser.add_argument("city_id", help="City profile identifier, e.g. milan")
    parser.add_argument("--entities-input", required=True, help="Aggregated entity JSONL input path")
    parser.add_argument("--out", required=True, help="Entity subgraph JSONL output path")
    parser.add_argument("--raw-dir", required=True, help="Directory for raw batch JSON responses and manifest")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()

    fetch_subgraphs(
        args.city_id,
        entities_input=Path(args.entities_input),
        output_path=Path(args.out),
        raw_dir=Path(args.raw_dir),
        batch_size=args.batch_size,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        sleep_seconds=args.sleep_seconds,
        user_agent=args.user_agent,
    )


if __name__ == "__main__":
    main()

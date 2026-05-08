"""Build deterministic Wikidata curation artifacts for one city."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from eventour_kg.curation.adjudication import (
    build_adjudication_rows,
    load_annotation_package_master,
    load_merged_annotation_rows,
    write_adjudication_csv,
)
from eventour_kg.curation.apply_policy import (
    apply_curation_to_records,
    load_adjudication_by_qid,
    load_city_overrides_by_qid,
    load_classification_jsonl,
)
from eventour_kg.curation.semantic_policy import GROUP_RULES, PRIORITY_ORDER


IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
ANNOTATION_PACKAGE_DIRNAME = "annotation_package_v1"
CITY_OVERRIDE_FIELDNAMES = (
    "item_qid",
    "preferred_label",
    "override_final_label",
    "override_final_category",
    "override_reason",
    "source",
    "notes",
)
SEMANTIC_POLICY_FIELDNAMES = (
    "policy_group",
    "group_description",
    "match_strategy",
    "priority_rank",
    "default_final_label",
    "default_final_category",
    "label_cap",
    "confidence_level",
    "match_signals",
    "preferred_label_signals",
    "description_signals",
    "direct_class_label_signals",
    "class_ancestor_label_signals",
    "semantic_fact_text_signals",
    "evidence_sample_ids",
    "evidence_item_qids",
    "recurring_direct_classes",
    "notes",
    "exception_handling",
)
_ADJUDICATION_PRESERVED_FIELDS = (
    "adjudicated_final_label",
    "adjudicated_final_category",
    "adjudication_notes",
)
_POLICY_SIGNAL_TARGETS = (
    "preferred_label",
    "description",
    "direct_class_labels",
    "class_ancestor_labels",
    "semantic_fact_texts",
)
_GROUP_DESCRIPTIONS = {
    "religious_sites": "Religious buildings and worship-oriented destination entities.",
    "historic_buildings_palazzi": "Historic buildings, palazzi, villas, and closely related heritage structures.",
    "cinemas_theatres_performance": "Performance-oriented cultural venues such as cinemas, theatres, auditoria, and opera spaces.",
    "named_urban_landmarks": "Named landmark-like urban reference entities such as monuments, arches, towers, and memorials.",
    "libraries_archives": "Libraries, archives, mediatheques, and closely related documentary cultural repositories.",
    "institutional_education": "Educational and institutional entities retained primarily as contextual urban knowledge.",
    "branded_venues": "Brand-led commercial venues and retail-oriented entities to exclude by default.",
    "hotels_lodging": "Hotels and lodging/accommodation entities to exclude by default.",
}


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _city_defaults(city_id: str) -> dict[str, Path]:
    city_root = IMPLEMENTATION_ROOT / "data" / "cities" / city_id
    evaluation_dir = city_root / "evaluation" / ANNOTATION_PACKAGE_DIRNAME
    final_dir = city_root / "final" / "wikidata_decisions"
    return {
        "annotations_workbook": evaluation_dir / "annotations_all.xlsx",
        "annotation_master_json": evaluation_dir / "annotation_package_master.json",
        "classification_input": city_root / "intermediate" / "wikidata_entity_classification_openai_full.jsonl",
        "adjudication_csv": evaluation_dir / "wikidata_annotation_adjudication.csv",
        "semantic_policy_csv": evaluation_dir / "wikidata_semantic_policy.csv",
        "city_overrides_csv": evaluation_dir / "wikidata_city_overrides.csv",
        "curated_final_jsonl": final_dir / "wikidata_curated_final.jsonl",
        "summary_json": final_dir / "wikidata_curated_summary.json",
    }


def _load_existing_rows_by_key(path: Path, *, key_field: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            key = _normalize_text(row.get(key_field))
            if key is None:
                continue
            rows[key] = dict(row)
    return rows


def _merge_adjudication_rows(
    built_rows: list[dict[str, object]],
    *,
    existing_by_sample_id: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    merged_rows: list[dict[str, object]] = []
    for row in built_rows:
        sample_id = _normalize_text(row.get("sample_id"))
        existing_row = existing_by_sample_id.get(sample_id or "")
        if not existing_row:
            merged_rows.append(row)
            continue
        merged_row = dict(row)
        for field in _ADJUDICATION_PRESERVED_FIELDS:
            existing_value = _normalize_text(existing_row.get(field))
            if existing_value is not None:
                merged_row[field] = existing_value
        merged_rows.append(merged_row)
    return merged_rows


def _policy_signal_blob(keywords: tuple[str, ...]) -> str:
    keyword_text = " | ".join(keywords)
    signal_targets = ",".join(_POLICY_SIGNAL_TARGETS)
    return f"keywords={keyword_text}; applies_to={signal_targets}"


def build_semantic_policy_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for priority_rank, group in enumerate(PRIORITY_ORDER, start=1):
        rule = GROUP_RULES[group]
        signal_blob = _policy_signal_blob(rule["keywords"])
        rows.append(
            {
                "policy_group": group,
                "group_description": _GROUP_DESCRIPTIONS[group],
                "match_strategy": "boundary_matched_keyword_bundle",
                "priority_rank": str(priority_rank),
                "default_final_label": str(rule["default_label"]),
                "default_final_category": "",
                "label_cap": str(rule["label_cap"]),
                "confidence_level": "v1_strict",
                "match_signals": signal_blob,
                "preferred_label_signals": signal_blob,
                "description_signals": signal_blob,
                "direct_class_label_signals": signal_blob,
                "class_ancestor_label_signals": signal_blob,
                "semantic_fact_text_signals": signal_blob,
                "evidence_sample_ids": "",
                "evidence_item_qids": "",
                "recurring_direct_classes": "",
                "notes": "",
                "exception_handling": "",
            }
        )
    return rows


def write_semantic_policy_csv(path: Path) -> list[dict[str, str]]:
    rows = build_semantic_policy_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEMANTIC_POLICY_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in SEMANTIC_POLICY_FIELDNAMES})
    return rows


def ensure_city_overrides_csv(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CITY_OVERRIDE_FIELDNAMES)
        writer.writeheader()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def build_wikidata_curation(
    *,
    city_id: str,
    annotations_workbook: Path,
    annotation_master_json: Path,
    classification_input: Path,
    adjudication_csv: Path,
    semantic_policy_csv: Path,
    city_overrides_csv: Path,
    curated_final_jsonl: Path,
    summary_json: Path,
) -> dict[str, Any]:
    annotations = load_merged_annotation_rows(annotations_workbook)
    master_by_sample_id = load_annotation_package_master(annotation_master_json)
    built_adjudication_rows = build_adjudication_rows(annotations, master_by_sample_id=master_by_sample_id)
    existing_adjudication = _load_existing_rows_by_key(adjudication_csv, key_field="sample_id")
    adjudication_rows = _merge_adjudication_rows(
        built_adjudication_rows,
        existing_by_sample_id=existing_adjudication,
    )
    write_adjudication_csv(adjudication_rows, adjudication_csv)

    semantic_policy_rows = write_semantic_policy_csv(semantic_policy_csv)

    ensure_city_overrides_csv(city_overrides_csv)

    classification_rows = load_classification_jsonl(classification_input)
    adjudication_by_qid = load_adjudication_by_qid(adjudication_csv)
    city_overrides_by_qid = load_city_overrides_by_qid(city_overrides_csv)
    curated_rows = apply_curation_to_records(
        classification_rows,
        adjudication_by_qid=adjudication_by_qid,
        city_overrides_by_qid=city_overrides_by_qid,
    )
    _write_jsonl(curated_final_jsonl, curated_rows)

    final_label_counts = Counter(
        label for label in (_normalize_text(row.get("final_label")) for row in curated_rows) if label is not None
    )
    curation_source_counts = Counter(
        source for source in (_normalize_text(row.get("curation_source")) for row in curated_rows) if source is not None
    )
    policy_group_counts = Counter(
        group for group in (_normalize_text(row.get("policy_group")) for row in curated_rows) if group is not None
    )
    summary = {
        "city_id": city_id,
        "record_count": len(curated_rows),
        "adjudication_row_count": len(adjudication_rows),
        "semantic_policy_row_count": len(semantic_policy_rows),
        "city_override_row_count": len(city_overrides_by_qid),
        "final_label_counts": _counter_dict(final_label_counts),
        "curation_source_counts": _counter_dict(curation_source_counts),
        "policy_group_counts": _counter_dict(policy_group_counts),
        "paths": {
            "annotations_workbook": str(annotations_workbook),
            "annotation_master_json": str(annotation_master_json),
            "classification_input": str(classification_input),
            "adjudication_csv": str(adjudication_csv),
            "semantic_policy_csv": str(semantic_policy_csv),
            "city_overrides_csv": str(city_overrides_csv),
            "curated_final_jsonl": str(curated_final_jsonl),
            "summary_json": str(summary_json),
        },
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build deterministic Wikidata curation outputs for one city.")
    parser.add_argument("--city-id", required=True, help="City identifier, for example: milan")
    parser.add_argument("--annotations-workbook", help="Annotation workbook (.xlsx)")
    parser.add_argument("--annotation-master-json", help="Annotation package master JSON")
    parser.add_argument("--classification-input", help="Full classification JSONL input")
    parser.add_argument("--adjudication-csv", help="Adjudication CSV output path")
    parser.add_argument("--semantic-policy-csv", help="Semantic policy CSV output path")
    parser.add_argument("--city-overrides-csv", help="City override CSV path")
    parser.add_argument("--curated-final-jsonl", help="Curated final JSONL output path")
    parser.add_argument("--summary-json", help="Curation summary JSON output path")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    defaults = _city_defaults(args.city_id)
    summary = build_wikidata_curation(
        city_id=args.city_id,
        annotations_workbook=Path(args.annotations_workbook) if args.annotations_workbook else defaults["annotations_workbook"],
        annotation_master_json=Path(args.annotation_master_json)
        if args.annotation_master_json
        else defaults["annotation_master_json"],
        classification_input=Path(args.classification_input) if args.classification_input else defaults["classification_input"],
        adjudication_csv=Path(args.adjudication_csv) if args.adjudication_csv else defaults["adjudication_csv"],
        semantic_policy_csv=Path(args.semantic_policy_csv)
        if args.semantic_policy_csv
        else defaults["semantic_policy_csv"],
        city_overrides_csv=Path(args.city_overrides_csv) if args.city_overrides_csv else defaults["city_overrides_csv"],
        curated_final_jsonl=Path(args.curated_final_jsonl) if args.curated_final_jsonl else defaults["curated_final_jsonl"],
        summary_json=Path(args.summary_json) if args.summary_json else defaults["summary_json"],
    )
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

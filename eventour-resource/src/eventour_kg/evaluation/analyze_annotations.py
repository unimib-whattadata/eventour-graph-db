"""Analyze human annotation agreement and compare provisional human labels with LLM outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DECISION_LABELS = ("keep_poi", "keep_context", "exclude")
ANNOTATORS = ("serena", "blerina", "fabio")
ANNOTATOR_COLUMNS = {
    "serena": {"decision": "H", "category": "I", "notes": "J"},
    "blerina": {"decision": "K", "category": "L", "notes": "M"},
    "fabio": {"decision": "N", "category": "O", "notes": None},
}


def _normalize(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_xlsx_rows(path: Path) -> list[dict[str, str]]:
    with ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared_strings.append("".join(node.text or "" for node in si.iterfind(".//m:t", NS)))

        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows: list[dict[str, str]] = []
        for row in sheet.find("m:sheetData", NS).findall("m:row", NS):
            row_values: dict[str, str] = {}
            for cell in row.findall("m:c", NS):
                column = "".join(ch for ch in cell.attrib["r"] if ch.isalpha())
                raw_type = cell.attrib.get("t")
                value_node = cell.find("m:v", NS)
                if value_node is None:
                    row_values[column] = ""
                    continue
                raw_value = value_node.text or ""
                row_values[column] = shared_strings[int(raw_value)] if raw_type == "s" else raw_value
            rows.append(row_values)
        return rows


def load_annotation_records(path: Path) -> list[dict[str, str | None]]:
    records: list[dict[str, str | None]] = []
    for row in load_xlsx_rows(path)[2:]:
        record = {
            "sample_id": _normalize(row.get("A")),
            "item_qid": _normalize(row.get("B")),
            "preferred_label": _normalize(row.get("C")),
        }
        for annotator in ANNOTATORS:
            mapping = ANNOTATOR_COLUMNS[annotator]
            record[f"{annotator}_decision"] = _normalize(row.get(mapping["decision"]))
            record[f"{annotator}_category"] = _normalize(row.get(mapping["category"]))
            note_column = mapping["notes"]
            record[f"{annotator}_notes"] = _normalize(row.get(note_column)) if note_column else None
        records.append(record)
    return records


def majority_vote(values: list[str | None]) -> tuple[str | None, bool]:
    observed = [value for value in values if value is not None]
    counts = Counter(observed)
    if not counts:
        return None, True
    ranked = counts.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None, True
    return ranked[0][0], False


def cohen_kappa(left: list[str], right: list[str], labels: tuple[str, ...]) -> float:
    total = len(left)
    if total == 0:
        return 0.0
    observed = sum(1 for lval, rval in zip(left, right) if lval == rval) / total
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum((left_counts[label] / total) * (right_counts[label] / total) for label in labels)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def fleiss_kappa(rating_rows: list[Counter[str]], labels: tuple[str, ...]) -> float:
    n_items = len(rating_rows)
    if n_items == 0:
        return 0.0
    n_raters = sum(rating_rows[0].values())
    p = {
        label: sum(row.get(label, 0) for row in rating_rows) / (n_items * n_raters)
        for label in labels
    }
    per_item = [
        (sum(count * count for count in row.values()) - n_raters) / (n_raters * (n_raters - 1))
        for row in rating_rows
    ]
    observed = sum(per_item) / n_items
    expected = sum(probability * probability for probability in p.values())
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def build_row_level_comparison(
    records: list[dict[str, str | None]],
    master_by_sample_id: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        sample_id = record["sample_id"]
        master = master_by_sample_id[sample_id]
        decisions = [record[f"{annotator}_decision"] for annotator in ANNOTATORS]
        counts = Counter(decisions)
        decision_majority, decision_tie = majority_vote(decisions)
        unanimous_decision = len(counts) == 1
        all_different = len(counts) == 3

        keep_poi_categories = [
            record[f"{annotator}_category"]
            for annotator in ANNOTATORS
            if record[f"{annotator}_decision"] == "keep_poi"
        ]
        category_majority, category_tie = majority_vote(keep_poi_categories)

        rows.append(
            {
                "sample_id": sample_id,
                "item_qid": record["item_qid"],
                "preferred_label": record["preferred_label"],
                "serena_decision": record["serena_decision"],
                "blerina_decision": record["blerina_decision"],
                "fabio_decision": record["fabio_decision"],
                "serena_category": record["serena_category"],
                "blerina_category": record["blerina_category"],
                "fabio_category": record["fabio_category"],
                "human_decision_unanimous": unanimous_decision,
                "human_decision_all_different": all_different,
                "human_decision_majority": decision_majority,
                "human_decision_tie": decision_tie,
                "human_keep_poi_category_majority": category_majority,
                "human_keep_poi_category_tie": category_tie,
                "llm_decision": master["llm_decision"],
                "llm_eventour_category": master["llm_eventour_category"],
                "llm_confidence": master["llm_confidence"],
                "llm_needs_review": master["llm_needs_review"],
                "llm_matches_majority_decision": (
                    decision_majority is not None and master["llm_decision"] == decision_majority
                ),
                "llm_matches_majority_keep_poi_category": (
                    decision_majority == "keep_poi"
                    and category_majority is not None
                    and master["llm_eventour_category"] == category_majority
                ),
            }
        )
    return rows


def summarize(
    records: list[dict[str, str | None]],
    master_by_sample_id: dict[str, dict[str, object]],
) -> dict[str, object]:
    pairwise = {}
    pairs = (("serena", "blerina"), ("serena", "fabio"), ("blerina", "fabio"))
    for left_name, right_name in pairs:
        valid = [
            (record[f"{left_name}_decision"], record[f"{right_name}_decision"])
            for record in records
            if record[f"{left_name}_decision"] is not None and record[f"{right_name}_decision"] is not None
        ]
        left = [item[0] for item in valid]
        right = [item[1] for item in valid]
        pairwise[f"{left_name}_{right_name}"] = {
            "n": len(valid),
            "percent_agreement": round(sum(1 for lval, rval in valid if lval == rval) / len(valid) * 100, 2),
            "cohen_kappa": round(cohen_kappa(left, right, DECISION_LABELS), 4),
        }

    rating_rows: list[Counter[str]] = []
    unanimous_decision = 0
    all_different = 0
    majority_distribution: Counter[str] = Counter()
    review_counts: Counter[tuple[str, bool]] = Counter()
    decision_confusion: Counter[tuple[str, str]] = Counter()

    llm_correct_majority = 0
    llm_total_majority = 0
    llm_correct_unanimous = 0
    llm_total_unanimous = 0

    category_pairwise = {f"{left}_{right}": {"n": 0, "agree": 0} for left, right in pairs}
    all_three_keep_poi = 0
    unanimous_category_all_keep_poi = 0
    llm_category_total_majority = 0
    llm_category_correct_majority = 0
    llm_category_total_unanimous = 0
    llm_category_correct_unanimous = 0

    llm_distribution: Counter[str] = Counter()
    llm_non_exception_total = 0
    llm_non_exception_correct = 0
    llm_confidence_by_majority: defaultdict[str, list[float]] = defaultdict(list)

    for record in records:
        sample_id = record["sample_id"]
        master = master_by_sample_id[sample_id]
        decisions = [record[f"{annotator}_decision"] for annotator in ANNOTATORS]
        decision_counts = Counter(decisions)
        rating_rows.append(Counter(decisions))
        if len(decision_counts) == 1:
            unanimous_decision += 1
        if len(decision_counts) == 3:
            all_different += 1

        decision_majority, _ = majority_vote(decisions)
        if decision_majority is not None:
            majority_distribution[decision_majority] += 1
            llm_total_majority += 1
            llm_distribution[str(master["llm_decision"])] += 1
            decision_confusion[(decision_majority, str(master["llm_decision"]))] += 1
            llm_confidence_by_majority[decision_majority].append(float(master["llm_confidence"]))
            if master["llm_decision"] == decision_majority:
                llm_correct_majority += 1
            if len(decision_counts) == 1:
                llm_total_unanimous += 1
                if master["llm_decision"] == decision_majority:
                    llm_correct_unanimous += 1
            if master["llm_decision"] != "candidate_exception":
                llm_non_exception_total += 1
                if master["llm_decision"] == decision_majority:
                    llm_non_exception_correct += 1
            review_counts[("unanimous" if len(decision_counts) == 1 else "disagreement", bool(master["llm_needs_review"]))] += 1

        decision_by_annotator = {annotator: record[f"{annotator}_decision"] for annotator in ANNOTATORS}
        category_by_annotator = {annotator: record[f"{annotator}_category"] for annotator in ANNOTATORS}
        for left_name, right_name in pairs:
            if (
                decision_by_annotator[left_name] == "keep_poi"
                and decision_by_annotator[right_name] == "keep_poi"
            ):
                entry = category_pairwise[f"{left_name}_{right_name}"]
                entry["n"] += 1
                if (
                    category_by_annotator[left_name] is not None
                    and category_by_annotator[left_name] == category_by_annotator[right_name]
                ):
                    entry["agree"] += 1

        if all(decision == "keep_poi" for decision in decisions):
            all_three_keep_poi += 1
            categories = [category_by_annotator[annotator] for annotator in ANNOTATORS]
            if len(set(categories)) == 1 and categories[0] is not None:
                unanimous_category_all_keep_poi += 1
                llm_category_total_unanimous += 1
                if master["llm_eventour_category"] == categories[0]:
                    llm_category_correct_unanimous += 1

        if decision_majority == "keep_poi":
            keep_poi_categories = [
                category_by_annotator[annotator]
                for annotator in ANNOTATORS
                if decision_by_annotator[annotator] == "keep_poi"
            ]
            category_majority, _ = majority_vote(keep_poi_categories)
            if category_majority is not None:
                llm_category_total_majority += 1
                if master["llm_eventour_category"] == category_majority:
                    llm_category_correct_majority += 1

    unanimous_count = unanimous_decision
    disagreement_count = len(records) - unanimous_count
    flagged_unanimous = review_counts[("unanimous", True)]
    flagged_disagreement = review_counts[("disagreement", True)]

    return {
        "n_items": len(records),
        "human_decision_agreement": {
            "pairwise": pairwise,
            "fleiss_kappa": round(fleiss_kappa(rating_rows, DECISION_LABELS), 4),
            "unanimous_rate": round(unanimous_decision / len(records) * 100, 2),
            "majority_resolved_rate": round(sum(majority_distribution.values()) / len(records) * 100, 2),
            "all_different_rate": round(all_different / len(records) * 100, 2),
            "majority_label_distribution": dict(majority_distribution),
        },
        "human_category_agreement_keep_poi_only": {
            "pairwise_when_both_keep_poi": {
                key: {
                    "n": value["n"],
                    "percent_agreement": round(value["agree"] / value["n"] * 100, 2) if value["n"] else None,
                }
                for key, value in category_pairwise.items()
            },
            "all_three_keep_poi_count": all_three_keep_poi,
            "all_three_keep_poi_unanimous_category_rate": (
                round(unanimous_category_all_keep_poi / all_three_keep_poi * 100, 2)
                if all_three_keep_poi
                else None
            ),
        },
        "llm_vs_provisional_human": {
            "decision_accuracy_vs_majority": round(llm_correct_majority / llm_total_majority * 100, 2),
            "decision_accuracy_vs_unanimous_subset": round(llm_correct_unanimous / llm_total_unanimous * 100, 2),
            "decision_eval_majority_n": llm_total_majority,
            "decision_eval_unanimous_n": llm_total_unanimous,
            "category_accuracy_vs_majority_keep_poi": (
                round(llm_category_correct_majority / llm_category_total_majority * 100, 2)
                if llm_category_total_majority
                else None
            ),
            "category_accuracy_vs_unanimous_keep_poi": (
                round(llm_category_correct_unanimous / llm_category_total_unanimous * 100, 2)
                if llm_category_total_unanimous
                else None
            ),
            "category_eval_majority_keep_poi_n": llm_category_total_majority,
            "category_eval_unanimous_keep_poi_n": llm_category_total_unanimous,
            "decision_confusion_majority_vs_llm": {
                f"{human}__{llm}": count for (human, llm), count in decision_confusion.items()
            },
        },
        "llm_review_signal": {
            "flagged_review_among_unanimous": (
                round(flagged_unanimous / unanimous_count * 100, 2) if unanimous_count else None
            ),
            "flagged_review_among_disagreement": (
                round(flagged_disagreement / disagreement_count * 100, 2) if disagreement_count else None
            ),
            "counts": {f"{group}__{flag}": count for (group, flag), count in review_counts.items()},
        },
        "llm_routing_view": {
            "llm_decision_distribution_on_majority_resolved_items": dict(llm_distribution),
            "llm_non_candidate_exception_accuracy_on_items_it_classified": (
                round(llm_non_exception_correct / llm_non_exception_total * 100, 2)
                if llm_non_exception_total
                else None
            ),
            "llm_non_candidate_exception_n": llm_non_exception_total,
            "llm_needs_review_rate_by_majority_label": {
                label: (
                    round(
                        review_counts[("unanimous", True)] / unanimous_count * 100,
                        2,
                    )
                    if False
                    else None
                )
                for label in ()
            },
            "llm_mean_confidence_by_majority_label": {
                label: round(sum(values) / len(values), 3) for label, values in llm_confidence_by_majority.items()
            },
        },
        "method_note": {
            "human_gold_status": "not_adjudicated",
            "comparison_target": "provisional human aggregate based on majority vote; unanimous subset reported separately",
            "important_caveat": "The LLM includes candidate_exception as a review-routing label, while human annotators used only keep_poi, keep_context, and exclude as final labels.",
        },
    }


def patch_routing_rates(summary: dict[str, object], records: list[dict[str, str | None]], master_by_sample_id: dict[str, dict[str, object]]) -> None:
    counts = Counter()
    for record in records:
        majority_label, tie = majority_vote([record[f"{annotator}_decision"] for annotator in ANNOTATORS])
        if majority_label is None:
            continue
        counts[(majority_label, bool(master_by_sample_id[record["sample_id"]]["llm_needs_review"]))] += 1
    summary["llm_routing_view"]["llm_needs_review_rate_by_majority_label"] = {
        label: round(counts[(label, True)] / (counts[(label, True)] + counts[(label, False)]) * 100, 2)
        for label in DECISION_LABELS
        if counts[(label, True)] + counts[(label, False)] > 0
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze annotation agreement and compare it with LLM outputs.")
    parser.add_argument("--annotations-xlsx", required=True, help="Merged annotations workbook")
    parser.add_argument("--master-json", required=True, help="Master annotation package JSON")
    parser.add_argument("--summary-json", required=True, help="Output JSON summary path")
    parser.add_argument("--row-level-csv", required=True, help="Output row-level comparison CSV path")
    args = parser.parse_args()

    annotations_path = Path(args.annotations_xlsx)
    master_path = Path(args.master_json)
    summary_path = Path(args.summary_json)
    row_level_path = Path(args.row_level_csv)

    records = load_annotation_records(annotations_path)
    master_payload = json.loads(master_path.read_text(encoding="utf-8"))
    master_by_sample_id = {item["sample_id"]: item for item in master_payload["items"]}

    summary = summarize(records, master_by_sample_id)
    patch_routing_rates(summary, records, master_by_sample_id)
    row_level_rows = build_row_level_comparison(records, master_by_sample_id)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(row_level_path, row_level_rows)
    print(json.dumps({"summary_json": str(summary_path), "row_level_csv": str(row_level_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

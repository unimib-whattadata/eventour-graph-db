"""Prepare a blinded annotation package from merged Eventour classification outputs."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_KEEP_POI_SAMPLE = 100
DEFAULT_KEEP_CONTEXT_SAMPLE = 60
DEFAULT_EXCLUDE_SAMPLE = 80
DEFAULT_SEED = 20260408

HARD_KEYWORD_GROUPS = {
    "building_house_palazzo": [
        "building",
        "edificio",
        "house",
        "casa",
        "palazzo",
    ],
    "libraries_archives": [
        "library",
        "biblioteca",
        "archive",
        "archivio",
    ],
    "branded_venues": [
        "brand",
        "branded",
        "retail",
        "shopping",
        "store",
        "mall",
        "commerciale",
        "shop",
        "boutique",
        "hotel",
        "albergo",
        "cinema",
    ],
    "events": [
        "event",
        "evento",
        "championship",
        "championships",
        "games",
        "olympics",
        "deaflympics",
        "competition",
        "regatta",
        "season",
        "stagione",
        "campionato",
    ],
    "schools_institutions": [
        "school",
        "scuola",
        "academy",
        "accademia",
        "university",
        "universita",
        "college",
        "istituto",
        "institution",
        "dipartimento",
        "department",
    ],
}

DECISION_DEFINITIONS = {
    "keep_poi": "The entity is a candidate Eventour stop: a culturally meaningful, visitable, or narratively useful place.",
    "keep_context": "The entity is useful as spatial or narrative context, but not as a primary itinerary stop.",
    "candidate_exception": "The entity is ambiguous or generic and needs human review before inclusion or exclusion.",
    "exclude": "The entity is not useful for Eventour as a POI or as contextual urban information.",
}

HUMAN_DECISION_DEFINITIONS = {
    "keep_poi": "The entity should be kept as a candidate Eventour stop.",
    "keep_context": "The entity should be kept only as contextual urban information.",
    "exclude": "The entity should be excluded from Eventour.",
}

EVENTOUR_CATEGORY_DEFINITIONS = {
    "museum_collection": "Museum, collection, or exhibition-oriented cultural venue.",
    "gallery_art_space": "Gallery, art space, or venue centered on visual arts display.",
    "religious_heritage": "Church, chapel, monastery, cemetery, or other religious heritage site.",
    "historic_architecture": "Historically or architecturally significant building, palace, house, or complex.",
    "monument_memorial": "Monument, memorial, commemorative site, or war remembrance structure.",
    "public_art": "Artwork, mural, sculpture, or artistic installation in public or semi-public space.",
    "archaeological_ancient_site": "Archaeological remains, ancient ruins, or historically ancient site.",
    "urban_landmark": "Distinctive landmark or city reference point with strong orientation or identity value.",
    "performing_arts_entertainment": "Theatre, opera house, cinema, music venue, or performing arts attraction.",
    "park_garden_nature": "Park, garden, natural area, or outdoor green attraction.",
    "cemetery_funerary_heritage": "Cemetery or funerary heritage site with cultural or historical significance.",
    "science_education_attraction": "Public-facing science, education, or discovery-oriented attraction.",
    "district_streetscape": "District, streetscape, square, or urban ensemble notable as a place experience.",
    "special_interest_attraction": "Other specialized attraction that is meaningful but does not fit the main categories cleanly.",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def join_labels(items: list[dict[str, Any]], *, key: str = "label") -> str:
    labels = []
    for item in items:
        value = item.get(key)
        if value:
            labels.append(str(value))
    return " | ".join(labels)


def join_semantic_facts(items: list[dict[str, Any]]) -> str:
    facts = []
    for item in items:
        value = item.get("prompt_text")
        if value:
            facts.append(str(value))
    return " | ".join(facts)


def normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def hard_flags(row: dict[str, Any]) -> list[str]:
    haystacks = [
        normalize_text(row.get("preferred_label")),
        normalize_text(row.get("description")),
        join_labels(row.get("direct_classes", [])).lower(),
        join_labels(row.get("class_ancestors", [])).lower(),
        join_semantic_facts(row.get("semantic_facts", [])).lower(),
    ]
    combined = " || ".join(haystacks)
    matches: list[str] = []
    for group, keywords in HARD_KEYWORD_GROUPS.items():
        if any(keyword in combined for keyword in keywords):
            matches.append(group)
    return matches


def annotator_row(row: dict[str, Any], *, sample_id: str) -> dict[str, Any]:
    direct_class_labels = row.get("direct_class_labels")
    if isinstance(direct_class_labels, list):
        direct_class_value = " | ".join(str(value) for value in direct_class_labels if value)
    else:
        direct_class_value = join_labels(row.get("direct_classes", []))

    class_ancestor_labels = row.get("class_ancestor_labels")
    if isinstance(class_ancestor_labels, list):
        class_ancestor_value = " | ".join(str(value) for value in class_ancestor_labels if value)
    else:
        class_ancestor_value = join_labels(row.get("class_ancestors", []))

    semantic_fact_texts = row.get("semantic_fact_texts")
    if isinstance(semantic_fact_texts, list):
        semantic_fact_value = " | ".join(str(value) for value in semantic_fact_texts if value)
    else:
        semantic_fact_value = join_semantic_facts(row.get("semantic_facts", []))

    return {
        "sample_id": sample_id,
        "item_qid": row.get("item_qid"),
        "preferred_label": row.get("preferred_label"),
        "description": row.get("description"),
        "direct_class_labels": direct_class_value,
        "class_ancestor_labels": class_ancestor_value,
        "semantic_fact_texts": semantic_fact_value,
        "annotator_final_decision": "",
        "annotator_eventour_category": "",
        "annotator_is_ambiguous": "",
        "annotator_notes": "",
    }


def master_row(
    row: dict[str, Any],
    *,
    sample_id: str,
    sample_bucket: str,
    sample_reasons: list[str],
    hard_groups: list[str],
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "sample_bucket": sample_bucket,
        "sample_reasons": sample_reasons,
        "hard_groups": hard_groups,
        "item_qid": row.get("item_qid"),
        "preferred_label": row.get("preferred_label"),
        "description": row.get("description"),
        "direct_class_labels": [item.get("label") for item in row.get("direct_classes", []) if item.get("label")],
        "class_ancestor_labels": [item.get("label") for item in row.get("class_ancestors", []) if item.get("label")],
        "semantic_fact_texts": [item.get("prompt_text") for item in row.get("semantic_facts", []) if item.get("prompt_text")],
        "llm_decision": row.get("decision"),
        "llm_eventour_category": row.get("eventour_category"),
        "llm_confidence": row.get("confidence"),
        "llm_needs_review": row.get("needs_review"),
    }


def select_ranked_subset(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    rng: random.Random,
) -> list[tuple[dict[str, Any], list[str], list[str]]]:
    ranked: list[tuple[tuple[Any, ...], float, dict[str, Any], list[str], list[str]]] = []
    for row in rows:
        flags = hard_flags(row)
        reasons: list[str] = []
        if flags:
            reasons.append("hard_class")
        confidence = float(row.get("confidence", 0.0))
        if confidence <= 0.8:
            reasons.append("low_confidence")
        if row.get("needs_review"):
            reasons.append("needs_review")
        sort_key = (
            0 if flags else 1,
            0 if row.get("needs_review") else 1,
            confidence,
            rng.random(),
        )
        ranked.append((sort_key, confidence, row, reasons, flags))
    ranked.sort(key=lambda item: item[0])
    selected = [(row, reasons, flags) for _, _, row, reasons, flags in ranked[:limit]]
    return selected


def build_sample(
    rows: list[dict[str, Any]],
    *,
    keep_poi_limit: int,
    keep_context_limit: int,
    exclude_limit: int,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    seen_qids: set[str] = set()
    audit: dict[str, Any] = {
        "seed": seed,
        "decision_targets": {
            "candidate_exception": "all",
            "keep_poi": keep_poi_limit,
            "keep_context": keep_context_limit,
            "exclude": exclude_limit,
        },
        "selected_counts": {},
        "hard_group_counts": Counter(),
    }

    def add_row(row: dict[str, Any], *, sample_bucket: str, reasons: list[str], flags: list[str]) -> None:
        item_qid = row.get("item_qid")
        if not item_qid or item_qid in seen_qids:
            return
        seen_qids.add(item_qid)
        sample_id = f"ann_{len(selected) + 1:04d}"
        selected.append(master_row(row, sample_id=sample_id, sample_bucket=sample_bucket, sample_reasons=reasons, hard_groups=flags))
        for flag in flags:
            audit["hard_group_counts"][flag] += 1

    by_decision: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_decision.setdefault(str(row.get("decision")), []).append(row)

    for row in by_decision.get("candidate_exception", []):
        flags = hard_flags(row)
        reasons = ["all_candidate_exception"]
        if flags:
            reasons.append("hard_class")
        if float(row.get("confidence", 0.0)) <= 0.8:
            reasons.append("low_confidence")
        if row.get("needs_review"):
            reasons.append("needs_review")
        add_row(row, sample_bucket="candidate_exception", reasons=reasons, flags=flags)

    targets = {
        "keep_poi": keep_poi_limit,
        "keep_context": keep_context_limit,
        "exclude": exclude_limit,
    }
    for decision, limit in targets.items():
        subset = select_ranked_subset(by_decision.get(decision, []), limit=limit, rng=rng)
        for row, reasons, flags in subset:
            add_row(row, sample_bucket=decision, reasons=reasons or ["balanced_slice"], flags=flags)

    audit["selected_counts"] = dict(Counter(item["sample_bucket"] for item in selected))
    audit["hard_group_counts"] = dict(audit["hard_group_counts"])
    return selected, audit


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "sample_id",
        "item_qid",
        "preferred_label",
        "description",
        "direct_class_labels",
        "class_ancestor_labels",
        "semantic_fact_texts",
        "annotator_final_decision",
        "annotator_eventour_category",
        "annotator_is_ambiguous",
        "annotator_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_instruction_markdown(sample_size: int, audit: dict[str, Any]) -> str:
    lines = [
        "# Annotation Instructions",
        "",
        "This package supports manual evaluation of the Eventour semantic classification layer.",
        "",
        "## What each annotator should do",
        "",
        "- Label each sampled entity independently using one final decision: `keep_poi`, `keep_context`, or `exclude`.",
        "- If you choose `keep_poi`, also assign exactly one Eventour category.",
        "- Use only the evidence fields shown in the CSV: label, description, direct classes, class ancestors, and semantic facts.",
        "- Do not use the LLM prediction during annotation. The annotator files are intentionally blinded.",
        "- Use `annotator_is_ambiguous` only as a secondary flag when the case is genuinely borderline for a human reviewer.",
        "",
        "## Human decision definitions",
        "",
    ]
    for key, value in HUMAN_DECISION_DEFINITIONS.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Model-only review label",
            "",
            "- `candidate_exception` is kept only in the master package as the LLM's review-routing output.",
            "- Annotators should not use `candidate_exception` as a final gold label.",
        ]
    )
    lines.extend(["", "## Eventour category definitions", ""])
    for key, value in EVENTOUR_CATEGORY_DEFINITIONS.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Sample design",
            "",
            f"- Total sampled entities: `{sample_size}`",
            f"- Candidate exceptions included in full: `{audit['selected_counts'].get('candidate_exception', 0)}`",
            f"- `keep_poi` sample: `{audit['selected_counts'].get('keep_poi', 0)}`",
            f"- `keep_context` sample: `{audit['selected_counts'].get('keep_context', 0)}`",
            f"- `exclude` sample: `{audit['selected_counts'].get('exclude', 0)}`",
            "- The sample is not proportional by decision. It is risk-aware and balanced: all `candidate_exception` rows are included, and the other decisions use bounded slices with oversampling of low-confidence and hard-class cases.",
            "",
            "## Hard classes intentionally oversampled",
            "",
        ]
    )
    for key, count in sorted(audit["hard_group_counts"].items()):
        lines.append(f"- `{key}`: `{count}` sampled entities")
    lines.extend(
        [
            "",
            "## Suggested evaluation workflow",
            "",
            "- Give the same blinded CSV to 3 annotators independently.",
            "- Merge the three completed CSVs by `sample_id`.",
            "- Compute inter-annotator agreement on the 4-way decision.",
            "- Build an adjudicated gold label for disagreements.",
            "- Compare the LLM outputs in the master JSON/JSONL package against the adjudicated gold labels.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a blinded annotation package for Eventour classification review.")
    parser.add_argument("--input", required=True, help="Merged classification JSONL path")
    parser.add_argument("--out-dir", required=True, help="Output directory for the annotation package")
    parser.add_argument("--keep-poi-sample", type=int, default=DEFAULT_KEEP_POI_SAMPLE)
    parser.add_argument("--keep-context-sample", type=int, default=DEFAULT_KEEP_CONTEXT_SAMPLE)
    parser.add_argument("--exclude-sample", type=int, default=DEFAULT_EXCLUDE_SAMPLE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    sampled_rows, audit = build_sample(
        rows,
        keep_poi_limit=args.keep_poi_sample,
        keep_context_limit=args.keep_context_sample,
        exclude_limit=args.exclude_sample,
        seed=args.seed,
    )
    sampled_rows.sort(key=lambda row: row["sample_id"])

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    master_json = {
        "metadata": {
            "source_input": str(Path(args.input)),
            "seed": args.seed,
            "decision_definitions": DECISION_DEFINITIONS,
            "eventour_category_definitions": EVENTOUR_CATEGORY_DEFINITIONS,
            "sampling_audit": audit,
        },
        "items": sampled_rows,
    }
    write_json(out_dir / "annotation_package_master.json", master_json)
    write_jsonl(out_dir / "annotation_package_master.jsonl", sampled_rows)

    blind_rows = [annotator_row(row, sample_id=row["sample_id"]) for row in sampled_rows]
    for suffix in ("A", "B", "C"):
        write_csv(out_dir / f"annotation_sheet_annotator_{suffix}.csv", blind_rows)

    instructions = build_instruction_markdown(len(sampled_rows), audit)
    (out_dir / "annotation_instructions.md").write_text(instructions, encoding="utf-8")

    print(
        json.dumps(
            {
                "sample_size": len(sampled_rows),
                "selected_counts": audit["selected_counts"],
                "hard_group_counts": audit["hard_group_counts"],
                "out_dir": str(out_dir),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

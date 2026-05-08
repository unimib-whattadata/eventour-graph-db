from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from eventour_kg.curation.apply_policy import apply_curation
from eventour_kg.curation import semantic_policy


def make_entity(
    item_qid: str,
    *,
    preferred_label: str,
    description: str = "",
    direct_labels: list[str] | None = None,
    ancestor_labels: list[str] | None = None,
    fact_texts: list[str] | None = None,
    decision: str = "candidate_exception",
    eventour_category: str | None = None,
    confidence: float = 0.5,
    needs_review: bool = True,
) -> dict[str, object]:
    return {
        "item_qid": item_qid,
        "preferred_label": preferred_label,
        "description": description,
        "direct_classes": [{"label": label} for label in (direct_labels or [])],
        "class_ancestors": [{"label": label} for label in (ancestor_labels or [])],
        "semantic_facts": [{"prompt_text": text} for text in (fact_texts or [])],
        "decision": decision,
        "eventour_category": eventour_category,
        "confidence": confidence,
        "needs_review": needs_review,
    }


def _write_minimal_annotations_xlsx(path: Path, *, rows: list[dict[str, str]]) -> None:
    shared_strings = ["ignored_header", "ignored_header_2"]
    for row in rows:
        for value in row.values():
            if value not in shared_strings:
                shared_strings.append(value)
    shared_index = {value: idx for idx, value in enumerate(shared_strings)}

    def build_row_xml(row_number: int, values: dict[str, str]) -> str:
        cells = []
        for column, value in values.items():
            index = shared_index[value]
            cells.append(f'<c r="{column}{row_number}" t="s"><v>{index}</v></c>')
        return f'<row r="{row_number}">{"".join(cells)}</row>'

    sheet_rows = [
        build_row_xml(1, {"A": "ignored_header"}),
        build_row_xml(2, {"A": "ignored_header_2"}),
    ]
    for offset, row in enumerate(rows, start=3):
        sheet_rows.append(build_row_xml(offset, row))

    shared_strings_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
        + "".join(f"<si><t>{value}</t></si>" for value in shared_strings)
        + "</sst>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )

    with ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared_strings_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


class ApplyCurationTests(unittest.TestCase):
    def test_city_override_wins_over_adjudication_and_semantic_policy(self) -> None:
        entity = make_entity(
            "Q1",
            preferred_label="Biblioteca test",
            description="biblioteca italiana",
            direct_labels=["biblioteca"],
            ancestor_labels=["biblioteca"],
        )
        adjudication = {
            "Q1": {
                "adjudicated_final_label": "secondary_poi",
                "adjudicated_final_category": "",
                "human_decision_majority": "keep_context",
            }
        }
        city_overrides = {
            "Q1": {
                "override_final_label": "primary_poi",
                "override_final_category": "museum_collection",
                "override_reason": "Local exception",
            }
        }

        result = apply_curation(
            entity,
            adjudication_by_qid=adjudication,
            city_overrides_by_qid=city_overrides,
        )

        self.assertEqual(result["final_label"], "primary_poi")
        self.assertEqual(result["final_category"], "museum_collection")
        self.assertEqual(result["curation_source"], "city_override")
        self.assertIsNone(result["policy_group"])
        self.assertIn("override", result["curation_notes"])

    def test_explicit_adjudication_wins_when_city_override_missing(self) -> None:
        entity = make_entity(
            "Q2",
            preferred_label="Palazzo test",
            description="historic palace in Milan",
            direct_labels=["palace"],
        )
        adjudication = {
            "Q2": {
                "adjudicated_final_label": "secondary_poi",
                "adjudicated_final_category": "historic_architecture",
                "human_decision_majority": "keep_poi",
                "human_category_majority": "museum_collection",
            }
        }

        result = apply_curation(entity, adjudication_by_qid=adjudication)

        self.assertEqual(result["final_label"], "secondary_poi")
        self.assertEqual(result["final_category"], "historic_architecture")
        self.assertEqual(result["curation_source"], "adjudication")
        self.assertIsNone(result["policy_group"])
        self.assertIn("explicit", result["curation_notes"])

    def test_adjudication_majority_default_wins_over_semantic_policy(self) -> None:
        entity = make_entity(
            "Q3",
            preferred_label="Duomo test",
            description="historic church in Milan",
            direct_labels=["church"],
        )
        adjudication = {
            "Q3": {
                "adjudicated_final_label": "",
                "adjudicated_final_category": "",
                "human_decision_majority": "keep_context",
                "human_category_majority": "",
            }
        }

        result = apply_curation(entity, adjudication_by_qid=adjudication)

        self.assertEqual(result["final_label"], "context_entity")
        self.assertIsNone(result["final_category"])
        self.assertEqual(result["curation_source"], "adjudication")
        self.assertIsNone(result["policy_group"])
        self.assertIn("majority", result["curation_notes"])

    def test_semantic_policy_applies_when_no_human_or_override_record_exists(self) -> None:
        entity = make_entity(
            "Q4",
            preferred_label="Cinema Anteo",
            description="cinema di Milano",
            direct_labels=["cinema"],
            eventour_category="museum_collection",
        )

        result = apply_curation(entity)

        self.assertEqual(result["final_label"], "primary_poi")
        self.assertEqual(result["final_category"], "museum_collection")
        self.assertEqual(result["curation_source"], "semantic_policy")
        self.assertEqual(result["policy_group"], "cinemas_theatres_performance")
        self.assertIn("semantic", result["curation_notes"])

    def test_fallback_never_returns_primary_poi_for_keep_poi_decision(self) -> None:
        entity = make_entity(
            "Q5",
            preferred_label="Unmatched gallery-ish thing",
            description="cultural venue without policy keywords",
            decision="keep_poi",
            eventour_category="museum_collection",
        )

        result = apply_curation(entity)

        self.assertEqual(result["final_label"], "secondary_poi")
        self.assertEqual(result["curation_source"], "fallback")
        self.assertIsNone(result["policy_group"])

    def test_fallback_uses_context_for_candidate_exception(self) -> None:
        entity = make_entity(
            "Q6",
            preferred_label="Needs manual pass",
            description="ambiguous venue without semantic policy keywords",
            decision="candidate_exception",
        )

        result = apply_curation(entity)

        self.assertEqual(result["final_label"], "context_entity")
        self.assertEqual(result["curation_source"], "fallback")
        self.assertIsNone(result["policy_group"])

    def test_fallback_uses_exclude_for_unknown_decision_without_cultural_signal(self) -> None:
        entity = make_entity(
            "Q7",
            preferred_label="Generic office block",
            description="administrative facility",
            decision="unknown",
        )

        result = apply_curation(entity)

        self.assertEqual(result["final_label"], "exclude")
        self.assertEqual(result["curation_source"], "fallback")
        self.assertIsNone(result["policy_group"])

    def test_cli_builds_wikidata_curation_outputs_from_temp_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            annotations_path = tmp_path / "annotations_all.xlsx"
            master_path = tmp_path / "annotation_package_master.json"
            classification_path = tmp_path / "wikidata_entity_classification.jsonl"
            adjudication_path = tmp_path / "wikidata_annotation_adjudication.csv"
            semantic_policy_path = tmp_path / "wikidata_semantic_policy.csv"
            city_overrides_path = tmp_path / "wikidata_city_overrides.csv"
            curated_final_path = tmp_path / "wikidata_curated_final.jsonl"
            summary_path = tmp_path / "wikidata_curated_summary.json"

            _write_minimal_annotations_xlsx(
                annotations_path,
                rows=[
                    {
                        "A": "ann_0001",
                        "B": "Q1",
                        "C": "Museo test",
                        "H": "keep_poi",
                        "I": "museum_collection",
                        "K": "keep_poi",
                        "L": "museum_collection",
                        "N": "exclude",
                        "O": "",
                    }
                ],
            )
            master_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "sample_id": "ann_0001",
                                "item_qid": "Q1",
                                "preferred_label": "Museo test",
                                "llm_decision": "candidate_exception",
                                "llm_eventour_category": "museum_collection",
                                "llm_confidence": 0.77,
                                "llm_needs_review": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            classification_rows = [
                make_entity(
                    "Q1",
                    preferred_label="Museo test",
                    description="museum in Milan",
                    direct_labels=["museum"],
                    decision="candidate_exception",
                    eventour_category="museum_collection",
                ),
                make_entity(
                    "Q2",
                    preferred_label="Cinema Test",
                    description="cinema in Milan",
                    direct_labels=["cinema"],
                    decision="candidate_exception",
                    eventour_category="museum_collection",
                ),
                make_entity(
                    "Q3",
                    preferred_label="Office Test",
                    description="administrative office",
                    decision="unknown",
                ),
            ]
            classification_path.write_text(
                "".join(json.dumps(row) + "\n" for row in classification_rows),
                encoding="utf-8",
            )

            env = dict(os.environ)
            src_path = str(Path(__file__).resolve().parents[1] / "src")
            env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else src_path + os.pathsep + env["PYTHONPATH"]

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "eventour_kg.curation.build_wikidata_curation",
                    "--city-id",
                    "milan",
                    "--annotations-workbook",
                    str(annotations_path),
                    "--annotation-master-json",
                    str(master_path),
                    "--classification-input",
                    str(classification_path),
                    "--adjudication-csv",
                    str(adjudication_path),
                    "--semantic-policy-csv",
                    str(semantic_policy_path),
                    "--city-overrides-csv",
                    str(city_overrides_path),
                    "--curated-final-jsonl",
                    str(curated_final_path),
                    "--summary-json",
                    str(summary_path),
                ],
                capture_output=True,
                check=False,
                env=env,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)

            cli_summary = json.loads(completed.stdout)
            self.assertEqual(cli_summary["city_id"], "milan")
            self.assertEqual(cli_summary["record_count"], 3)
            self.assertEqual(cli_summary["adjudication_row_count"], 1)
            self.assertEqual(cli_summary["semantic_policy_row_count"], len(semantic_policy.PRIORITY_ORDER))
            self.assertTrue(city_overrides_path.exists())

            with adjudication_path.open("r", encoding="utf-8", newline="") as handle:
                adjudication_rows = list(csv.DictReader(handle))
            self.assertEqual(len(adjudication_rows), 1)
            self.assertEqual(adjudication_rows[0]["item_qid"], "Q1")
            self.assertEqual(adjudication_rows[0]["human_decision_majority"], "keep_poi")
            self.assertEqual(adjudication_rows[0]["human_category_majority"], "museum_collection")

            with semantic_policy_path.open("r", encoding="utf-8", newline="") as handle:
                policy_rows = list(csv.DictReader(handle))
            self.assertEqual(len(policy_rows), len(semantic_policy.PRIORITY_ORDER))
            self.assertEqual(policy_rows[0]["policy_group"], semantic_policy.PRIORITY_ORDER[0])
            self.assertEqual(policy_rows[0]["priority_rank"], "1")
            self.assertEqual(policy_rows[0]["match_strategy"], "boundary_matched_keyword_bundle")
            self.assertEqual(policy_rows[0]["confidence_level"], "v1_strict")
            self.assertIn("group_description", policy_rows[0])
            self.assertIn("evidence_sample_ids", policy_rows[0])
            self.assertIn("recurring_direct_classes", policy_rows[0])
            self.assertIn("keywords=", policy_rows[0]["match_signals"])

            with city_overrides_path.open("r", encoding="utf-8", newline="") as handle:
                override_reader = csv.DictReader(handle)
                override_rows = list(override_reader)
            self.assertEqual(override_rows, [])
            self.assertIn("source", override_reader.fieldnames)

            curated_rows = [
                json.loads(line)
                for line in curated_final_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            curated_by_qid = {row["item_qid"]: row for row in curated_rows}
            self.assertEqual(curated_by_qid["Q1"]["final_label"], "primary_poi")
            self.assertEqual(curated_by_qid["Q1"]["curation_source"], "adjudication")
            self.assertEqual(curated_by_qid["Q2"]["final_label"], "primary_poi")
            self.assertEqual(curated_by_qid["Q2"]["curation_source"], "semantic_policy")
            self.assertEqual(curated_by_qid["Q3"]["final_label"], "exclude")
            self.assertEqual(curated_by_qid["Q3"]["curation_source"], "fallback")

            written_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(written_summary["record_count"], 3)
            self.assertEqual(written_summary["final_label_counts"]["primary_poi"], 2)
            self.assertEqual(written_summary["final_label_counts"]["exclude"], 1)


if __name__ == "__main__":
    unittest.main()

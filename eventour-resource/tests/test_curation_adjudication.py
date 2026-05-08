from __future__ import annotations

import unittest
from pathlib import Path

from eventour_kg.curation.adjudication import (
    build_adjudication_rows,
    load_annotation_package_master,
    load_merged_annotation_rows,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "cities" / "milan" / "evaluation" / "annotation_package_v1"


class CurationAdjudicationTests(unittest.TestCase):
    def test_build_adjudication_rows_computes_majority_and_preserves_llm_fields(self) -> None:
        annotations = [
            {
                "sample_id": "ann_0001",
                "item_qid": "Q1",
                "preferred_label": "Example",
                "serena_decision": "keep_poi",
                "blerina_decision": "exclude",
                "fabio_decision": "keep_poi",
                "serena_category": "historic_architecture",
                "blerina_category": None,
                "fabio_category": "historic_architecture",
            }
        ]
        master = {
            "ann_0001": {
                "llm_decision": "keep_poi",
                "llm_eventour_category": "historic_architecture",
                "llm_confidence": 0.82,
                "llm_needs_review": True,
            }
        }

        rows = build_adjudication_rows(annotations, master_by_sample_id=master)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["human_decision_majority"], "keep_poi")
        self.assertEqual(row["human_category_majority"], "historic_architecture")
        self.assertEqual(row["llm_decision"], "keep_poi")
        self.assertEqual(row["llm_eventour_category"], "historic_architecture")
        self.assertEqual(row["llm_confidence"], 0.82)
        self.assertTrue(row["llm_needs_review"])
        self.assertEqual(row["adjudicated_final_label"], "")
        self.assertEqual(row["adjudicated_final_category"], "")

    def test_build_adjudication_rows_leaves_category_majority_blank_without_keep_poi_majority(self) -> None:
        annotations = [
            {
                "sample_id": "ann_0002",
                "item_qid": "Q2",
                "preferred_label": "Example 2",
                "serena_decision": "keep_poi",
                "blerina_decision": "exclude",
                "fabio_decision": "exclude",
                "serena_category": "historic_architecture",
                "blerina_category": None,
                "fabio_category": None,
            }
        ]
        master = {
            "ann_0002": {
                "llm_decision": "candidate_exception",
                "llm_eventour_category": "historic_architecture",
                "llm_confidence": 0.51,
                "llm_needs_review": True,
            }
        }

        rows = build_adjudication_rows(annotations, master_by_sample_id=master)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["human_decision_majority"], "exclude")
        self.assertEqual(row["human_category_majority"], "")

    def test_build_adjudication_rows_raises_on_missing_master_record(self) -> None:
        annotations = [
            {
                "sample_id": "ann_missing",
                "item_qid": "Q3",
                "preferred_label": "Missing Master",
                "serena_decision": "exclude",
                "blerina_decision": "exclude",
                "fabio_decision": "exclude",
            }
        ]

        with self.assertRaisesRegex(KeyError, "ann_missing"):
            build_adjudication_rows(annotations, master_by_sample_id={})

    def test_build_adjudication_rows_leaves_majority_blank_for_partial_panel(self) -> None:
        annotations = [
            {
                "sample_id": "ann_0003",
                "item_qid": "Q4",
                "preferred_label": "Partial Panel",
                "serena_decision": "keep_poi",
                "blerina_decision": None,
                "fabio_decision": None,
                "serena_category": "historic_architecture",
                "blerina_category": None,
                "fabio_category": None,
            }
        ]
        master = {
            "ann_0003": {
                "llm_decision": "keep_poi",
                "llm_eventour_category": "historic_architecture",
                "llm_confidence": 0.73,
                "llm_needs_review": True,
            }
        }

        rows = build_adjudication_rows(annotations, master_by_sample_id=master)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["human_decision_majority"], "")
        self.assertEqual(row["human_category_majority"], "")

    def test_loaders_match_real_annotation_package_shapes(self) -> None:
        annotations = load_merged_annotation_rows(DATA_DIR / "annotations_all.xlsx")
        master_by_sample_id = load_annotation_package_master(DATA_DIR / "annotation_package_master.json")

        self.assertGreater(len(annotations), 700)
        self.assertIn("ann_0001", master_by_sample_id)

        first_row = annotations[0]
        self.assertEqual(first_row["sample_id"], "ann_0001")
        self.assertEqual(first_row["item_qid"], "Q4546860")
        self.assertEqual(first_row["serena_decision"], "keep_context")

        master_row = master_by_sample_id["ann_0001"]
        self.assertEqual(master_row["item_qid"], "Q4546860")
        self.assertEqual(master_row["llm_decision"], "candidate_exception")
        self.assertIn("llm_eventour_category", master_row)
        self.assertIn("llm_confidence", master_row)
        self.assertIn("llm_needs_review", master_row)


if __name__ == "__main__":
    unittest.main()

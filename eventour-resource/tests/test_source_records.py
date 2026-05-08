from __future__ import annotations

import unittest

from eventour_kg.extraction.source_records import _pick_external_id


class SourceRecordIdSelectionTests(unittest.TestCase):
    def test_sources_with_obj_id_prefer_obj_id_over_codice(self) -> None:
        properties = {
            "obj_id": 162523,
            "codice": "L219400",
        }

        for source_id in ("benches", "picnic_tables", "trees"):
            with self.subTest(source_id=source_id):
                self.assertEqual(_pick_external_id(source_id, properties), "162523")


if __name__ == "__main__":
    unittest.main()

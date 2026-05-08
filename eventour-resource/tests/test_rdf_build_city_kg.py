from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph

from eventour_kg.rdf.build_city_kg import build_city_kg


class RdfBuildCityKgTests(unittest.TestCase):
    def test_build_city_kg_writes_turtle_and_jsonld_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            normalized_dir = tmp_path / "normalized"
            normalized_dir.mkdir()
            gtfs_dir = tmp_path / "gtfs"
            gtfs_dir.mkdir()
            out_dir = tmp_path / "rdf"
            wikidata_curated_path = tmp_path / "wikidata_curated.jsonl"

            (normalized_dir / "historic_shops_normalized.jsonl").write_text(
                json.dumps(
                    {
                        "city_id": "milan",
                        "source_id": "historic_shops",
                        "record_id": "historic_shops:1",
                        "external_id": "1",
                        "domain": "poi",
                        "entity_family": "historic_shop",
                        "integration_role": "candidate_poi_source",
                        "preferred_label": "a Santa Lucia",
                        "display_address": "Via SAN PIETRO ALL'ORTO 3",
                        "source_category": "Ristorante",
                        "status": "attiva",
                        "geometry_type": "Point",
                        "longitude": 9.19561447250575,
                        "latitude": 45.4658047226987,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            self._write_csv(
                gtfs_dir / "stops.txt",
                ["stop_id", "stop_name", "stop_lat", "stop_lon"],
                [{"stop_id": "S1", "stop_name": "Stop One", "stop_lat": "45.0", "stop_lon": "9.0"}],
            )
            self._write_csv(
                gtfs_dir / "routes.txt",
                ["route_id", "route_short_name", "route_long_name", "route_desc", "route_type"],
                [{"route_id": "R1", "route_short_name": "1", "route_long_name": "Line One", "route_desc": "", "route_type": "0"}],
            )
            self._write_csv(
                gtfs_dir / "trips.txt",
                ["route_id", "trip_id", "shape_id"],
                [{"route_id": "R1", "trip_id": "T1", "shape_id": "SH1"}],
            )
            self._write_csv(
                gtfs_dir / "stop_times.txt",
                ["trip_id", "stop_id", "stop_sequence"],
                [{"trip_id": "T1", "stop_id": "S1", "stop_sequence": "1"}],
            )
            self._write_csv(
                gtfs_dir / "shapes.txt",
                ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
                [{"shape_id": "SH1", "shape_pt_lat": "45.0", "shape_pt_lon": "9.0", "shape_pt_sequence": "1"}],
            )

            wikidata_curated_path.write_text(
                json.dumps(
                    {
                        "item_qid": "Q1",
                        "item_uri": "http://www.wikidata.org/entity/Q1",
                        "preferred_label": "Cinema Test",
                        "description": "cinema in Milan",
                        "longitude": 9.2,
                        "latitude": 45.4,
                        "final_label": "primary_poi",
                        "final_category": "museum_collection",
                        "curation_source": "semantic_policy",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = build_city_kg(
                normalized_dir=normalized_dir,
                gtfs_dir=gtfs_dir,
                out_dir=out_dir,
                wikidata_curated_path=wikidata_curated_path,
            )

            self.assertTrue((out_dir / "eventour_ontology.ttl").exists())
            self.assertTrue((out_dir / "eventour_ontology.jsonld").exists())
            self.assertTrue((out_dir / "sources" / "historic_shops.ttl").exists())
            self.assertTrue((out_dir / "sources" / "historic_shops.jsonld").exists())
            self.assertTrue((out_dir / "sources" / "gtfs_structure.ttl").exists())
            self.assertTrue((out_dir / "sources" / "gtfs_structure.jsonld").exists())
            self.assertTrue((out_dir / "sources" / "wikidata_curated.ttl").exists())
            self.assertTrue((out_dir / "sources" / "wikidata_curated.jsonld").exists())
            self.assertTrue((out_dir / "milan_local_kg.ttl").exists())
            self.assertTrue((out_dir / "milan_local_kg.jsonld").exists())
            self.assertTrue((out_dir / "milan_eventour_kg.ttl").exists())
            self.assertTrue((out_dir / "milan_eventour_kg.jsonld").exists())
            self.assertEqual(result["source_graph_count"], 3)
            self.assertTrue(result["wikidata_graph_included"])

            merged = Graph()
            merged.parse(out_dir / "milan_eventour_kg.ttl", format="turtle")
            self.assertGreater(len(merged), 0)

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()

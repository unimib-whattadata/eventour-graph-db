from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from rdflib import RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS

from eventour_kg.rdf.gtfs_export import export_gtfs_structure_graph
from eventour_kg.rdf.iris import build_gtfs_route_iri, build_gtfs_stop_iri
from eventour_kg.rdf.ontology import EV


GEO = URIRef("http://www.opengis.net/ont/geosparql#hasGeometry")


class RdfGtfsExportTests(unittest.TestCase):
    def test_gtfs_export_emits_routes_stops_and_route_stop_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gtfs_dir = Path(tmp)
            self._write_csv(
                gtfs_dir / "stops.txt",
                ["stop_id", "stop_name", "stop_lat", "stop_lon"],
                [
                    {"stop_id": "S1", "stop_name": "Stop One", "stop_lat": "45.0", "stop_lon": "9.0"},
                    {"stop_id": "S2", "stop_name": "Stop Two", "stop_lat": "45.1", "stop_lon": "9.1"},
                ],
            )
            self._write_csv(
                gtfs_dir / "routes.txt",
                ["route_id", "route_short_name", "route_long_name", "route_desc", "route_type"],
                [
                    {
                        "route_id": "R1",
                        "route_short_name": "1",
                        "route_long_name": "Line One",
                        "route_desc": "Test line",
                        "route_type": "0",
                    }
                ],
            )
            self._write_csv(
                gtfs_dir / "trips.txt",
                ["route_id", "trip_id", "shape_id"],
                [{"route_id": "R1", "trip_id": "T1", "shape_id": "SH1"}],
            )
            self._write_csv(
                gtfs_dir / "stop_times.txt",
                ["trip_id", "stop_id", "stop_sequence"],
                [
                    {"trip_id": "T1", "stop_id": "S1", "stop_sequence": "1"},
                    {"trip_id": "T1", "stop_id": "S2", "stop_sequence": "2"},
                ],
            )
            self._write_csv(
                gtfs_dir / "shapes.txt",
                ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
                [
                    {"shape_id": "SH1", "shape_pt_lat": "45.0", "shape_pt_lon": "9.0", "shape_pt_sequence": "1"},
                    {"shape_id": "SH1", "shape_pt_lat": "45.1", "shape_pt_lon": "9.1", "shape_pt_sequence": "2"},
                ],
            )

            graph = export_gtfs_structure_graph(gtfs_dir)

        route = URIRef(build_gtfs_route_iri("R1"))
        stop_one = URIRef(build_gtfs_stop_iri("S1"))
        stop_two = URIRef(build_gtfs_stop_iri("S2"))

        self.assertIn((route, RDF.type, EV.MobilityRoute), graph)
        self.assertIn((route, RDFS.label, None), graph)
        self.assertIn((route, DCTERMS.identifier, None), graph)
        self.assertIn((route, EV.hasStop, stop_one), graph)
        self.assertIn((route, EV.hasStop, stop_two), graph)

        self.assertIn((stop_one, RDF.type, EV.MobilityNode), graph)
        self.assertIn((stop_one, RDFS.label, None), graph)
        self.assertIn((stop_one, DCTERMS.identifier, None), graph)
        self.assertIn((stop_one, GEO, None), graph)

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()

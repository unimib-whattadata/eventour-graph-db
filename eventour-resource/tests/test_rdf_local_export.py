from __future__ import annotations

import unittest

from rdflib import RDF, RDFS, DCTERMS, Namespace, URIRef

from eventour_kg.rdf.iris import build_entity_iri, build_geometry_iri
from eventour_kg.rdf.local_export import export_normalized_record, export_normalized_rows
from eventour_kg.rdf.ontology import EV


PROV = Namespace("http://www.w3.org/ns/prov#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
SCHEMA = Namespace("https://schema.org/")


class RdfLocalExportTests(unittest.TestCase):
    def test_export_normalized_point_record_emits_core_triples(self) -> None:
        record = {
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
            "description": None,
        }

        graph = export_normalized_record(record)
        entity = URIRef(build_entity_iri("historic_shops", "historic_shops:1"))
        geometry = URIRef(build_geometry_iri("historic_shops", "historic_shops:1"))

        self.assertIn((entity, RDF.type, EV.UrbanEntity), graph)
        self.assertIn((entity, RDF.type, EV.Place), graph)
        self.assertIn((entity, RDFS.label, None), graph)
        self.assertIn((entity, DCTERMS.identifier, None), graph)
        self.assertIn((entity, PROV.wasDerivedFrom, None), graph)
        self.assertIn((entity, EV.hasPrimaryFamily, EV.Place), graph)
        self.assertIn((entity, SCHEMA.streetAddress, None), graph)
        self.assertIn((entity, GEO.hasGeometry, geometry), graph)
        self.assertIn((entity, GEO.hasDefaultGeometry, geometry), graph)
        self.assertIn((geometry, RDF.type, GEO.Geometry), graph)
        self.assertIn((geometry, GEO.asWKT, None), graph)

    def test_export_record_without_geometry_skips_geometry_triples(self) -> None:
        record = {
            "city_id": "milan",
            "source_id": "benches",
            "record_id": "benches:L219400",
            "external_id": "L219400",
            "domain": "urban",
            "entity_family": "bench",
            "integration_role": "support_source",
            "preferred_label": "Bench - vie Guerzoni - Ciaia",
            "display_address": "vie Guerzoni - Ciaia",
            "source_category": "bench",
            "status": None,
            "geometry_type": "MultiLineString",
            "longitude": None,
            "latitude": None,
            "description": None,
        }

        graph = export_normalized_record(record)
        entity = URIRef(build_entity_iri("benches", "benches:L219400"))

        self.assertIn((entity, RDF.type, EV.UrbanEntity), graph)
        self.assertIn((entity, RDF.type, EV.SupportService), graph)
        self.assertNotIn((entity, GEO.hasGeometry, None), graph)
        self.assertNotIn((entity, GEO.hasDefaultGeometry, None), graph)

    def test_export_rows_rejects_duplicate_record_ids(self) -> None:
        rows = [
            {
                "city_id": "milan",
                "source_id": "benches",
                "record_id": "benches:L219400",
                "external_id": "L219400",
                "domain": "urban",
                "entity_family": "bench",
                "integration_role": "support_source",
                "preferred_label": "Bench - first",
                "display_address": "first",
                "source_category": "bench",
                "status": None,
                "geometry_type": "MultiLineString",
                "longitude": None,
                "latitude": None,
                "description": None,
            },
            {
                "city_id": "milan",
                "source_id": "benches",
                "record_id": "benches:L219400",
                "external_id": "L219400",
                "domain": "urban",
                "entity_family": "bench",
                "integration_role": "support_source",
                "preferred_label": "Bench - second",
                "display_address": "second",
                "source_category": "bench",
                "status": None,
                "geometry_type": "MultiLineString",
                "longitude": None,
                "latitude": None,
                "description": None,
            },
        ]

        with self.assertRaisesRegex(ValueError, "Duplicate record_id"):
            export_normalized_rows(rows)


if __name__ == "__main__":
    unittest.main()

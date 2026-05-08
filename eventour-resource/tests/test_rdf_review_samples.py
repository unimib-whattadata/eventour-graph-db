from __future__ import annotations

import unittest

from rdflib import RDF, SKOS
from rdflib import Namespace

from eventour_kg.rdf.ontology import EV
from eventour_kg.rdf.review_samples import (
    export_open_meteo_review_sample,
    export_review_sample_for_records,
)

GEO = Namespace("http://www.opengis.net/ont/geosparql#")


class RdfReviewSamplesTests(unittest.TestCase):
    def test_export_review_sample_limits_to_ten_unique_entities(self) -> None:
        records = []
        for index in range(12):
            records.append(
                {
                    "source_id": "benches",
                    "record_id": f"benches:{1000 + index}",
                    "raw_geometry": None,
                    "raw_properties": {
                        "località": f"Bench area {index}",
                        "descrizione_codice": "Panchina",
                        "municipio": 1,
                    },
                }
            )

        graph, summary = export_review_sample_for_records(
            source_id="benches",
            dataset_label="Panchine",
            entity_family="bench",
            records=records,
            sample_size=10,
        )

        self.assertEqual(len(summary), 10)
        self.assertEqual(len(set(item["subject_iri"] for item in summary)), 10)
        self.assertEqual(len(set(graph.subjects(RDF.type, EV.UrbanEntity))), 10)
        self.assertTrue(all(item["label"].startswith("Bench - ") for item in summary))

    def test_export_review_sample_emits_linestring_geometry_when_present(self) -> None:
        records = [
            {
                "source_id": "tpl_metro_routes",
                "record_id": "tpl_metro_routes:100002",
                "raw_geometry": {
                    "type": "LineString",
                    "coordinates": [[9.0, 45.0], [9.1, 45.1]],
                },
                "raw_properties": {
                    "linea": "1",
                    "nome": "BISCEGLIE - SESTO 1 MAGGIO FS",
                    "mezzo": "METRO",
                    "percorso": "100002",
                    "num_ferm": "27",
                    "lung_km": "16.38",
                },
            }
        ]

        graph, summary = export_review_sample_for_records(
            source_id="tpl_metro_routes",
            dataset_label="ATM percorsi linee metro",
            entity_family="route_geometry",
            records=records,
            sample_size=10,
        )

        self.assertEqual(len(summary), 1)
        self.assertIn((None, RDF.type, EV.MobilityRoute), graph)
        geo_wkts = [str(obj) for obj in graph.objects(None, GEO.asWKT)]
        self.assertTrue(any(wkt.startswith("LINESTRING") for wkt in geo_wkts))

    def test_export_open_meteo_review_sample_emits_ten_concepts(self) -> None:
        payload = {
            str(index): {
                "day": {"description": f"Day {index}", "image": f"https://example.com/day/{index}.png"},
                "night": {"description": f"Night {index}", "image": f"https://example.com/night/{index}.png"},
            }
            for index in range(12)
        }

        graph, summary = export_open_meteo_review_sample(payload, sample_size=10)

        self.assertEqual(len(summary), 10)
        self.assertEqual(len(set(graph.subjects(RDF.type, SKOS.Concept))), 10)
        self.assertEqual(len(set(graph.subjects(RDF.type, EV.UrbanEntity))), 0)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from rdflib import DCTERMS, OWL, RDF, URIRef

from eventour_kg.rdf.iris import (
    build_category_iri,
    build_curation_label_iri,
    build_entity_iri,
    build_eventour_role_iri,
    build_geometry_iri,
)
from eventour_kg.rdf.ontology import EV
from eventour_kg.rdf.wikidata_export import export_curated_wikidata_rows


GEO_HAS_GEOMETRY = URIRef("http://www.opengis.net/ont/geosparql#hasGeometry")
GEO_HAS_DEFAULT_GEOMETRY = URIRef("http://www.opengis.net/ont/geosparql#hasDefaultGeometry")


class RdfWikidataExportTests(unittest.TestCase):
    def test_export_curated_wikidata_rows_retains_only_non_excluded_entities(self) -> None:
        rows = [
            {
                "item_qid": "Q1",
                "item_uri": "http://www.wikidata.org/entity/Q1",
                "preferred_label": "Cinema Test",
                "description": "cinema in Milan",
                "longitude": 9.1,
                "latitude": 45.4,
                "final_label": "primary_poi",
                "final_category": "museum_collection",
                "curation_source": "semantic_policy",
            },
            {
                "item_qid": "Q2",
                "item_uri": "http://www.wikidata.org/entity/Q2",
                "preferred_label": "University Test",
                "description": "university in Milan",
                "longitude": 9.2,
                "latitude": 45.5,
                "final_label": "context_entity",
                "final_category": None,
                "curation_source": "adjudication",
            },
            {
                "item_qid": "Q3",
                "item_uri": "http://www.wikidata.org/entity/Q3",
                "preferred_label": "Hotel Test",
                "final_label": "exclude",
                "curation_source": "semantic_policy",
            },
            {
                "item_qid": "Q4",
                "item_uri": "http://www.wikidata.org/entity/Q4",
                "preferred_label": "Coordinate Missing",
                "final_label": "secondary_poi",
                "curation_source": "fallback",
            },
            {
                "item_qid": "Q5",
                "item_uri": "http://www.wikidata.org/entity/Q5",
                "preferred_label": "Old Label Secondary",
                "longitude": 9.3,
                "latitude": 45.6,
                "final_label": "secondary_cultural_poi",
                "curation_source": "fallback",
            },
        ]

        graph = export_curated_wikidata_rows(rows)

        entity_q1 = URIRef(build_entity_iri("wikidata", "Q1"))
        entity_q2 = URIRef(build_entity_iri("wikidata", "Q2"))
        entity_q3 = URIRef(build_entity_iri("wikidata", "Q3"))
        entity_q4 = URIRef(build_entity_iri("wikidata", "Q4"))
        entity_q5 = URIRef(build_entity_iri("wikidata", "Q5"))

        self.assertIn((entity_q1, RDF.type, EV.Place), graph)
        self.assertIn((entity_q2, RDF.type, EV.Place), graph)
        self.assertNotIn((entity_q3, None, None), graph)
        self.assertNotIn((entity_q4, None, None), graph)
        self.assertIn((entity_q5, RDF.type, EV.Place), graph)

        self.assertIn((entity_q1, EV.hasCurationLabel, URIRef(build_curation_label_iri("primary_poi"))), graph)
        self.assertIn((entity_q1, EV.hasEventourRole, URIRef(build_eventour_role_iri("primary_poi"))), graph)
        self.assertIn((entity_q5, EV.hasEventourRole, URIRef(build_eventour_role_iri("secondary_poi"))), graph)
        self.assertIn(
            (entity_q1, EV.hasEventourCategory, URIRef(build_category_iri("museum_collection"))),
            graph,
        )
        self.assertIn((entity_q1, OWL.sameAs, URIRef("http://www.wikidata.org/entity/Q1")), graph)
        self.assertIn((entity_q1, GEO_HAS_GEOMETRY, URIRef(build_geometry_iri("wikidata", "Q1"))), graph)
        self.assertIn((entity_q1, GEO_HAS_DEFAULT_GEOMETRY, URIRef(build_geometry_iri("wikidata", "Q1"))), graph)
        self.assertIn((entity_q1, DCTERMS.provenance, None), graph)
        self.assertNotIn((entity_q2, EV.hasEventourCategory, None), graph)

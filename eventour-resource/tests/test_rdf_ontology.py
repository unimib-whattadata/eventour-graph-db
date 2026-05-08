from __future__ import annotations

import unittest

from rdflib import RDF, RDFS, SKOS, OWL, URIRef

from eventour_kg.rdf.namespaces import ontology_term
from eventour_kg.rdf.ontology import build_eventour_ontology_graph


class RdfOntologyTests(unittest.TestCase):
    def test_core_classes_and_properties_exist(self) -> None:
        graph = build_eventour_ontology_graph()

        for local_name in (
            "UrbanEntity",
            "Place",
            "Area",
            "MobilityNode",
            "MobilityRoute",
            "SupportService",
            "EnvironmentalFeature",
        ):
            self.assertIn((URIRef(ontology_term(local_name)), RDF.type, OWL.Class), graph)

        for local_name in (
            "hasPrimaryFamily",
            "hasSecondaryFamily",
            "hasEventourCategory",
            "hasEventourRole",
            "hasCurationLabel",
            "hasStop",
        ):
            predicate = URIRef(ontology_term(local_name))
            self.assertTrue(
                (predicate, RDF.type, OWL.ObjectProperty) in graph
                or (predicate, RDF.type, OWL.DatatypeProperty) in graph
            )

    def test_core_family_subclass_links_exist(self) -> None:
        graph = build_eventour_ontology_graph()
        urban_entity = URIRef(ontology_term("UrbanEntity"))

        for local_name in (
            "Place",
            "Area",
            "MobilityNode",
            "MobilityRoute",
            "SupportService",
            "EnvironmentalFeature",
        ):
            self.assertIn((URIRef(ontology_term(local_name)), RDFS.subClassOf, urban_entity), graph)

    def test_eventour_category_concept_scheme_exists(self) -> None:
        graph = build_eventour_ontology_graph()
        scheme = URIRef(ontology_term("EventourCategoryScheme"))
        role_scheme = URIRef(ontology_term("EventourRoleScheme"))
        curation_scheme = URIRef(ontology_term("CurationLabelScheme"))

        self.assertIn((scheme, RDF.type, SKOS.ConceptScheme), graph)
        self.assertIn((scheme, SKOS.prefLabel, None), graph)
        self.assertIn((role_scheme, RDF.type, SKOS.ConceptScheme), graph)
        self.assertIn((role_scheme, SKOS.prefLabel, None), graph)
        self.assertIn((curation_scheme, RDF.type, SKOS.ConceptScheme), graph)
        self.assertIn((curation_scheme, SKOS.prefLabel, None), graph)


if __name__ == "__main__":
    unittest.main()

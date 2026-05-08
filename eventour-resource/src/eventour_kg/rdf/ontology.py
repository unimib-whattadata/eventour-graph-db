"""Build the lightweight Eventour ontology graph."""

from __future__ import annotations

from rdflib import Graph, Literal, Namespace, RDF, RDFS, SKOS, OWL

from eventour_kg.rdf.namespaces import ONTOLOGY_BASE


EV = Namespace(ONTOLOGY_BASE)


CORE_CLASSES = (
    "UrbanEntity",
    "Place",
    "Area",
    "MobilityNode",
    "MobilityRoute",
    "SupportService",
    "EnvironmentalFeature",
)

CORE_PROPERTIES = (
    ("hasPrimaryFamily", OWL.ObjectProperty),
    ("hasSecondaryFamily", OWL.ObjectProperty),
    ("hasEventourCategory", OWL.ObjectProperty),
    ("hasEventourRole", OWL.ObjectProperty),
    ("hasCurationLabel", OWL.ObjectProperty),
    ("hasStop", OWL.ObjectProperty),
)


def build_eventour_ontology_graph() -> Graph:
    graph = Graph()
    graph.bind("ev", EV)
    graph.bind("owl", OWL)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("skos", SKOS)

    for class_name in CORE_CLASSES:
        graph.add((EV[class_name], RDF.type, OWL.Class))
        graph.add((EV[class_name], RDFS.label, Literal(class_name)))

    for class_name in CORE_CLASSES[1:]:
        graph.add((EV[class_name], RDFS.subClassOf, EV.UrbanEntity))

    for property_name, property_type in CORE_PROPERTIES:
        graph.add((EV[property_name], RDF.type, property_type))
        graph.add((EV[property_name], RDFS.label, Literal(property_name)))

    graph.add((EV.EventourCategoryScheme, RDF.type, SKOS.ConceptScheme))
    graph.add((EV.EventourCategoryScheme, SKOS.prefLabel, Literal("Eventour Category Scheme", lang="en")))
    graph.add((EV.EventourRoleScheme, RDF.type, SKOS.ConceptScheme))
    graph.add((EV.EventourRoleScheme, SKOS.prefLabel, Literal("Eventour Role Scheme", lang="en")))
    graph.add((EV.CurationLabelScheme, RDF.type, SKOS.ConceptScheme))
    graph.add((EV.CurationLabelScheme, SKOS.prefLabel, Literal("Eventour Curation Label Scheme", lang="en")))

    return graph

"""Generate the publishable Eventour ontology artifact.

The final ontology combines the converter static model with the Eventour
role/place layer used by the Wikidata projection. It intentionally excludes
city-specific individuals such as Milan datasets, source records, geometries,
and concrete urban assets.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import DCTERMS, Graph, Literal, Namespace, OWL, RDF, RDFS, SKOS, URIRef


EVT = Namespace("http://eventour.unimib.it/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SCHEMA = Namespace("https://schema.org/")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")


GLOBAL_RESOURCE_PREFIXES = (
    "http://eventour.unimib.it/category/",
    "http://eventour.unimib.it/curation-label/",
    "http://eventour.unimib.it/role/",
    "http://eventour.unimib.it/scheme/",
)

CITY_OR_INSTANCE_PREFIXES = (
    "http://eventour.unimib.it/activity/",
    "http://eventour.unimib.it/agent/",
    "http://eventour.unimib.it/bench/",
    "http://eventour.unimib.it/bicycle-parking-area/",
    "http://eventour.unimib.it/bike-sharing-station/",
    "http://eventour.unimib.it/dataset/",
    "http://eventour.unimib.it/distribution/",
    "http://eventour.unimib.it/drinking-fountain/",
    "http://eventour.unimib.it/ev-charging-station/",
    "http://eventour.unimib.it/historic-shop/",
    "http://eventour.unimib.it/milan/",
    "http://eventour.unimib.it/municipality/",
    "http://eventour.unimib.it/nil/",
    "http://eventour.unimib.it/organization/",
    "http://eventour.unimib.it/parking-facility/",
    "http://eventour.unimib.it/picnic-table/",
    "http://eventour.unimib.it/place/",
    "http://eventour.unimib.it/project/",
    "http://eventour.unimib.it/public-toilet/",
    "http://eventour.unimib.it/route-pattern/",
    "http://eventour.unimib.it/service-pattern/",
    "http://eventour.unimib.it/source-record/",
    "http://eventour.unimib.it/stop/",
    "http://eventour.unimib.it/stop-in-route/",
    "http://eventour.unimib.it/timetable-summary/",
    "http://eventour.unimib.it/transit-line/",
    "http://eventour.unimib.it/tree/",
    "http://eventour.unimib.it/wifi-access-point/",
)


ROLE_DEFINITIONS = {
    "primary-poi": (
        "Primary POI",
        "Culturally or historically salient urban place that can act as a destination anchor for itinerary generation, cultural promotion, and event-tourism applications.",
    ),
    "secondary-poi": (
        "Secondary POI",
        "Non-primary geolocated urban place candidate that can support operational tasks such as crowd redistribution, alternative routing, local discovery, or post-event staggering.",
    ),
    "context-entity": (
        "Context Entity",
        "Geolocated entity that provides semantic background for the urban knowledge graph but is not treated as a candidate destination or redistribution anchor.",
    ),
}


def bind_prefixes(graph: Graph) -> None:
    graph.bind("dct", DCTERMS)
    graph.bind("evt", EVT)
    graph.bind("geo", GEO)
    graph.bind("owl", OWL)
    graph.bind("prov", PROV)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("schema", SCHEMA)
    graph.bind("skos", SKOS)
    graph.bind("xsd", XSD)


def is_instance_resource(value: object) -> bool:
    if not isinstance(value, URIRef):
        return False
    text = str(value)
    return any(text.startswith(prefix) for prefix in CITY_OR_INSTANCE_PREFIXES)


def is_global_controlled_vocabulary(value: object) -> bool:
    if not isinstance(value, URIRef):
        return False
    text = str(value)
    return any(text.startswith(prefix) for prefix in GLOBAL_RESOURCE_PREFIXES)


def include_subject(source_graph: Graph, subject: URIRef) -> bool:
    if is_instance_resource(subject):
        return False
    if is_global_controlled_vocabulary(subject):
        return True
    if (subject, RDF.type, OWL.Class) in source_graph:
        return True
    if (subject, RDF.type, RDF.Property) in source_graph:
        return True
    if (subject, RDF.type, OWL.ObjectProperty) in source_graph:
        return True
    if (subject, RDF.type, OWL.DatatypeProperty) in source_graph:
        return True
    if (subject, RDF.type, OWL.AnnotationProperty) in source_graph:
        return True
    if (subject, RDF.type, SKOS.ConceptScheme) in source_graph:
        return True
    if subject == EVT.EventourOntology:
        return True
    return False


def copy_ontology_terms(target: Graph, source: Graph) -> None:
    for subject in set(source.subjects()):
        if not isinstance(subject, URIRef) or not include_subject(source, subject):
            continue
        for predicate, obj in source.predicate_objects(subject):
            if is_instance_resource(obj):
                continue
            target.add((subject, predicate, obj))


def add_core_place_layer(graph: Graph) -> None:
    graph.add((EVT.EventourOntology, RDF.type, OWL.Ontology))
    graph.add((EVT.EventourOntology, RDFS.label, Literal("Eventour ontology", lang="en")))
    graph.add(
        (
            EVT.EventourOntology,
            DCTERMS.description,
            Literal(
                "Ontology for the Eventour multi-layer urban knowledge graph, covering municipal urban infrastructure, mobility and service layers, and a role-based semantic place layer.",
                lang="en",
            ),
        )
    )
    graph.add((EVT.EventourOntology, OWL.versionInfo, Literal("2026-05-03")))

    graph.add((EVT.UrbanEntity, RDF.type, OWL.Class))
    graph.add((EVT.UrbanEntity, RDFS.label, Literal("Urban entity", lang="en")))
    graph.add(
        (
            EVT.UrbanEntity,
            RDFS.comment,
            Literal("Top-level class for entities represented in an Eventour city knowledge graph.", lang="en"),
        )
    )

    graph.add((EVT.UrbanThing, RDFS.subClassOf, EVT.UrbanEntity))

    graph.add((EVT.UrbanPlace, RDF.type, OWL.Class))
    graph.add((EVT.UrbanPlace, RDFS.label, Literal("Urban place", lang="en")))
    graph.add((EVT.UrbanPlace, RDFS.subClassOf, EVT.UrbanEntity))
    graph.add((EVT.UrbanPlace, RDFS.subClassOf, GEO.Feature))

    graph.add((EVT.Place, RDF.type, OWL.Class))
    graph.add((EVT.Place, RDFS.label, Literal("Place", lang="en")))
    graph.add((EVT.Place, RDFS.subClassOf, EVT.UrbanPlace))
    graph.add(
        (
            EVT.Place,
            RDFS.comment,
            Literal("Geolocated place entity in the Eventour semantic place layer.", lang="en"),
        )
    )

    property_specs = {
        EVT.hasEventourRole: (
            OWL.ObjectProperty,
            "has Eventour role",
            EVT.Place,
            SKOS.Concept,
            "Associates a semantic place with its application role in Eventour.",
        ),
        EVT.hasEventourCategory: (
            OWL.ObjectProperty,
            "has Eventour category",
            EVT.Place,
            SKOS.Concept,
            "Associates a primary or secondary place with a semantic Eventour category.",
        ),
        EVT.hasCurationLabel: (
            OWL.ObjectProperty,
            "has curation label",
            EVT.Place,
            SKOS.Concept,
            "Stores the normalized curation label assigned during semantic place curation.",
        ),
        EVT.hasPrimaryFamily: (
            OWL.ObjectProperty,
            "has primary family",
            EVT.UrbanEntity,
            OWL.Class,
            "Links an entity to its broad Eventour family.",
        ),
        EVT.hasSecondaryFamily: (
            OWL.ObjectProperty,
            "has secondary family",
            EVT.UrbanEntity,
            OWL.Class,
            "Links an entity to an additional Eventour family when applicable.",
        ),
    }
    for prop, (prop_type, label, domain, range_, comment) in property_specs.items():
        graph.add((prop, RDF.type, prop_type))
        graph.add((prop, RDFS.label, Literal(label, lang="en")))
        graph.add((prop, RDFS.domain, domain))
        graph.add((prop, RDFS.range, range_))
        graph.add((prop, RDFS.comment, Literal(comment, lang="en")))

    scheme_specs = {
        EVT.EventourRoleScheme: "Eventour role scheme",
        EVT.EventourCategoryScheme: "Eventour category scheme",
        EVT.CurationLabelScheme: "Eventour curation label scheme",
    }
    for scheme, label in scheme_specs.items():
        graph.add((scheme, RDF.type, SKOS.ConceptScheme))
        graph.add((scheme, SKOS.prefLabel, Literal(label, lang="en")))

    for scheme in (EVT.EventourCategoryScheme, EVT.CurationLabelScheme):
        for concept in set(graph.subjects(SKOS.inScheme, scheme)):
            graph.add((concept, SKOS.topConceptOf, scheme))
            graph.add((scheme, SKOS.hasTopConcept, concept))

    for local_id, (label, definition) in ROLE_DEFINITIONS.items():
        role = URIRef(f"http://eventour.unimib.it/role/{local_id}")
        graph.add((role, RDF.type, SKOS.Concept))
        graph.add((role, SKOS.inScheme, EVT.EventourRoleScheme))
        graph.add((role, SKOS.topConceptOf, EVT.EventourRoleScheme))
        graph.add((EVT.EventourRoleScheme, SKOS.hasTopConcept, role))
        graph.add((role, SKOS.prefLabel, Literal(label, lang="en")))
        graph.add((role, SKOS.definition, Literal(definition, lang="en")))


def build_final_ontology(static_model_path: Path, wikidata_layer_path: Path) -> Graph:
    output = Graph()
    bind_prefixes(output)

    static_graph = Graph().parse(static_model_path)
    copy_ontology_terms(output, static_graph)

    wikidata_graph = Graph().parse(wikidata_layer_path)
    copy_ontology_terms(output, wikidata_graph)

    add_core_place_layer(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the final Eventour ontology TTL artifact.")
    parser.add_argument("--static-model", required=True, help="Static model TTL from the Comune KG converter")
    parser.add_argument("--wikidata-layer", required=True, help="Wikidata place layer TTL or NT")
    parser.add_argument("--out", required=True, help="Output ontology TTL path")
    args = parser.parse_args()

    graph = build_final_ontology(Path(args.static_model), Path(args.wikidata_layer))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=out, format="turtle")
    print({"output": str(out), "triples": len(graph)})


if __name__ == "__main__":
    main()

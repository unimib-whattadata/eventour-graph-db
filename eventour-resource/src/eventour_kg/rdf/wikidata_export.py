"""Export curated Wikidata rows into RDF graphs."""

from __future__ import annotations

from rdflib import Graph, Literal, Namespace, OWL, RDF, RDFS, SKOS, DCTERMS, URIRef

from eventour_kg.rdf.iris import (
    build_category_iri,
    build_curation_label_iri,
    build_entity_iri,
    build_eventour_role_iri,
    build_geometry_iri,
    build_source_iri,
)
from eventour_kg.rdf.ontology import EV


GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PROV = Namespace("http://www.w3.org/ns/prov#")

WIKIDATA_SOURCE_ID = "wikidata"
RETAINED_FINAL_LABELS = {"primary_poi", "secondary_poi", "secondary_cultural_poi", "context_entity"}
FINAL_LABEL_TO_ROLE = {
    "primary_poi": "primary_poi",
    "secondary_poi": "secondary_poi",
    "secondary_cultural_poi": "secondary_poi",
    "context_entity": "context_entity",
}
ROLE_LABELS = {
    "primary_poi": "Primary POI",
    "secondary_poi": "Secondary POI",
    "context_entity": "Context Entity",
}
ROLE_DEFINITIONS = {
    "primary_poi": "Culturally or historically salient urban place usable as a destination anchor.",
    "secondary_poi": "Non-primary geolocated urban place candidate usable for operational tasks such as crowd redistribution or alternative routing.",
    "context_entity": "Geolocated entity that provides urban context but is not treated as a candidate destination or redistribution anchor.",
}
CURATION_LABELS = {
    "primary_poi": "Primary POI",
    "secondary_poi": "Secondary POI",
    "secondary_cultural_poi": "Secondary Cultural POI",
    "context_entity": "Context Entity",
    "exclude": "Exclude",
}


def _bind_namespaces(graph: Graph) -> None:
    graph.bind("dcterms", DCTERMS)
    graph.bind("ev", EV)
    graph.bind("geo", GEO)
    graph.bind("owl", OWL)
    graph.bind("prov", PROV)
    graph.bind("rdfs", RDFS)
    graph.bind("skos", SKOS)


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _point_wkt(longitude: float, latitude: float) -> Literal:
    return Literal(f"POINT ({longitude} {latitude})", datatype=GEO.wktLiteral)


def _add_category_concept(graph: Graph, category_id: str) -> URIRef:
    concept = URIRef(build_category_iri(category_id))
    graph.add((concept, RDF.type, SKOS.Concept))
    graph.add((concept, SKOS.inScheme, EV.EventourCategoryScheme))
    graph.add((concept, SKOS.prefLabel, Literal(category_id.replace("_", " "))))
    return concept


def _add_curation_label_concept(graph: Graph, final_label: str) -> URIRef:
    concept = URIRef(build_curation_label_iri(final_label))
    graph.add((concept, RDF.type, SKOS.Concept))
    graph.add((concept, SKOS.inScheme, EV.CurationLabelScheme))
    graph.add((concept, SKOS.prefLabel, Literal(CURATION_LABELS[final_label], lang="en")))
    return concept


def _add_eventour_role_concept(graph: Graph, role_id: str) -> URIRef:
    concept = URIRef(build_eventour_role_iri(role_id))
    graph.add((concept, RDF.type, SKOS.Concept))
    graph.add((concept, SKOS.inScheme, EV.EventourRoleScheme))
    graph.add((concept, SKOS.prefLabel, Literal(ROLE_LABELS[role_id], lang="en")))
    graph.add((concept, SKOS.definition, Literal(ROLE_DEFINITIONS[role_id], lang="en")))
    return concept


def export_curated_wikidata_record(record: dict[str, object]) -> Graph:
    graph = Graph()
    _bind_namespaces(graph)

    final_label = _normalize_text(record.get("final_label"))
    if final_label not in RETAINED_FINAL_LABELS:
        return graph

    longitude = record.get("longitude")
    latitude = record.get("latitude")
    if longitude is None or latitude is None:
        return graph

    item_qid = _normalize_text(record.get("item_qid"))
    if item_qid is None:
        raise ValueError("Curated Wikidata record is missing item_qid")

    entity = URIRef(build_entity_iri(WIKIDATA_SOURCE_ID, item_qid))
    source = URIRef(build_source_iri("wikidata_curated"))
    graph.add((entity, RDF.type, EV.UrbanEntity))
    graph.add((entity, RDF.type, EV.Place))
    graph.add((entity, EV.hasPrimaryFamily, EV.Place))
    graph.add((entity, DCTERMS.identifier, Literal(item_qid)))
    graph.add((entity, PROV.wasDerivedFrom, source))
    graph.add((entity, DCTERMS.source, source))

    label = _normalize_text(record.get("preferred_label"))
    if label is not None:
        graph.add((entity, RDFS.label, Literal(label)))

    description = _normalize_text(record.get("description"))
    if description is not None:
        graph.add((entity, DCTERMS.description, Literal(description)))

    item_uri = _normalize_text(record.get("item_uri"))
    if item_uri is not None:
        graph.add((entity, OWL.sameAs, URIRef(item_uri)))

    curation_label = _add_curation_label_concept(graph, final_label)
    graph.add((entity, EV.hasCurationLabel, curation_label))

    role_id = FINAL_LABEL_TO_ROLE[final_label]
    eventour_role = _add_eventour_role_concept(graph, role_id)
    graph.add((entity, EV.hasEventourRole, eventour_role))

    final_category = _normalize_text(record.get("final_category"))
    if final_category is not None:
        category = _add_category_concept(graph, final_category)
        graph.add((entity, EV.hasEventourCategory, category))

    curation_source = _normalize_text(record.get("curation_source"))
    if curation_source is not None:
        graph.add((entity, DCTERMS.provenance, Literal(curation_source)))

    geometry = URIRef(build_geometry_iri(WIKIDATA_SOURCE_ID, item_qid))
    graph.add((entity, RDF.type, GEO.Feature))
    graph.add((entity, GEO.hasGeometry, geometry))
    graph.add((entity, GEO.hasDefaultGeometry, geometry))
    graph.add((geometry, RDF.type, GEO.Geometry))
    graph.add((geometry, GEO.asWKT, _point_wkt(float(longitude), float(latitude))))

    return graph


def export_curated_wikidata_rows(rows: list[dict[str, object]]) -> Graph:
    graph = Graph()
    _bind_namespaces(graph)
    seen_item_qids: set[str] = set()
    for row in rows:
        item_qid = _normalize_text(row.get("item_qid"))
        if item_qid is None:
            raise ValueError("Curated Wikidata row is missing item_qid")
        if item_qid in seen_item_qids:
            raise ValueError(f"Duplicate item_qid in curated Wikidata rows: {item_qid}")
        seen_item_qids.add(item_qid)
        graph += export_curated_wikidata_record(row)
    return graph

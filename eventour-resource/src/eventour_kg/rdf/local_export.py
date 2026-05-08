"""Export normalized local records into RDF graphs."""

from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, DCTERMS, URIRef
from eventour_kg.rdf.iris import build_entity_iri, build_geometry_iri, build_source_iri
from eventour_kg.rdf.ontology import EV


PROV = Namespace("http://www.w3.org/ns/prov#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
SCHEMA = Namespace("https://schema.org/")


FAMILY_CLASS_MAP = {
    "historic_shop": EV.Place,
    "administrative_area": EV.Area,
    "metro_station": EV.MobilityNode,
    "surface_stop": EV.MobilityNode,
    "bike_sharing_station": EV.MobilityNode,
    "bike_parking": EV.MobilityNode,
    "park_and_ride": EV.MobilityNode,
    "parking_facility": EV.MobilityNode,
    "ev_charging_station": EV.MobilityNode,
    "restricted_access_gate": EV.MobilityNode,
    "public_toilet": EV.SupportService,
    "wifi_hotspot": EV.SupportService,
    "drinking_fountain": EV.SupportService,
    "bench": EV.SupportService,
    "picnic_table": EV.SupportService,
    "tree": EV.EnvironmentalFeature,
}


def _bind_namespaces(graph: Graph) -> None:
    graph.bind("dcterms", DCTERMS)
    graph.bind("ev", EV)
    graph.bind("geo", GEO)
    graph.bind("prov", PROV)
    graph.bind("rdfs", RDFS)
    graph.bind("schema", SCHEMA)


def _point_wkt(longitude: float, latitude: float) -> Literal:
    return Literal(f"POINT ({longitude} {latitude})", datatype=GEO.wktLiteral)


def export_normalized_record(record: dict[str, object]) -> Graph:
    graph = Graph()
    _bind_namespaces(graph)

    source_id = str(record["source_id"])
    record_id = str(record["record_id"])
    entity = URIRef(build_entity_iri(source_id, record_id))
    source = URIRef(build_source_iri(source_id))

    family = FAMILY_CLASS_MAP.get(str(record.get("entity_family") or ""), EV.UrbanEntity)

    graph.add((entity, RDF.type, EV.UrbanEntity))
    if family != EV.UrbanEntity:
        graph.add((entity, RDF.type, family))
        graph.add((entity, EV.hasPrimaryFamily, family))

    label = record.get("preferred_label")
    if label:
        graph.add((entity, RDFS.label, Literal(str(label))))

    graph.add((entity, DCTERMS.identifier, Literal(record_id)))
    graph.add((entity, PROV.wasDerivedFrom, source))
    graph.add((entity, DCTERMS.source, source))

    description = record.get("description")
    if description:
        graph.add((entity, DCTERMS.description, Literal(str(description))))

    address = record.get("display_address")
    if address:
        graph.add((entity, SCHEMA.streetAddress, Literal(str(address))))

    longitude = record.get("longitude")
    latitude = record.get("latitude")
    if longitude is not None and latitude is not None:
        geometry = URIRef(build_geometry_iri(source_id, record_id))
        graph.add((entity, RDF.type, GEO.Feature))
        graph.add((entity, GEO.hasGeometry, geometry))
        graph.add((entity, GEO.hasDefaultGeometry, geometry))
        graph.add((geometry, RDF.type, GEO.Geometry))
        graph.add((geometry, GEO.asWKT, _point_wkt(float(longitude), float(latitude))))

    return graph


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def export_normalized_rows(rows: list[dict[str, object]]) -> Graph:
    graph = Graph()
    _bind_namespaces(graph)
    seen_record_ids: set[str] = set()
    for row in rows:
        record_id = str(row["record_id"])
        if record_id in seen_record_ids:
            raise ValueError(f"Duplicate record_id in normalized rows: {record_id}")
        seen_record_ids.add(record_id)
        graph += export_normalized_record(row)
    return graph

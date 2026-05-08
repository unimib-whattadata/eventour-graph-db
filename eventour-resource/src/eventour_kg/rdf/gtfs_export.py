"""Export GTFS structural entities to RDF."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, DCTERMS, URIRef

from eventour_kg.rdf.iris import (
    build_geometry_iri,
    build_gtfs_route_iri,
    build_gtfs_stop_iri,
    build_source_iri,
)
from eventour_kg.rdf.ontology import EV


PROV = Namespace("http://www.w3.org/ns/prov#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")


def _bind_namespaces(graph: Graph) -> None:
    graph.bind("dcterms", DCTERMS)
    graph.bind("ev", EV)
    graph.bind("geo", GEO)
    graph.bind("prov", PROV)
    graph.bind("rdfs", RDFS)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _point_wkt(longitude: float, latitude: float) -> Literal:
    return Literal(f"POINT ({longitude} {latitude})", datatype=GEO.wktLiteral)


def _linestring_wkt(points: list[tuple[float, float]]) -> Literal:
    joined = ", ".join(f"{lon} {lat}" for lat, lon in points)
    return Literal(f"LINESTRING ({joined})", datatype=GEO.wktLiteral)


def export_gtfs_structure_graph(gtfs_dir: Path) -> Graph:
    graph = Graph()
    _bind_namespaces(graph)

    source = URIRef(build_source_iri("gtfs"))
    stops = _read_csv(gtfs_dir / "stops.txt")
    routes = _read_csv(gtfs_dir / "routes.txt")
    trips = _read_csv(gtfs_dir / "trips.txt")
    stop_times = _read_csv(gtfs_dir / "stop_times.txt")
    shapes = _read_csv(gtfs_dir / "shapes.txt")

    stop_by_id = {row["stop_id"]: row for row in stops if row.get("stop_id")}
    trips_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for trip in trips:
        route_id = trip.get("route_id")
        if route_id:
            trips_by_route[route_id].append(trip)

    stop_times_by_trip: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in stop_times:
        trip_id = row.get("trip_id")
        if trip_id:
            stop_times_by_trip[trip_id].append(row)
    for rows in stop_times_by_trip.values():
        rows.sort(key=lambda row: int(row.get("stop_sequence") or 0))

    shape_points: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for row in shapes:
        shape_id = row.get("shape_id")
        if not shape_id:
            continue
        sequence = int(row.get("shape_pt_sequence") or 0)
        lat = float(row["shape_pt_lat"])
        lon = float(row["shape_pt_lon"])
        shape_points[shape_id].append((sequence, lat, lon))
    for points in shape_points.values():
        points.sort(key=lambda item: item[0])

    for row in stops:
        stop_id = row.get("stop_id")
        if not stop_id:
            continue
        stop = URIRef(build_gtfs_stop_iri(stop_id))
        graph.add((stop, RDF.type, EV.UrbanEntity))
        graph.add((stop, RDF.type, EV.MobilityNode))
        graph.add((stop, EV.hasPrimaryFamily, EV.MobilityNode))
        graph.add((stop, RDFS.label, Literal(row.get("stop_name") or stop_id)))
        graph.add((stop, DCTERMS.identifier, Literal(stop_id)))
        graph.add((stop, PROV.wasDerivedFrom, source))

        lat = row.get("stop_lat")
        lon = row.get("stop_lon")
        if lat and lon:
            geometry = URIRef(build_geometry_iri("gtfs-stop", stop_id))
            graph.add((stop, RDF.type, GEO.Feature))
            graph.add((stop, GEO.hasGeometry, geometry))
            graph.add((geometry, RDF.type, GEO.Geometry))
            graph.add((geometry, GEO.asWKT, _point_wkt(float(lon), float(lat))))

    for row in routes:
        route_id = row.get("route_id")
        if not route_id:
            continue
        route = URIRef(build_gtfs_route_iri(route_id))
        label = row.get("route_long_name") or row.get("route_short_name") or route_id
        graph.add((route, RDF.type, EV.UrbanEntity))
        graph.add((route, RDF.type, EV.MobilityRoute))
        graph.add((route, EV.hasPrimaryFamily, EV.MobilityRoute))
        graph.add((route, RDFS.label, Literal(label)))
        graph.add((route, DCTERMS.identifier, Literal(route_id)))
        if row.get("route_desc"):
            graph.add((route, DCTERMS.description, Literal(row["route_desc"])))
        graph.add((route, PROV.wasDerivedFrom, source))

        route_trips = trips_by_route.get(route_id, [])
        if route_trips:
            trip = route_trips[0]
            for stop_time in stop_times_by_trip.get(trip.get("trip_id") or "", []):
                stop_id = stop_time.get("stop_id")
                if stop_id and stop_id in stop_by_id:
                    graph.add((route, EV.hasStop, URIRef(build_gtfs_stop_iri(stop_id))))

            shape_id = trip.get("shape_id")
            if shape_id and shape_id in shape_points:
                ordered = shape_points[shape_id]
                geometry = URIRef(build_geometry_iri("gtfs-route", route_id))
                graph.add((route, RDF.type, GEO.Feature))
                graph.add((route, GEO.hasGeometry, geometry))
                graph.add((geometry, RDF.type, GEO.Geometry))
                graph.add((geometry, GEO.asWKT, _linestring_wkt([(lat, lon) for _, lat, lon in ordered])))

    return graph

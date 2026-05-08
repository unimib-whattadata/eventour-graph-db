"""Build small per-dataset RDF review samples from raw dataset files."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, RDFS, DCTERMS, SKOS, URIRef

from eventour_kg.config.loaders import load_city_profile
from eventour_kg.extraction.source_records import geojson_source_records
from eventour_kg.rdf.iris import build_category_iri, build_entity_iri, build_geometry_iri, build_source_iri
from eventour_kg.rdf.ontology import EV
from eventour_kg.rdf.serialize import serialize_graph


PROV = Namespace("http://www.w3.org/ns/prov#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
SCHEMA = Namespace("https://schema.org/")


FAMILY_TYPE_MAP = {
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
    "route_geometry": EV.MobilityRoute,
    "route_sequence": EV.UrbanEntity,
    "schedule_summary": EV.UrbanEntity,
}


@dataclass(frozen=True)
class SampleDatasetSummary:
    dataset_file: str
    source_id: str
    sample_count: int
    output_base: str


def _bind_namespaces(graph: Graph) -> None:
    graph.bind("dcterms", DCTERMS)
    graph.bind("ev", EV)
    graph.bind("geo", GEO)
    graph.bind("prov", PROV)
    graph.bind("rdfs", RDFS)
    graph.bind("schema", SCHEMA)
    graph.bind("skos", SKOS)


def _value(properties: dict[str, Any], key: str) -> str | None:
    value = properties.get(key)
    if value in (None, ""):
        return None
    return str(value)


def _join_text(*values: Any, sep: str = " | ") -> str | None:
    parts = [str(value).strip() for value in values if value not in (None, "", "None")]
    return sep.join(parts) if parts else None


def _format_point(coords: list[float]) -> str:
    return f"{coords[0]} {coords[1]}"


def _format_line(coords: list[list[float]]) -> str:
    return ", ".join(_format_point(point) for point in coords)


def geometry_to_wkt(geometry: dict[str, Any] | None) -> str | None:
    if not geometry:
        return None
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if geom_type == "Point" and isinstance(coords, list) and len(coords) >= 2:
        return f"POINT ({_format_point(coords)})"
    if geom_type == "LineString" and isinstance(coords, list):
        return f"LINESTRING ({_format_line(coords)})"
    if geom_type == "Polygon" and isinstance(coords, list):
        rings = ", ".join(f"({_format_line(ring)})" for ring in coords)
        return f"POLYGON ({rings})"
    if geom_type == "MultiPoint" and isinstance(coords, list):
        points = ", ".join(f"({_format_point(point)})" for point in coords)
        return f"MULTIPOINT ({points})"
    if geom_type == "MultiLineString" and isinstance(coords, list):
        lines = ", ".join(f"({_format_line(line)})" for line in coords)
        return f"MULTILINESTRING ({lines})"
    if geom_type == "MultiPolygon" and isinstance(coords, list):
        polygons = ", ".join(
            f"({', '.join(f'({_format_line(ring)})' for ring in polygon)})"
            for polygon in coords
        )
        return f"MULTIPOLYGON ({polygons})"
    return None


def _label_for_record(source_id: str, record: dict[str, Any]) -> str:
    properties = record.get("raw_properties", {})
    if source_id == "historic_shops":
        return _value(properties, "TARGA") or record["record_id"]
    if source_id == "nils":
        return _value(properties, "NIL") or record["record_id"]
    if source_id == "bikemi_stations":
        return _value(properties, "nome") or record["record_id"]
    if source_id == "tpl_metro_stops":
        return _value(properties, "nome") or record["record_id"]
    if source_id == "tpl_surface_stops":
        return _value(properties, "ubicazione") or record["record_id"]
    if source_id == "public_toilets":
        return _join_text("Public toilet", _value(properties, "VIA"), _value(properties, "LOCALITA"), sep=" - ") or record["record_id"]
    if source_id == "openwifi":
        return _value(properties, "AP") or record["record_id"]
    if source_id == "park_and_ride":
        return _value(properties, "Nome") or record["record_id"]
    if source_id == "public_parking":
        return _value(properties, "nome") or record["record_id"]
    if source_id == "charging_stations":
        return _join_text("Charging station", _value(properties, "localita"), sep=" - ") or record["record_id"]
    if source_id == "bike_parking":
        return _join_text("Bike parking", _value(properties, "via_nome"), _value(properties, "num_civico"), sep=" - ") or record["record_id"]
    if source_id == "vedovelle":
        return _join_text("Vedovella", _value(properties, "NIL"), _value(properties, "objectID"), sep=" - ") or record["record_id"]
    if source_id == "benches":
        return _join_text("Bench", _value(properties, "località"), sep=" - ") or record["record_id"]
    if source_id == "picnic_tables":
        return _join_text("Picnic table", _value(properties, "località"), sep=" - ") or record["record_id"]
    if source_id == "trees":
        return _join_text("Tree", _value(properties, "obj_id"), _join_text(_value(properties, "genere"), _value(properties, "specie"), sep=" "), sep=" - ") or record["record_id"]
    if source_id == "area_b_gates":
        return _value(properties, "nome") or record["record_id"]
    if source_id == "area_c_gates":
        return _join_text("Area C gate", _value(properties, "label"), sep=" - ") or record["record_id"]
    if source_id == "tpl_metro_routes":
        return _join_text("Metro line", _value(properties, "linea"), _value(properties, "nome"), sep=" - ") or record["record_id"]
    if source_id == "tpl_surface_routes":
        return _join_text(_value(properties, "mezzo"), _value(properties, "linea"), _value(properties, "nome"), sep=" - ") or record["record_id"]
    if source_id == "tpl_metro_route_sequences":
        return _join_text("Metro route sequence", _value(properties, "percorso"), _value(properties, "id_ferm"), sep=" - ") or record["record_id"]
    if source_id == "tpl_surface_route_sequences":
        return _join_text("Route sequence", _value(properties, "percorso"), _value(properties, "id_ferm"), sep=" - ") or record["record_id"]
    if source_id == "tpl_metro_schedules":
        return _join_text("Metro schedule", _value(properties, "linea"), _value(properties, "percorso"), _value(properties, "tipo_giorno"), sep=" - ") or record["record_id"]
    if source_id == "tpl_surface_schedules":
        return _join_text(_value(properties, "mezzo"), "schedule", _value(properties, "linea"), _value(properties, "percorso"), _value(properties, "tipo_giorno"), sep=" - ") or record["record_id"]
    return record["record_id"]


def _description_for_record(source_id: str, record: dict[str, Any]) -> str | None:
    properties = record.get("raw_properties", {})
    if source_id == "historic_shops":
        return _join_text(_value(properties, "GENERE MERCEOLOGICO"), _value(properties, "STATO"), _value(properties, "ANNO"))
    if source_id == "nils":
        return _join_text(_value(properties, "ID_NIL"), _value(properties, "Valido_dal"), _value(properties, "Valido_al"))
    if source_id == "bikemi_stations":
        return _join_text(_value(properties, "tipo"), _value(properties, "stalli"), _value(properties, "stato"))
    if source_id in {"tpl_metro_stops", "tpl_surface_stops"}:
        return _join_text(_value(properties, "linee"), _value(properties, "id_amat"))
    if source_id == "public_toilets":
        return _join_text(_value(properties, "TIPO"), _value(properties, "DISPONIBILITA"), _value(properties, "ULTERIORI_INFO"))
    if source_id == "openwifi":
        return _join_text(_value(properties, "MUNICIPIO"), _value(properties, "NIL"), _value(properties, "CAP"))
    if source_id == "park_and_ride":
        return _join_text(_value(properties, "TAB1"), _value(properties, "INFO"))
    if source_id == "public_parking":
        return _join_text(_value(properties, "tipo"), _value(properties, "n_posti"), _value(properties, "comune"))
    if source_id == "charging_stations":
        return _join_text(_value(properties, "titolare"), _value(properties, "numero_pdr"), _value(properties, "infra"), _value(properties, "tipologia"))
    if source_id == "bike_parking":
        return _join_text(_value(properties, "veicoli"), _value(properties, "stalli_totali"), _value(properties, "tipo_man"), _value(properties, "stato"))
    if source_id in {"vedovelle", "benches", "picnic_tables"}:
        return _join_text(_value(properties, "descrizione_codice"), _value(properties, "municipio"), _value(properties, "data_ini"))
    if source_id == "trees":
        return _join_text(_value(properties, "codice"), _value(properties, "diam_tronc"), _value(properties, "diam_chiom"), _value(properties, "h_m"), _value(properties, "municipio"))
    if source_id == "area_b_gates":
        return _join_text(_value(properties, "stato"), _value(properties, "autorizzaz"))
    if source_id == "area_c_gates":
        return _join_text(_value(properties, "id_amat"))
    if source_id in {"tpl_metro_routes", "tpl_surface_routes"}:
        return _join_text(_value(properties, "percorso"), _value(properties, "num_ferm"), _value(properties, "lung_km"), _value(properties, "verso"), _value(properties, "tipo_perc"))
    if source_id in {"tpl_metro_route_sequences", "tpl_surface_route_sequences"}:
        return _join_text(_value(properties, "num"), _value(properties, "id_ferm"), _value(properties, "percorso"))
    if source_id in {"tpl_metro_schedules", "tpl_surface_schedules"}:
        return _join_text(
            _value(properties, "orario"),
            _join_text(_value(properties, "inizio"), _value(properties, "fine"), sep=" -> "),
            _join_text("daily", _value(properties, "corse_gior"), sep=" "),
            _join_text("peak", _value(properties, "corse_punt"), sep=" "),
            _join_text("offpeak", _value(properties, "corse_morb"), sep=" "),
            _join_text("evening", _value(properties, "corse_sera"), sep=" "),
        )
    return None


def _address_for_record(source_id: str, record: dict[str, Any]) -> str | None:
    properties = record.get("raw_properties", {})
    if source_id == "historic_shops":
        return _value(properties, "INDIRIZZO")
    if source_id == "tpl_surface_stops":
        return _value(properties, "ubicazione")
    if source_id == "public_toilets":
        return _join_text(_value(properties, "VIA"), _value(properties, "LOCALITA"), sep=" ")
    if source_id == "openwifi":
        return _value(properties, "indirizzo")
    if source_id == "park_and_ride":
        return _value(properties, "indirizzo")
    if source_id == "public_parking":
        return _value(properties, "indirizzo")
    if source_id == "charging_stations":
        return _value(properties, "localita")
    if source_id == "bike_parking":
        return _join_text(_value(properties, "via_nome"), _value(properties, "num_civico"), sep=" ")
    if source_id in {"benches", "picnic_tables"}:
        return _value(properties, "località")
    return None


def export_review_sample_for_records(
    *,
    source_id: str,
    dataset_label: str,
    entity_family: str,
    records: list[dict[str, Any]],
    sample_size: int = 10,
) -> tuple[Graph, list[dict[str, Any]]]:
    graph = Graph()
    _bind_namespaces(graph)

    source = URIRef(build_source_iri(source_id))
    rdf_type = FAMILY_TYPE_MAP.get(entity_family, EV.UrbanEntity)
    sample_records = records[:sample_size]
    seen_subjects: set[str] = set()
    summary: list[dict[str, Any]] = []

    for record in sample_records:
        record_id = str(record["record_id"])
        subject_iri = build_entity_iri(source_id, record_id)
        if subject_iri in seen_subjects:
            raise ValueError(f"Duplicate review sample subject for {source_id}: {record_id}")
        seen_subjects.add(subject_iri)

        entity = URIRef(subject_iri)
        label = _label_for_record(source_id, record)
        description = _description_for_record(source_id, record)
        address = _address_for_record(source_id, record)

        graph.add((entity, RDF.type, EV.UrbanEntity))
        if rdf_type != EV.UrbanEntity:
            graph.add((entity, RDF.type, rdf_type))
            graph.add((entity, EV.hasPrimaryFamily, rdf_type))

        graph.add((entity, RDFS.label, Literal(label)))
        graph.add((entity, DCTERMS.identifier, Literal(record_id)))
        graph.add((entity, PROV.wasDerivedFrom, source))
        graph.add((entity, DCTERMS.source, source))
        if description:
            graph.add((entity, DCTERMS.description, Literal(description)))
        if address:
            graph.add((entity, SCHEMA.streetAddress, Literal(address)))

        geometry = record.get("raw_geometry")
        wkt = geometry_to_wkt(geometry)
        if wkt:
            geometry_iri = URIRef(build_geometry_iri(source_id, record_id))
            graph.add((entity, RDF.type, GEO.Feature))
            graph.add((entity, GEO.hasGeometry, geometry_iri))
            graph.add((geometry_iri, RDF.type, GEO.Geometry))
            graph.add((geometry_iri, GEO.asWKT, Literal(wkt, datatype=GEO.wktLiteral)))

        summary.append(
            {
                "record_id": record_id,
                "external_id": record.get("external_id"),
                "subject_iri": subject_iri,
                "label": label,
                "description": description,
                "address": address,
                "geometry_type": None if not geometry else geometry.get("type"),
                "dataset_label": dataset_label,
            }
        )

    return graph, summary


def export_open_meteo_review_sample(
    payload: dict[str, Any],
    *,
    sample_size: int = 10,
) -> tuple[Graph, list[dict[str, Any]]]:
    graph = Graph()
    _bind_namespaces(graph)

    source = URIRef(build_source_iri("open_meteo_descriptions"))
    scheme = URIRef(build_category_iri("open-meteo-description-scheme"))
    graph.add((scheme, RDF.type, SKOS.ConceptScheme))
    graph.add((scheme, SKOS.prefLabel, Literal("Open Meteo description scheme", lang="en")))

    summary: list[dict[str, Any]] = []
    keys = sorted(payload.keys(), key=lambda value: int(value) if str(value).isdigit() else str(value))
    for code in keys[:sample_size]:
        entry = payload[code]
        concept_iri = build_category_iri(f"open-meteo-description-{code}")
        concept = URIRef(concept_iri)
        label = f"Weather code {code}"
        description = _join_text(
            _join_text("day", entry.get("day", {}).get("description"), sep=": "),
            _join_text("night", entry.get("night", {}).get("description"), sep=": "),
        )

        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.inScheme, scheme))
        graph.add((concept, SKOS.prefLabel, Literal(label, lang="en")))
        graph.add((concept, DCTERMS.identifier, Literal(str(code))))
        graph.add((concept, PROV.wasDerivedFrom, source))
        graph.add((concept, DCTERMS.source, source))
        if description:
            graph.add((concept, DCTERMS.description, Literal(description)))

        summary.append(
            {
                "record_id": str(code),
                "subject_iri": concept_iri,
                "label": label,
                "description": description,
                "dataset_label": "Open meteo descriptions",
            }
        )

    return graph, summary


def _write_graph_pair(graph: Graph, base_path: Path) -> None:
    serialize_graph(graph, base_path.with_suffix(".ttl"), format="turtle")
    serialize_graph(graph, base_path.with_suffix(".jsonld"), format="json-ld")


def build_dataset_review_samples(
    *,
    city_id: str,
    datasets_dir: Path,
    out_dir: Path,
    sample_size: int = 10,
) -> dict[str, Any]:
    profile = load_city_profile(city_id)
    source_by_path = {
        source.path.resolve(): source
        for source in profile.sources
        if source.path.parent.resolve() == datasets_dir.resolve()
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []

    for dataset_path in sorted(path for path in datasets_dir.iterdir() if path.is_file() and path.name != ".DS_Store"):
        source = source_by_path.get(dataset_path.resolve())
        if source is None:
            continue

        output_base = out_dir / dataset_path.stem
        if dataset_path.suffix == ".geojson":
            records = geojson_source_records(city_id, source.source_id)
            graph, summary = export_review_sample_for_records(
                source_id=source.source_id,
                dataset_label=source.label,
                entity_family=source.entity_family,
                records=records,
                sample_size=sample_size,
            )
        elif dataset_path.name == "open-meteo-descriptions.json":
            payload = json.loads(dataset_path.read_text(encoding="utf-8"))
            graph, summary = export_open_meteo_review_sample(payload, sample_size=sample_size)
        else:
            continue

        _write_graph_pair(graph, output_base)
        summary_path = output_base.with_suffix(".sample.json")
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

        summaries.append(
            SampleDatasetSummary(
                dataset_file=dataset_path.name,
                source_id=source.source_id,
                sample_count=len(summary),
                output_base=str(output_base),
            ).__dict__
        )

    index_path = out_dir / "index.json"
    index_path.write_text(json.dumps({"datasets": summaries}, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"dataset_count": len(summaries), "sample_size": sample_size, "index_path": str(index_path)}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build 10-instance RDF review samples for each dataset file.")
    parser.add_argument("--city-id", default="milan")
    parser.add_argument("--datasets-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--sample-size", type=int, default=10)
    args = parser.parse_args()

    summary = build_dataset_review_samples(
        city_id=args.city_id,
        datasets_dir=Path(args.datasets_dir),
        out_dir=Path(args.out_dir),
        sample_size=args.sample_size,
    )
    print(summary)


if __name__ == "__main__":
    main()

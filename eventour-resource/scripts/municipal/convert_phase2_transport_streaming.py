#!/usr/bin/env python3
"""Streaming Phase-2 Eventour transport RDF converter.

This converter creates the GTFS-like Eventour transport model:

- evt:TransitLine
- evt:Stop
- evt:MetroStation
- evt:RoutePattern
- evt:StopInRoute
- evt:ServicePattern
- evt:TimetableSummary

It streams N-Triples directly to disk, like the Phase-1 streaming converter.

Run from the project root:

    $CONDA_PREFIX/bin/python scripts/convert_phase2_transport_streaming.py \
      --datasets datasets \
      --mapping mappings/phase2_transport_mappings.yaml \
      --output output/eventour_phase2_transport_data.nt

The script uses robust field aliases because Comune transport datasets often vary
field capitalization or naming between metro/surface files.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any, Iterable, TextIO

import fiona
import yaml
from shapely.geometry import shape
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

EVT = Namespace("http://eventour.unimib.it/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
ORG = Namespace("http://www.w3.org/ns/org#")

PREFIXES = {
    "evt": EVT,
    "geo": GEO,
    "prov": PROV,
    "dcat": DCAT,
    "skos": SKOS,
    "org": ORG,
    "dct": DCTERMS,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
}

ALIASES = {
    "stop_id": ["id_amat", "ID_AMAT", "id_ferm", "ID_FERM", "id_fermata", "ID_FERMATA", "id", "ID"],
    "stop_label": ["ubicazione", "UBICAZIONE", "localita", "località", "LOCALITA", "nome", "NOME", "descrizione", "DESCRIZIONE", "fermata", "FERMATA"],
    "lines": ["linee", "LINEE", "Linee", "linea", "LINEA", "Linea"],
    "line": ["linea", "LINEA", "Linea", "linee", "LINEE", "Linee"],
    "mode": ["mezzo", "MEZZO", "Mezzo"],
    "route_pattern": ["percorso", "PERCORSO", "Percorso"],
    "route_direction": ["verso", "VERSO", "direzione", "DIREZIONE"],
    "route_length": ["lunghezza", "LUNGHEZZA", "lung_km", "LUNG_KM", "lunghezza_km", "LUNGHEZZA_KM", "km", "KM"],
    "route_stop_count": ["num_ferm", "NUM_FERM", "n_ferm", "N_FERM", "fermate", "FERMATE"],
    "sequence_number": ["num", "NUM", "sequenza", "SEQUENZA", "ordine", "ORDINE"],
    "sequence_stop_id": ["id_ferm", "ID_FERM", "id_fermata", "ID_FERMATA", "id_amat", "ID_AMAT"],
    "schedule_code": ["orario", "ORARIO", "Orario"],
    "day_type": ["tipo_giorno", "TIPO_GIORNO", "Tipo_giorno"],
    "start_time": ["inizio", "INIZIO", "inizio_servizio", "INIZIO_SERVIZIO"],
    "end_time": ["fine", "FINE", "fine_servizio", "FINE_SERVIZIO"],
    "daily_trips": ["corse_gior", "CORSE_GIOR", "corse_giorno", "CORSE_GIORNO"],
    "peak_trips": ["corse_punt", "CORSE_PUNT"],
    "offpeak_trips": ["corse_morb", "CORSE_MORB"],
    "evening_trips": ["corse_sera", "CORSE_SERA"],
}

MODE_CODE_MAP = {
    "METRO": "metro",
    "M": "metro",
    "MM": "metro",
    "BUS": "bus",
    "AUTOBUS": "bus",
    "TRAM": "tram",
    "TRANVIA": "tram",
    "FILOBUS": "trolleybus",
    "TROLLEYBUS": "trolleybus",
}


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if isinstance(value, float) and math.isnan(value):
            return True
    except TypeError:
        pass
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "null", "nat"}


def clean_text(value: Any) -> str:
    return "" if is_missing(value) else str(value).strip()


def safe_token(value: Any) -> str:
    text = clean_text(value)
    text = text.replace("/", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^A-Za-z0-9._~:-]+", "-", text)
    return text.strip("-")


def evt_uri(path: str) -> URIRef:
    return URIRef(str(EVT) + path.lstrip("/"))


def write_triple(out: TextIO, s: URIRef, p: URIRef, o: URIRef | Literal) -> None:
    out.write(f"{s.n3()} {p.n3()} {o.n3()} .\n")


def first_value(props: dict[str, Any], key: str) -> Any | None:
    for alias in ALIASES[key]:
        if alias in props and not is_missing(props[alias]):
            return props[alias]
    return None


def first_field_name(props: dict[str, Any], key: str) -> str | None:
    for alias in ALIASES[key]:
        if alias in props and not is_missing(props[alias]):
            return alias
    return None


def split_values(value: Any) -> list[str]:
    if is_missing(value):
        return []
    text = str(value).strip()
    # Split common separators but keep metro labels like M1 intact.
    parts = re.split(r"[,;/|]+|\s{2,}", text)
    if len(parts) == 1:
        # Some line fields are space-separated, e.g. "1 14 19".
        # Avoid splitting labels with ordinary words.
        if re.fullmatch(r"[A-Za-z0-9 ]+", text) and len(text.split()) > 1:
            return [p for p in text.split() if p]
    return [p.strip() for p in parts if p.strip()]


def normalize_mode(value: Any, fallback_scope: str = "surface") -> str:
    text = clean_text(value).upper()
    text = text.replace(".", "").replace("-", "").strip()

    if text in MODE_CODE_MAP:
        return MODE_CODE_MAP[text]

    if text.startswith("M") and re.fullmatch(r"M\d+", text):
        return "metro"

    if fallback_scope == "metro":
        return "metro"

    return fallback_scope or "surface"


def normalize_line_token(line_value: Any, mode_scope: str) -> str:
    text = clean_text(line_value).upper().replace("LINEA", "").strip()
    text = text.replace("MM", "M")
    # M2 -> 2 for URI transit-line/metro/2
    if mode_scope == "metro":
        match = re.search(r"M?(\d+)", text)
        if match:
            return match.group(1)
    return safe_token(text)


def transit_line_uri(line_value: Any, mode_scope: str) -> URIRef:
    line_token = normalize_line_token(line_value, mode_scope)
    return evt_uri(f"transit-line/{mode_scope}/{line_token}")


def add_transit_line(out: TextIO, line_value: Any, mode_scope: str) -> URIRef:
    line_uri = transit_line_uri(line_value, mode_scope)
    line_token = normalize_line_token(line_value, mode_scope)

    write_triple(out, line_uri, RDF.type, EVT.TransitLine)
    write_triple(out, line_uri, RDF.type, EVT.TransportEntity)
    write_triple(out, line_uri, DCTERMS.identifier, Literal(line_token))
    write_triple(out, line_uri, RDFS.label, Literal(f"{mode_scope} line {line_token}", lang="en"))
    write_triple(out, line_uri, EVT.transportMode, evt_uri(f"transport-mode/{mode_scope}"))
    return line_uri


def direction_concept(value: Any) -> URIRef | None:
    if is_missing(value):
        return None
    text = clean_text(value).lower()
    if text in {"as", "asc", "ascendente"}:
        return evt_uri("route-direction/as")
    if text in {"di", "disc", "discendente"}:
        return evt_uri("route-direction/di")
    return evt_uri(f"route-direction/{safe_token(text)}")


def day_type_concept(value: Any) -> URIRef | None:
    if is_missing(value):
        return None
    text = clean_text(value).upper()
    if text in {"L", "LAVORATIVO"}:
        return evt_uri("day-type/L")
    if text in {"S", "SABATO"}:
        return evt_uri("day-type/S")
    if text in {"F", "FESTIVO"}:
        return evt_uri("day-type/F")
    return evt_uri(f"day-type/{safe_token(text)}")


def as_decimal_literal(value: Any) -> Literal | None:
    if is_missing(value):
        return None
    text = clean_text(value).replace(",", ".")
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return None
    return Literal(match.group(0), datatype=XSD.decimal)


def as_integer_literal(value: Any) -> Literal | None:
    if is_missing(value):
        return None
    text = clean_text(value)
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    return Literal(match.group(0), datatype=XSD.integer)


def normalize_time(value: Any) -> str | None:
    if is_missing(value):
        return None
    text = clean_text(value)
    # Accept HH:MM or HH:MM:SS. Some feeds use 24+ GTFS-like hours; xsd:time cannot.
    match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3) or "0")
    if hour > 23 or minute > 59 or second > 59:
        return None
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def add_geometry(out: TextIO, entity_uri: URIRef, geometry_dict: Any, crs_uri: str) -> None:
    if geometry_dict is None:
        return
    geom = shape(geometry_dict)
    if geom.is_empty:
        return

    geom_uri = URIRef(str(entity_uri) + "/geometry")
    write_triple(out, entity_uri, GEO.hasGeometry, geom_uri)
    write_triple(out, entity_uri, GEO.hasDefaultGeometry, geom_uri)
    write_triple(out, geom_uri, RDF.type, GEO.Geometry)
    write_triple(out, geom_uri, GEO.asWKT, Literal(f"<{crs_uri}> {geom.wkt}", datatype=GEO.wktLiteral))


def add_dataset_metadata(out: TextIO, dataset_name: str, dataset_uri: URIRef, defaults: dict[str, Any]) -> None:
    write_triple(out, dataset_uri, RDF.type, DCAT.Dataset)
    write_triple(out, dataset_uri, RDFS.label, Literal(dataset_name, lang="en"))

    publisher_uri = URIRef(defaults["publisher_uri"])
    write_triple(out, dataset_uri, DCTERMS.publisher, publisher_uri)
    write_triple(out, publisher_uri, RDF.type, ORG.Organization)
    write_triple(out, publisher_uri, RDFS.label, Literal("Comune di Milano", lang="it"))

    place_uri = evt_uri("place/milano")
    write_triple(out, dataset_uri, DCTERMS.spatial, place_uri)
    write_triple(out, place_uri, RDFS.label, Literal("Milano", lang="it"))


def add_transform_activity(out: TextIO, dataset_name: str, dataset_uri: URIRef, activity_uri: URIRef, defaults: dict[str, Any]) -> None:
    agent_uri = URIRef(defaults["pipeline_agent_uri"])
    write_triple(out, agent_uri, RDF.type, PROV.Agent)
    write_triple(out, agent_uri, RDFS.label, Literal("Eventour RDF conversion pipeline", lang="en"))
    write_triple(out, activity_uri, RDF.type, PROV.Activity)
    write_triple(out, activity_uri, RDFS.label, Literal(f"Transform {dataset_name} dataset to RDF", lang="en"))
    write_triple(out, activity_uri, PROV.used, dataset_uri)
    write_triple(out, activity_uri, PROV.wasAssociatedWith, agent_uri)


def add_source_record(out: TextIO, entity_uri: URIRef, dataset_name: str, dataset_uri: URIRef, record_key: str, id_field: str | None = None) -> None:
    record_uri = evt_uri(f"source-record/{dataset_name}/{safe_token(record_key)}")
    write_triple(out, entity_uri, DCTERMS.source, dataset_uri)
    write_triple(out, entity_uri, PROV.wasDerivedFrom, record_uri)
    write_triple(out, record_uri, RDF.type, EVT.SourceRecord)
    write_triple(out, record_uri, DCTERMS.isPartOf, dataset_uri)
    write_triple(out, record_uri, EVT.sourceIdentifierField, Literal(id_field or "derived-key"))
    write_triple(out, record_uri, EVT.sourceIdentifierValue, Literal(record_key))


def add_common_generation(out: TextIO, entity_uri: URIRef, dataset_name: str, dataset_uri: URIRef, activity_uri: URIRef, record_key: str, id_field: str | None) -> None:
    add_source_record(out, entity_uri, dataset_name, dataset_uri, record_key, id_field)
    write_triple(out, entity_uri, PROV.wasGeneratedBy, activity_uri)
    write_triple(out, activity_uri, PROV.generated, entity_uri)


def convert_stops(out: TextIO, dataset_name: str, cfg: dict[str, Any], path: Path, defaults: dict[str, Any]) -> int:
    dataset_uri = evt_uri(cfg["dataset_uri"])
    activity_uri = evt_uri(cfg["transform_activity_uri"])
    stop_scope = cfg.get("stop_scope", "surface")
    count = 0

    with fiona.open(path) as src:
        for feature in src:
            props = dict(feature["properties"])
            stop_id = first_value(props, "stop_id")
            if is_missing(stop_id):
                continue

            stop_uri = evt_uri(f"stop/{stop_scope}/{safe_token(stop_id)}")
            write_triple(out, stop_uri, RDF.type, EVT.Stop)
            write_triple(out, stop_uri, RDF.type, EVT.Facility)
            write_triple(out, stop_uri, RDF.type, EVT.ServiceAccessPoint)
            write_triple(out, stop_uri, RDF.type, GEO.Feature)
            if stop_scope == "metro":
                write_triple(out, stop_uri, RDF.type, EVT.MetroStation)

            write_triple(out, stop_uri, DCTERMS.identifier, Literal(str(stop_id)))

            label = first_value(props, "stop_label")
            if not is_missing(label):
                write_triple(out, stop_uri, RDFS.label, Literal(clean_text(label), lang=defaults.get("language", "it")))

            add_geometry(out, stop_uri, feature["geometry"], defaults["crs_uri"])

            lines_raw = first_value(props, "lines")
            for line in split_values(lines_raw):
                mode = "metro" if stop_scope == "metro" else "surface"
                line_uri = add_transit_line(out, line, mode)
                write_triple(out, stop_uri, EVT.servedByLine, line_uri)

            id_field = first_field_name(props, "stop_id")
            add_common_generation(out, stop_uri, dataset_name, dataset_uri, activity_uri, str(stop_id), id_field)
            count += 1

    return count


def convert_routes(out: TextIO, dataset_name: str, cfg: dict[str, Any], path: Path, defaults: dict[str, Any]) -> int:
    dataset_uri = evt_uri(cfg["dataset_uri"])
    activity_uri = evt_uri(cfg["transform_activity_uri"])
    fallback_scope = cfg.get("route_scope", "surface")
    count = 0

    with fiona.open(path) as src:
        for feature in src:
            props = dict(feature["properties"])
            route_id = first_value(props, "route_pattern")
            if is_missing(route_id):
                continue

            mode = normalize_mode(first_value(props, "mode"), fallback_scope)
            route_uri = evt_uri(f"route-pattern/{mode}/{safe_token(route_id)}")

            write_triple(out, route_uri, RDF.type, EVT.RoutePattern)
            write_triple(out, route_uri, RDF.type, EVT.TransportEntity)
            write_triple(out, route_uri, RDF.type, GEO.Feature)
            write_triple(out, route_uri, DCTERMS.identifier, Literal(str(route_id)))
            write_triple(out, route_uri, RDFS.label, Literal(f"Route pattern {route_id}", lang="en"))
            write_triple(out, route_uri, EVT.transportMode, evt_uri(f"transport-mode/{mode}"))

            line_value = first_value(props, "line")
            if not is_missing(line_value):
                line_uri = add_transit_line(out, line_value, mode)
                write_triple(out, route_uri, EVT.forTransitLine, line_uri)

            direction = direction_concept(first_value(props, "route_direction"))
            if direction is not None:
                write_triple(out, route_uri, EVT.routeDirection, direction)

            length_lit = as_decimal_literal(first_value(props, "route_length"))
            if length_lit is not None:
                write_triple(out, route_uri, EVT.routeLengthKm, length_lit)

            stop_count_lit = as_integer_literal(first_value(props, "route_stop_count"))
            if stop_count_lit is not None:
                write_triple(out, route_uri, EVT.numberOfStops, stop_count_lit)

            add_geometry(out, route_uri, feature["geometry"], defaults["crs_uri"])

            id_field = first_field_name(props, "route_pattern")
            add_common_generation(out, route_uri, dataset_name, dataset_uri, activity_uri, str(route_id), id_field)
            count += 1

    return count


def convert_sequences(out: TextIO, dataset_name: str, cfg: dict[str, Any], path: Path, defaults: dict[str, Any]) -> int:
    dataset_uri = evt_uri(cfg["dataset_uri"])
    activity_uri = evt_uri(cfg["transform_activity_uri"])
    route_scope = cfg.get("route_scope", "surface")
    stop_scope = cfg.get("stop_scope", route_scope)
    count = 0

    with fiona.open(path) as src:
        for feature in src:
            props = dict(feature["properties"])
            route_id = first_value(props, "route_pattern")
            seq_num = first_value(props, "sequence_number")
            stop_id = first_value(props, "sequence_stop_id")

            if is_missing(route_id) or is_missing(seq_num) or is_missing(stop_id):
                continue

            entity_uri = evt_uri(f"stop-in-route/{route_scope}/{safe_token(route_id)}/{safe_token(seq_num)}")
            route_uri = evt_uri(f"route-pattern/{route_scope}/{safe_token(route_id)}")
            stop_uri = evt_uri(f"stop/{stop_scope}/{safe_token(stop_id)}")

            write_triple(out, entity_uri, RDF.type, EVT.StopInRoute)
            write_triple(out, entity_uri, RDF.type, EVT.TransportEntity)
            write_triple(out, entity_uri, EVT.forRoutePattern, route_uri)
            write_triple(out, entity_uri, EVT.stop, stop_uri)
            write_triple(out, route_uri, EVT.hasStopInRoute, entity_uri)

            seq_lit = as_integer_literal(seq_num)
            if seq_lit is not None:
                write_triple(out, entity_uri, EVT.sequenceNumber, seq_lit)
            else:
                write_triple(out, entity_uri, EVT.sourceSequenceNumber, Literal(clean_text(seq_num)))

            record_key = f"{route_id}-{seq_num}-{stop_id}"
            add_common_generation(out, entity_uri, dataset_name, dataset_uri, activity_uri, record_key, "percorso-num-id_ferm")
            count += 1

    return count


def convert_timetables(out: TextIO, dataset_name: str, cfg: dict[str, Any], path: Path, defaults: dict[str, Any]) -> int:
    dataset_uri = evt_uri(cfg["dataset_uri"])
    activity_uri = evt_uri(cfg["transform_activity_uri"])
    fallback_scope = cfg.get("route_scope", "surface")
    count = 0

    with fiona.open(path) as src:
        for feature in src:
            props = dict(feature["properties"])
            route_id = first_value(props, "route_pattern")
            if is_missing(route_id):
                continue

            mode = normalize_mode(first_value(props, "mode"), fallback_scope)
            day_raw = first_value(props, "day_type")
            schedule_raw = first_value(props, "schedule_code") or "default"

            day_token = safe_token(day_raw or "unknown")
            schedule_token = safe_token(schedule_raw)

            entity_uri = evt_uri(f"timetable-summary/{mode}/{safe_token(route_id)}/{day_token}/{schedule_token}")
            route_uri = evt_uri(f"route-pattern/{mode}/{safe_token(route_id)}")
            service_uri = evt_uri(f"service-pattern/{schedule_token}/{day_token}")

            write_triple(out, entity_uri, RDF.type, EVT.TimetableSummary)
            write_triple(out, entity_uri, RDF.type, EVT.TransportEntity)
            write_triple(out, entity_uri, EVT.forRoutePattern, route_uri)
            write_triple(out, entity_uri, EVT.servicePattern, service_uri)

            write_triple(out, service_uri, RDF.type, EVT.ServicePattern)
            write_triple(out, service_uri, RDF.type, EVT.TransportEntity)
            write_triple(out, service_uri, DCTERMS.identifier, Literal(f"{schedule_token}/{day_token}"))

            day_uri = day_type_concept(day_raw)
            if day_uri is not None:
                write_triple(out, entity_uri, EVT.dayType, day_uri)
                write_triple(out, service_uri, EVT.dayType, day_uri)

            start = normalize_time(first_value(props, "start_time"))
            if start is not None:
                write_triple(out, entity_uri, EVT.startTime, Literal(start, datatype=XSD.time))
            else:
                raw = first_value(props, "start_time")
                if not is_missing(raw):
                    write_triple(out, entity_uri, EVT.sourceStartTime, Literal(clean_text(raw)))

            end = normalize_time(first_value(props, "end_time"))
            if end is not None:
                write_triple(out, entity_uri, EVT.endTime, Literal(end, datatype=XSD.time))
            else:
                raw = first_value(props, "end_time")
                if not is_missing(raw):
                    write_triple(out, entity_uri, EVT.sourceEndTime, Literal(clean_text(raw)))

            for key, pred in [
                ("daily_trips", EVT.dailyTrips),
                ("peak_trips", EVT.peakTrips),
                ("offpeak_trips", EVT.offPeakTrips),
                ("evening_trips", EVT.eveningTrips),
            ]:
                lit = as_integer_literal(first_value(props, key))
                if lit is not None:
                    write_triple(out, entity_uri, pred, lit)

            line_value = first_value(props, "line")
            if not is_missing(line_value):
                line_uri = add_transit_line(out, line_value, mode)
                write_triple(out, route_uri, EVT.forTransitLine, line_uri)

            record_key = f"{route_id}-{day_token}-{schedule_token}"
            add_common_generation(out, entity_uri, dataset_name, dataset_uri, activity_uri, record_key, "percorso-tipo_giorno-orario")
            count += 1

    return count


def convert_one_dataset(out: TextIO, dataset_name: str, cfg: dict[str, Any], datasets_dir: Path, defaults: dict[str, Any]) -> int:
    path = datasets_dir / cfg["file"]
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    dataset_uri = evt_uri(cfg["dataset_uri"])
    activity_uri = evt_uri(cfg["transform_activity_uri"])
    add_dataset_metadata(out, dataset_name, dataset_uri, defaults)
    add_transform_activity(out, dataset_name, dataset_uri, activity_uri, defaults)

    kind = cfg["kind"]
    if kind == "stops":
        return convert_stops(out, dataset_name, cfg, path, defaults)
    if kind == "routes":
        return convert_routes(out, dataset_name, cfg, path, defaults)
    if kind == "sequences":
        return convert_sequences(out, dataset_name, cfg, path, defaults)
    if kind == "timetables":
        return convert_timetables(out, dataset_name, cfg, path, defaults)

    raise ValueError(f"Unsupported dataset kind: {kind}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    datasets_dir = Path(args.datasets)
    mapping_path = Path(args.mapping)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    defaults = config["defaults"]

    total = 0
    with output_path.open("w", encoding="utf-8") as out:
        for dataset_name, cfg in config["datasets"].items():
            count = convert_one_dataset(out, dataset_name, cfg, datasets_dir, defaults)
            print(f"{dataset_name}: {count} entities", flush=True)
            total += count

    print(f"Generated {total} transport entities")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

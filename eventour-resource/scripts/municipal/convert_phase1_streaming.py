#!/usr/bin/env python3
"""Streaming Phase-1 Eventour RDF converter.

This script replaces the first in-memory RDFlib converter for large datasets.
It streams triples directly to N-Triples, so it avoids building one huge Graph
and avoids slow Turtle serialization.

Usage:
    $CONDA_PREFIX/bin/python scripts/convert_phase1_streaming.py \
      --datasets datasets \
      --mapping mappings/phase1_mappings.yaml \
      --output output/eventour_phase1_data.nt
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any, TextIO

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
LOCN = Namespace("http://www.w3.org/ns/locn#")
SCHEMA = Namespace("https://schema.org/")
ORG = Namespace("http://www.w3.org/ns/org#")

PREFIXES = {
    "evt": EVT,
    "geo": GEO,
    "prov": PROV,
    "dcat": DCAT,
    "skos": SKOS,
    "locn": LOCN,
    "schema": SCHEMA,
    "org": ORG,
    "dct": DCTERMS,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
}

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def safe_token(value: Any) -> str:
    text = "" if is_missing(value) else str(value).strip()
    text = text.replace("/", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^A-Za-z0-9._~:-]+", "-", text)
    return text.strip("-")


def evt_uri(path: str) -> URIRef:
    return URIRef(str(EVT) + path.lstrip("/"))


def expand_curie(curie: str) -> URIRef:
    prefix, local = curie.split(":", 1)
    if prefix not in PREFIXES:
        raise ValueError(f"Unknown prefix in CURIE: {curie}")
    return URIRef(str(PREFIXES[prefix]) + local)


def datatype_uri(datatype: str | None) -> URIRef | None:
    if datatype is None or datatype == "rdf:langString":
        return None
    return expand_curie(datatype)


def write_triple(out: TextIO, s: URIRef, p: URIRef, o: URIRef | Literal) -> None:
    out.write(f"{s.n3()} {p.n3()} {o.n3()} .\n")


def normalize_literal(value: Any, transform: str | None = None) -> str:
    text = str(value).strip()
    if transform == "date_prefix":
        return text[:10]
    return text


def normalize_xsd_date(value: Any, transform: str | None = None) -> str | None:
    text = normalize_literal(value, transform=transform)
    return text if ISO_DATE_RE.match(text) else None


def add_literal(
    out: TextIO,
    subject: URIRef,
    predicate: URIRef,
    value: Any,
    datatype: str | None = None,
    lang: str | None = None,
    transform: str | None = None,
) -> None:
    if is_missing(value):
        return

    if datatype == "xsd:date":
        date_text = normalize_xsd_date(value, transform=transform)
        if date_text is not None:
            write_triple(out, subject, predicate, Literal(date_text, datatype=XSD.date))
        else:
            raw = str(value).strip()
            write_triple(out, subject, EVT.sourceDateValue, Literal(raw))
            write_triple(
                out,
                subject,
                EVT.dateNormalizationNote,
                Literal(
                    f"Source date value {raw!r} was not emitted as xsd:date because it could not be normalized to YYYY-MM-DD.",
                    lang="en",
                ),
            )
        return

    text = normalize_literal(value, transform=transform)

    if datatype == "rdf:langString":
        write_triple(out, subject, predicate, Literal(text, lang=lang or "it"))
    else:
        dt = datatype_uri(datatype)
        write_triple(out, subject, predicate, Literal(text, datatype=dt))


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

    write_triple(
        out,
        dataset_uri,
        EVT.metadataCompletionNote,
        Literal(
            "Official catalogue metadata such as license, issued date, modified date, and download URL should be added from Comune di Milano metadata.",
            lang="en",
        ),
    )


def add_transform_activity(
    out: TextIO,
    activity_uri: URIRef,
    dataset_uri: URIRef,
    dataset_name: str,
    defaults: dict[str, Any],
) -> None:
    agent_uri = URIRef(defaults["pipeline_agent_uri"])
    write_triple(out, agent_uri, RDF.type, PROV.Agent)
    write_triple(out, agent_uri, RDFS.label, Literal("Eventour RDF conversion pipeline", lang="en"))

    write_triple(out, activity_uri, RDF.type, PROV.Activity)
    write_triple(out, activity_uri, RDFS.label, Literal(f"Transform {dataset_name} dataset to RDF", lang="en"))
    write_triple(out, activity_uri, PROV.used, dataset_uri)
    write_triple(out, activity_uri, PROV.wasAssociatedWith, agent_uri)


def add_source_record(
    out: TextIO,
    entity_uri: URIRef,
    dataset_name: str,
    dataset_uri: URIRef,
    source_id_field: str,
    source_id_value: Any,
) -> URIRef:
    record_uri = evt_uri(f"source-record/{dataset_name}/{safe_token(source_id_value)}")
    write_triple(out, entity_uri, DCTERMS.source, dataset_uri)
    write_triple(out, entity_uri, PROV.wasDerivedFrom, record_uri)

    write_triple(out, record_uri, RDF.type, EVT.SourceRecord)
    write_triple(out, record_uri, DCTERMS.isPartOf, dataset_uri)
    write_triple(out, record_uri, EVT.sourceIdentifierField, Literal(source_id_field))
    write_triple(out, record_uri, EVT.sourceIdentifierValue, Literal(str(source_id_value)))
    return record_uri


def make_label(props: dict[str, Any], config: dict[str, Any]) -> str | None:
    if "label_field" in config:
        value = props.get(config["label_field"])
        if not is_missing(value):
            return str(value).strip()
    elif "label_template" in config:
        row_dict = {k: "" if is_missing(v) else str(v).strip() for k, v in props.items()}
        label = config["label_template"].format(**row_dict).strip()
        return label or None
    return None


def convert_dataset(out: TextIO, dataset_name: str, config: dict[str, Any], datasets_dir: Path, defaults: dict[str, Any]) -> int:
    path = datasets_dir / config["file"]
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    dataset_uri = evt_uri(config["dataset_uri"])
    activity_uri = evt_uri(config["transform_activity_uri"])

    add_dataset_metadata(out, dataset_name, dataset_uri, defaults)
    add_transform_activity(out, activity_uri, dataset_uri, dataset_name, defaults)

    default_lang = defaults.get("language", "it")
    crs_uri = defaults["crs_uri"]
    count = 0

    with fiona.open(path) as src:
        for feature in src:
            props = dict(feature["properties"])
            source_id_field = config["identifier_field"]
            source_id_value = props.get(source_id_field)
            if is_missing(source_id_value):
                continue

            safe_props = {k: safe_token(v) for k, v in props.items()}
            entity_path = config["entity_uri_template"].format(**safe_props)
            entity_uri = evt_uri(entity_path)

            for cls in config.get("classes", []):
                write_triple(out, entity_uri, RDF.type, expand_curie(cls))

            write_triple(out, entity_uri, DCTERMS.identifier, Literal(str(source_id_value)))

            label = make_label(props, config)
            if label:
                write_triple(out, entity_uri, RDFS.label, Literal(label, lang=default_lang))

            add_geometry(out, entity_uri, feature["geometry"], crs_uri)

            add_source_record(
                out,
                entity_uri,
                dataset_name,
                dataset_uri,
                config["source_identifier_field"],
                source_id_value,
            )

            write_triple(out, entity_uri, PROV.wasGeneratedBy, activity_uri)
            write_triple(out, activity_uri, PROV.generated, entity_uri)

            for source_field, field_cfg in config.get("fields", {}).items():
                value = props.get(source_field)
                if is_missing(value):
                    continue

                predicate = expand_curie(field_cfg["property"])
                kind = field_cfg.get("kind", "literal")

                if kind == "resource":
                    value_token = safe_token(value)
                    target_path = field_cfg["uri_template"].format(value=value_token)
                    write_triple(out, entity_uri, predicate, evt_uri(target_path))
                elif kind == "literal":
                    add_literal(
                        out,
                        entity_uri,
                        predicate,
                        value,
                        datatype=field_cfg.get("datatype"),
                        lang=field_cfg.get("lang", default_lang),
                        transform=field_cfg.get("transform"),
                    )
                else:
                    raise ValueError(f"Unsupported mapping kind {kind!r} for {dataset_name}.{source_field}")

            count += 1
            if count % 50000 == 0:
                print(f"  {dataset_name}: {count} entities written...", flush=True)

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", required=True, help="Folder containing source GeoJSON datasets")
    parser.add_argument("--mapping", required=True, help="YAML mapping file")
    parser.add_argument("--output", required=True, help="Output N-Triples file, e.g. output/eventour_phase1_data.nt")
    args = parser.parse_args()

    datasets_dir = Path(args.datasets)
    mapping_path = Path(args.mapping)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    defaults = config["defaults"]

    total = 0
    with output_path.open("w", encoding="utf-8") as out:
        for dataset_name, dataset_config in config["datasets"].items():
            count = convert_dataset(out, dataset_name, dataset_config, datasets_dir, defaults)
            print(f"{dataset_name}: {count} entities", flush=True)
            total += count

    print(f"Generated {total} entities")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Streaming Phase-3 Eventour services/facilities RDF converter.

Converts the remaining service/facility datasets to N-Triples:

- bicycle parking areas
- BikeMi stations
- Open WiFi access points
- historic shops
- public toilets
- interchange/public parking facilities
- EV charging stations
- drinking fountains / vedovelle

Run from the project root:

    $CONDA_PREFIX/bin/python scripts/convert_phase3_services_streaming.py \
      --datasets datasets \
      --mapping mappings/phase3_services_mappings.yaml \
      --output output/eventour_phase3_services_data.nt
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
SCHEMA = Namespace("https://schema.org/")
ORG = Namespace("http://www.w3.org/ns/org#")
LOCN = Namespace("http://www.w3.org/ns/locn#")

PREFIXES = {
    "evt": EVT,
    "geo": GEO,
    "prov": PROV,
    "dcat": DCAT,
    "skos": SKOS,
    "schema": SCHEMA,
    "org": ORG,
    "locn": LOCN,
    "dct": DCTERMS,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
}

CHARGING_TYPOLOGY_LABELS = {
    "N": "Normal charging",
    "F": "Fast charging",
    "Q": "Quadricycles",
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
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^A-Za-z0-9._~:-]+", "-", text)
    return text.strip("-")


def render_uri_template(template: str, props: dict[str, Any]) -> str:
    """Render URI templates with arbitrary source-field names.

    Python's str.format() cannot safely handle field names such as "N.".
    This function replaces every {field_name} manually, so templates like
    "historic-shop/{N.}" work correctly.
    """
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in props:
            available = ", ".join(sorted(props.keys()))
            raise KeyError(f"Template field {key!r} not found. Available fields: {available}")
        return safe_token(props[key])

    return re.sub(r"\{([^{}]+)\}", replace, template)


def slug(value: Any) -> str:
    text = clean_text(value).lower()
    text = text.replace("à", "a").replace("è", "e").replace("é", "e").replace("ì", "i").replace("ò", "o").replace("ù", "u")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def evt_uri(path: str) -> URIRef:
    return URIRef(str(EVT) + path.lstrip("/"))


def expand_curie(curie: str) -> URIRef:
    prefix, local = curie.split(":", 1)
    if prefix not in PREFIXES:
        raise ValueError(f"Unknown prefix in CURIE: {curie}")
    return URIRef(str(PREFIXES[prefix]) + local)


def write_triple(out: TextIO, s: URIRef, p: URIRef, o: URIRef | Literal) -> None:
    out.write(f"{s.n3()} {p.n3()} {o.n3()} .\n")


def datatype_uri(datatype: str | None) -> URIRef | None:
    if datatype is None or datatype == "rdf:langString":
        return None
    return expand_curie(datatype)


def literal_for(value: Any, datatype: str | None = None, lang: str | None = None) -> Literal | None:
    if is_missing(value):
        return None
    text = clean_text(value)
    if datatype == "rdf:langString":
        return Literal(text, lang=lang or "it")
    if datatype == "xsd:gYear":
        match = re.search(r"\d{4}", text)
        return Literal(match.group(0), datatype=XSD.gYear) if match else None
    dt = datatype_uri(datatype)
    return Literal(text, datatype=dt)


def integer_literal(value: Any) -> Literal | None:
    if is_missing(value):
        return None
    text = clean_text(value)
    match = re.search(r"-?\d+", text)
    return Literal(match.group(0), datatype=XSD.integer) if match else None


def concept_uri(scheme: str, value: Any) -> URIRef:
    return evt_uri(f"{scheme}/{slug(value)}")


def add_concept(out: TextIO, scheme: str, value: Any, label: str | None = None, notation: str | None = None) -> URIRef:
    uri = concept_uri(scheme, value)
    scheme_uri = evt_uri(f"scheme/{scheme}")

    write_triple(out, scheme_uri, RDF.type, SKOS.ConceptScheme)
    write_triple(out, scheme_uri, RDFS.label, Literal(f"{scheme.replace('-', ' ').title()} concept scheme", lang="en"))

    write_triple(out, uri, RDF.type, SKOS.Concept)
    write_triple(out, uri, SKOS.inScheme, scheme_uri)
    write_triple(out, uri, SKOS.topConceptOf, scheme_uri)
    write_triple(out, scheme_uri, SKOS.hasTopConcept, uri)
    write_triple(out, uri, SKOS.prefLabel, Literal(label or clean_text(value), lang="it"))
    write_triple(out, uri, SKOS.notation, Literal(notation or clean_text(value)))
    return uri


def split_multi(value: Any) -> list[str]:
    if is_missing(value):
        return []
    text = clean_text(value)
    # Protect the explicit "Condivisa (...)" value as one concept.
    if "Condivisa" in text:
        return [text]
    return [p.strip() for p in re.split(r"[,;/|]+", text) if p.strip()]


def organization_uri(name: Any) -> URIRef:
    return evt_uri(f"organization/{slug(name)}")


def project_uri(name: Any) -> URIRef:
    return evt_uri(f"project/{slug(name)}")


def address_uri(entity_uri: URIRef) -> URIRef:
    return URIRef(str(entity_uri) + "/address")



def starts_with_street_type(street_name: str, street_type: str) -> bool:
    if not street_name or not street_type:
        return False
    s = street_name.strip().lower()
    t = street_type.strip().lower()
    return s == t or s.startswith(t + " ")


def compose_full_address(
    props: dict[str, Any],
    address_field: str | None = None,
    street_name_field: str | None = None,
    street_type_field: str | None = None,
    house_number_field: str | None = None,
    locality_field: str | None = None,
) -> str | None:
    address = clean_text(props.get(address_field)) if address_field else ""
    street_name = clean_text(props.get(street_name_field)) if street_name_field else ""
    street_type = clean_text(props.get(street_type_field)) if street_type_field else ""
    house_number = clean_text(props.get(house_number_field)) if house_number_field else ""
    locality = clean_text(props.get(locality_field)) if locality_field else ""

    if address:
        full = address
    elif street_name:
        if street_type and not starts_with_street_type(street_name, street_type):
            full = f"{street_type} {street_name}"
        else:
            full = street_name
    elif locality:
        full = locality
    else:
        return None

    if house_number:
        normalized = full.strip().lower()
        if not re.search(rf"\\b{re.escape(house_number.lower())}\\b", normalized):
            full = f"{full} {house_number}"

    full = re.sub(r"\\s+", " ", full).strip()
    return full or None



def starts_with_street_type(street_name: str, street_type: str) -> bool:
    if not street_name or not street_type:
        return False
    s = street_name.strip().lower()
    t = street_type.strip().lower()
    return s == t or s.startswith(t + " ")


def compose_full_address(
    props: dict[str, Any],
    address_field: str | None = None,
    street_name_field: str | None = None,
    street_type_field: str | None = None,
    house_number_field: str | None = None,
    locality_field: str | None = None,
) -> str | None:
    address = clean_text(props.get(address_field)) if address_field else ""
    street_name = clean_text(props.get(street_name_field)) if street_name_field else ""
    street_type = clean_text(props.get(street_type_field)) if street_type_field else ""
    house_number = clean_text(props.get(house_number_field)) if house_number_field else ""
    locality = clean_text(props.get(locality_field)) if locality_field else ""

    if address:
        full = address
    elif street_name:
        if street_type and not starts_with_street_type(street_name, street_type):
            full = f"{street_type} {street_name}"
        else:
            full = street_name
    elif locality:
        full = locality
    else:
        return None

    if house_number:
        normalized = full.strip().lower()
        if not re.search(rf"\\b{re.escape(house_number.lower())}\\b", normalized):
            full = f"{full} {house_number}"

    full = re.sub(r"\\s+", " ", full).strip()
    return full or None


def add_address(out: TextIO, entity_uri: URIRef, props: dict[str, Any], cfg: dict[str, Any], lang: str) -> None:
    addr_cfg = cfg.get("address") or {}
    if not addr_cfg:
        return

    address_field = addr_cfg.get("address_field")
    street_name_field = addr_cfg.get("street_name_field")
    street_type_field = addr_cfg.get("street_type_field")
    house_number_field = addr_cfg.get("house_number_field")
    postal_code_field = addr_cfg.get("postal_code_field")
    locality_field = addr_cfg.get("locality_field")
    street_id_field = addr_cfg.get("street_id_field")

    full_address = compose_full_address(
        props,
        address_field=address_field,
        street_name_field=street_name_field,
        street_type_field=street_type_field,
        house_number_field=house_number_field,
        locality_field=locality_field,
    )

    has_any_component = any(
        f and not is_missing(props.get(f))
        for f in [
            address_field,
            street_name_field,
            street_type_field,
            house_number_field,
            postal_code_field,
            locality_field,
            street_id_field,
        ]
    )

    if not full_address and not has_any_component:
        return

    addr = address_uri(entity_uri)
    write_triple(out, entity_uri, SCHEMA.address, addr)
    write_triple(out, addr, RDF.type, LOCN.Address)
    write_triple(out, addr, RDF.type, SCHEMA.PostalAddress)

    if full_address:
        write_triple(out, addr, SCHEMA.streetAddress, Literal(full_address, lang=lang))
        write_triple(out, addr, LOCN.fullAddress, Literal(full_address, lang=lang))

    if street_name_field and not is_missing(props.get(street_name_field)):
        write_triple(out, addr, EVT.streetName, Literal(clean_text(props[street_name_field]), lang=lang))
        write_triple(out, addr, LOCN.thoroughfare, Literal(clean_text(props[street_name_field]), lang=lang))

    if street_type_field and not is_missing(props.get(street_type_field)):
        write_triple(out, addr, EVT.streetType, Literal(clean_text(props[street_type_field]), lang=lang))

    if house_number_field and not is_missing(props.get(house_number_field)):
        write_triple(out, addr, LOCN.locatorDesignator, Literal(clean_text(props[house_number_field])))

    if street_id_field and not is_missing(props.get(street_id_field)):
        write_triple(out, addr, EVT.streetIdentifier, Literal(clean_text(props[street_id_field])))

    if postal_code_field and not is_missing(props.get(postal_code_field)):
        write_triple(out, addr, SCHEMA.postalCode, Literal(clean_text(props[postal_code_field])))
        write_triple(out, addr, LOCN.postCode, Literal(clean_text(props[postal_code_field])))

    if locality_field and not is_missing(props.get(locality_field)):
        write_triple(out, addr, EVT.locality, Literal(clean_text(props[locality_field]), lang=lang))


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


def add_source_record(out: TextIO, entity_uri: URIRef, dataset_name: str, dataset_uri: URIRef, source_id_field: str, source_id_value: Any) -> None:
    record_uri = evt_uri(f"source-record/{dataset_name}/{safe_token(source_id_value)}")
    write_triple(out, entity_uri, DCTERMS.source, dataset_uri)
    write_triple(out, entity_uri, PROV.wasDerivedFrom, record_uri)
    write_triple(out, record_uri, RDF.type, EVT.SourceRecord)
    write_triple(out, record_uri, DCTERMS.isPartOf, dataset_uri)
    write_triple(out, record_uri, EVT.sourceIdentifierField, Literal(source_id_field))
    write_triple(out, record_uri, EVT.sourceIdentifierValue, Literal(str(source_id_value)))


def add_label(out: TextIO, entity_uri: URIRef, props: dict[str, Any], cfg: dict[str, Any], lang: str) -> None:
    if "label_field" in cfg and not is_missing(props.get(cfg["label_field"])):
        write_triple(out, entity_uri, RDFS.label, Literal(clean_text(props[cfg["label_field"]]), lang=lang))
        return
    if "label_template" in cfg:
        safe_props = {k: clean_text(v) for k, v in props.items()}
        try:
            label = cfg["label_template"].format(**safe_props)
        except KeyError:
            label = cfg["label_template"]
        if label:
            write_triple(out, entity_uri, RDFS.label, Literal(label, lang=lang))


def add_literal_field(out: TextIO, entity_uri: URIRef, pred: URIRef, value: Any, field_cfg: dict[str, Any], lang: str) -> None:
    kind = field_cfg.get("kind", "literal")

    if kind == "integer":
        lit = integer_literal(value)
        if lit is not None:
            write_triple(out, entity_uri, pred, lit)
        else:
            write_triple(out, entity_uri, EVT.sourceNumericValue, Literal(clean_text(value)))
        return

    if kind == "gYear":
        lit = literal_for(value, "xsd:gYear")
        if lit is not None:
            write_triple(out, entity_uri, pred, lit)
        else:
            write_triple(out, entity_uri, EVT.sourceYearValue, Literal(clean_text(value)))
        return

    lit = literal_for(value, field_cfg.get("datatype"), field_cfg.get("lang", lang))
    if lit is not None:
        write_triple(out, entity_uri, pred, lit)


def add_specials(out: TextIO, entity_uri: URIRef, props: dict[str, Any], cfg: dict[str, Any], lang: str) -> None:
    special = cfg.get("special") or {}

    if special.get("parse_capacity_from_TAB1") and not is_missing(props.get("TAB1")):
        raw = clean_text(props["TAB1"])
        lit = integer_literal(raw)
        if lit is not None:
            write_triple(out, entity_uri, EVT.parkingSpaces, lit)
            write_triple(out, entity_uri, EVT.derivedValueNote, Literal("The numeric parking-space value was parsed from the source TAB1 field.", lang="en"))

    if special.get("derive_interchange_line_from_INFO") and not is_missing(props.get("INFO")):
        info = clean_text(props["INFO"])
        # Simple extraction: MM2, M2, LINEA 2 -> transit-line/metro/2
        match = re.search(r"\bM{1,2}\s*(\d+)\b", info.upper())
        if match:
            line_uri = evt_uri(f"transit-line/metro/{match.group(1)}")
            write_triple(out, entity_uri, EVT.interchangesWithLine, line_uri)
            write_triple(out, entity_uri, EVT.derivedRelationNote, Literal(f"The link to Metro line {match.group(1)} is derived from the free-text INFO field.", lang="en"))

    if special.get("titolare_as_responsible_organization") and not is_missing(props.get("titolare")):
        org_uri = organization_uri(props["titolare"])
        write_triple(out, org_uri, RDF.type, ORG.Organization)
        write_triple(out, org_uri, RDF.type, PROV.Agent)
        write_triple(out, org_uri, RDFS.label, Literal(clean_text(props["titolare"])))
        write_triple(out, entity_uri, SCHEMA.provider, org_uri)
        write_triple(out, entity_uri, EVT.responsibleOrganization, org_uri)
        write_triple(out, entity_uri, EVT.sourceResponsibleOrganizationRole, Literal("titolare"))

    if special.get("project_as_resource") and not is_missing(props.get("progetto")):
        p_uri = project_uri(props["progetto"])
        write_triple(out, p_uri, RDF.type, EVT.Project)
        write_triple(out, p_uri, RDFS.label, Literal(clean_text(props["progetto"]), lang=lang))
        write_triple(out, entity_uri, EVT.partOfProject, p_uri)


def add_charging_typology(out: TextIO, entity_uri: URIRef, value: Any) -> None:
    if is_missing(value):
        return

    raw = clean_text(value).upper()
    write_triple(out, entity_uri, EVT.sourceChargingTypologyCode, Literal(raw))

    # Combined concept, e.g. QN
    combined = add_concept(out, "charging-typology", raw, label=raw, notation=raw)
    write_triple(out, entity_uri, EVT.chargingTypology, combined)

    # Expanded individual code concepts, e.g. Q + N.
    for char in raw:
        if char.isalpha():
            label = CHARGING_TYPOLOGY_LABELS.get(char, char)
            c_uri = add_concept(out, "charging-typology", char, label=label, notation=char)
            write_triple(out, entity_uri, EVT.chargingTypology, c_uri)


def add_field(out: TextIO, entity_uri: URIRef, props: dict[str, Any], source_field: str, field_cfg: dict[str, Any], lang: str) -> None:
    if source_field not in props or is_missing(props[source_field]):
        return

    value = props[source_field]
    pred = expand_curie(field_cfg["property"])
    kind = field_cfg.get("kind", "literal")

    if kind == "resource":
        target_path = field_cfg["uri_template"].format(value=safe_token(value))
        write_triple(out, entity_uri, pred, evt_uri(target_path))
    elif kind == "concept":
        c_uri = add_concept(out, field_cfg["scheme"], value)
        write_triple(out, entity_uri, pred, c_uri)
    elif kind == "multi_concept":
        for part in split_multi(value):
            c_uri = add_concept(out, field_cfg["scheme"], part)
            write_triple(out, entity_uri, pred, c_uri)
        write_triple(out, entity_uri, EVT.sourceMultiValue, Literal(clean_text(value)))
    elif kind == "charging_typology":
        add_charging_typology(out, entity_uri, value)
    else:
        add_literal_field(out, entity_uri, pred, value, field_cfg, lang)


def convert_dataset(out: TextIO, dataset_name: str, cfg: dict[str, Any], datasets_dir: Path, defaults: dict[str, Any]) -> int:
    path = datasets_dir / cfg["file"]
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    dataset_uri = evt_uri(cfg["dataset_uri"])
    activity_uri = evt_uri(cfg["transform_activity_uri"])
    lang = defaults.get("language", "it")

    add_dataset_metadata(out, dataset_name, dataset_uri, defaults)
    add_transform_activity(out, dataset_name, dataset_uri, activity_uri, defaults)

    count = 0
    with fiona.open(path) as src:
        for feature in src:
            props = dict(feature["properties"])
            identifier_field = cfg["identifier_field"]
            identifier_value = props.get(identifier_field)

            if is_missing(identifier_value):
                continue

            # Use a custom renderer because source fields may contain punctuation, e.g. "N.".
            entity_uri = evt_uri(render_uri_template(cfg["entity_uri_template"], props))

            for cls in cfg.get("classes", []):
                write_triple(out, entity_uri, RDF.type, expand_curie(cls))

            write_triple(out, entity_uri, DCTERMS.identifier, Literal(str(identifier_value)))
            add_label(out, entity_uri, props, cfg, lang)
            add_geometry(out, entity_uri, feature["geometry"], defaults["crs_uri"])
            add_address(out, entity_uri, props, cfg, lang)

            for source_field, field_cfg in cfg.get("fields", {}).items():
                add_field(out, entity_uri, props, source_field, field_cfg, lang)

            add_specials(out, entity_uri, props, cfg, lang)

            add_source_record(out, entity_uri, dataset_name, dataset_uri, identifier_field, identifier_value)
            write_triple(out, entity_uri, PROV.wasGeneratedBy, activity_uri)
            write_triple(out, activity_uri, PROV.generated, entity_uri)

            count += 1

    return count


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
            count = convert_dataset(out, dataset_name, cfg, datasets_dir, defaults)
            print(f"{dataset_name}: {count} entities", flush=True)
            total += count

    print(f"Generated {total} service/facility entities")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

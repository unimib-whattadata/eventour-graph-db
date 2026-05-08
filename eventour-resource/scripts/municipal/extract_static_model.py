#!/usr/bin/env python3
"""Extract the static Eventour model from an example KG TTL.

Purpose
-------
Your example KG likely contains both:
  1. static ontology/vocabulary/metadata triples, and
  2. example individuals such as example trees, stops, parking facilities, etc.

For the production KG, we want to combine:
  static model layer + generated data layer

but we do NOT want to duplicate example individuals.

This script extracts the static layer into:
  output/eventour_static_model.ttl
  output/eventour_static_model.nt

It keeps:
  - owl/rdfs classes
  - rdf/owl properties
  - SKOS concept schemes and concepts
  - DCAT datasets and distributions
  - organizations / agents
  - selected Eventour static URI namespaces such as scheme/, status/, day-type/,
    transport-mode/, route-direction/, charging-typology/, etc.

It drops:
  - example domain individuals such as evt:tree/..., evt:bench/...,
    evt:stop/..., evt:route-pattern/..., evt:parking-facility/..., etc.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS

EVT = Namespace("http://eventour.unimib.it/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SCHEMA = Namespace("https://schema.org/")
ORG = Namespace("http://www.w3.org/ns/org#")
LOCN = Namespace("http://www.w3.org/ns/locn#")
SH = Namespace("http://www.w3.org/ns/shacl#")


STATIC_RDF_TYPES = {
    OWL.Ontology,
    OWL.Class,
    RDFS.Class,
    RDF.Property,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    SKOS.ConceptScheme,
    SKOS.Concept,
    DCAT.Dataset,
    DCAT.Distribution,
    ORG.Organization,
    PROV.Agent,
    SH.NodeShape,
    SH.PropertyShape,
}

# Eventour URI path prefixes that are static vocabulary/metadata rather than
# generated domain instances.
STATIC_EVT_PATH_PREFIXES = (
    "ontology",
    "scheme/",
    "status/",
    "transport-mode/",
    "route-direction/",
    "day-type/",
    "commercial-category/",
    "charging-typology/",
    "vehicle-type/",
    "street-furniture-type/",
    "placement-context/",
    "station-layout-type/",
    "toilet-type/",
    "parking-type/",
    "urban-belt/",
    "implementation-status/",
    "charging-infrastructure/",
    "organization/",
    "agent/",
    "dataset/",
    "distribution/",
    "license/",
    "theme/",
    "place/",
)

# Eventour generated instance path prefixes. These are explicitly dropped from
# the static model, even if they appear in the example KG.
GENERATED_EVT_PATH_PREFIXES = (
    "tree/",
    "bench/",
    "picnic-table/",
    "nil/",
    "subnil/",
    "municipality/",
    "geometry/",
    "stop/",
    "transit-line/",
    "route-pattern/",
    "stop-in-route/",
    "service-pattern/",
    "timetable-summary/",
    "bicycle-parking-area/",
    "bike-sharing-station/",
    "wifi-access-point/",
    "historic-shop/",
    "public-toilet/",
    "parking-facility/",
    "ev-charging-station/",
    "drinking-fountain/",
    "source-record/",
    "activity/transform/",
)


def evt_path(uri: URIRef) -> str | None:
    text = str(uri)
    base = str(EVT)
    if text.startswith(base):
        return text[len(base):]
    return None


def is_static_evt_uri(uri: URIRef) -> bool:
    path = evt_path(uri)
    if path is None:
        return False

    if path.startswith(GENERATED_EVT_PATH_PREFIXES):
        return False

    return path.startswith(STATIC_EVT_PATH_PREFIXES)


def is_static_subject(g: Graph, s) -> bool:
    if isinstance(s, BNode):
        return False

    if isinstance(s, URIRef):
        if is_static_evt_uri(s):
            return True

    for t in g.objects(s, RDF.type):
        if t in STATIC_RDF_TYPES:
            return True

    return False


def should_keep_uri(g: Graph, uri: URIRef, static_subjects: set) -> bool:
    # Keep external ontology terms and literals referenced by static definitions.
    if str(uri).startswith((
        str(RDF),
        str(RDFS),
        str(OWL),
        str(XSD),
        str(DCTERMS),
        str(GEO),
        str(PROV),
        str(DCAT),
        str(SKOS),
        str(SCHEMA),
        str(ORG),
        str(LOCN),
        str(SH),
    )):
        return True

    if uri in static_subjects:
        return True

    if is_static_evt_uri(uri):
        return True

    # Keep classes/properties from any namespace if explicitly typed as static.
    for t in g.objects(uri, RDF.type):
        if t in STATIC_RDF_TYPES:
            return True

    return False


def add_bnode_closure(src: Graph, dst: Graph, bnode: BNode, seen: set[BNode]) -> None:
    if bnode in seen:
        return
    seen.add(bnode)

    for s, p, o in src.triples((bnode, None, None)):
        dst.add((s, p, o))
        if isinstance(o, BNode):
            add_bnode_closure(src, dst, o, seen)


def extract_static_model(src: Graph) -> Graph:
    dst = Graph()

    # Preserve common prefixes.
    prefixes = {
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
        "owl": OWL,
        "xsd": XSD,
        "sh": SH,
    }
    for prefix, ns in prefixes.items():
        dst.bind(prefix, ns)

    static_subjects = {s for s in set(src.subjects()) if is_static_subject(src, s)}

    # Expand seeds by adding URI objects that are themselves static terms.
    changed = True
    while changed:
        changed = False
        for s in list(static_subjects):
            for _, _, o in src.triples((s, None, None)):
                if isinstance(o, URIRef) and is_static_subject(src, o) and o not in static_subjects:
                    static_subjects.add(o)
                    changed = True

    bnode_seen: set[BNode] = set()

    for s in static_subjects:
        for _, p, o in src.triples((s, None, None)):
            keep = False

            if isinstance(o, BNode):
                keep = True
            elif isinstance(o, URIRef):
                keep = should_keep_uri(src, o, static_subjects)
            else:
                keep = True

            if keep:
                dst.add((s, p, o))
                if isinstance(o, BNode):
                    add_bnode_closure(src, dst, o, bnode_seen)

    return dst


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="ontology/eventour_final_example_kg_production_refined.ttl",
        help="Input example KG TTL file",
    )
    parser.add_argument(
        "--output-ttl",
        default="output/eventour_static_model.ttl",
        help="Output static model TTL",
    )
    parser.add_argument(
        "--output-nt",
        default="output/eventour_static_model.nt",
        help="Output static model N-Triples",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_ttl = Path(args.output_ttl)
    output_nt = Path(args.output_nt)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}. "
            "Check the path to your final example KG TTL."
        )

    output_ttl.parent.mkdir(parents=True, exist_ok=True)
    output_nt.parent.mkdir(parents=True, exist_ok=True)

    src = Graph()
    src.parse(str(input_path), format="turtle")

    static = extract_static_model(src)
    static.serialize(destination=str(output_ttl), format="turtle")
    static.serialize(destination=str(output_nt), format="nt")

    print(f"Input triples: {len(src)}")
    print(f"Static triples: {len(static)}")
    print(f"Wrote {output_ttl}")
    print(f"Wrote {output_nt}")

    # Quick warning if obvious generated instances slipped through.
    generated_prefix_hits = []
    for s in set(static.subjects()):
        if isinstance(s, URIRef):
            path = evt_path(s)
            if path and path.startswith(GENERATED_EVT_PATH_PREFIXES):
                generated_prefix_hits.append(str(s))

    if generated_prefix_hits:
        print("WARNING: Generated-looking subjects found in static output:")
        for uri in generated_prefix_hits[:20]:
            print("  ", uri)
        if len(generated_prefix_hits) > 20:
            print(f"  ... and {len(generated_prefix_hits) - 20} more")
    else:
        print("No generated-instance URI prefixes found in static output.")


if __name__ == "__main__":
    main()

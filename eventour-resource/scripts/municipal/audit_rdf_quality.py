#!/usr/bin/env python3
from __future__ import annotations
import argparse, re
from collections import defaultdict
from pathlib import Path
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, DCTERMS

EVT = Namespace("http://eventour.unimib.it/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SCHEMA = Namespace("https://schema.org/")
LOCN = Namespace("http://www.w3.org/ns/locn#")

DUP_STREET = re.compile(r"\b(via|viale|piazza|p\.za|corso|largo|vicolo|strada|parco)\s+\1\b", re.I)
NUMERIC_ONLY = re.compile(r"^\s*\d+[A-Za-z]?\s*$")

DOMAIN_CLASSES = [
    EVT.NILArea, EVT.Tree, EVT.Bench, EVT.PicnicTable, EVT.Stop, EVT.RoutePattern,
    EVT.StopInRoute, EVT.TimetableSummary, EVT.BicycleParkingArea, EVT.BikeSharingStation,
    EVT.WiFiAccessPoint, EVT.HistoricShop, EVT.PublicToilet, EVT.ParkingFacility,
    EVT.EVChargingStation, EVT.DrinkingFountain,
]

NIL_RELEVANT = [
    EVT.Tree, EVT.Bench, EVT.PicnicTable, EVT.Stop, EVT.BicycleParkingArea,
    EVT.BikeSharingStation, EVT.WiFiAccessPoint, EVT.HistoricShop, EVT.PublicToilet,
    EVT.ParkingFacility, EVT.EVChargingStation, EVT.DrinkingFountain,
]

def w(f, s=""):
    print(s)
    f.write(s + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="output/eventour_complete_kg.nt")
    ap.add_argument("--report", default="output/eventour_quality_report.txt")
    args = ap.parse_args()

    g = Graph()
    g.parse(args.input, format="nt")
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        w(f, "Eventour RDF quality report")
        w(f, "=" * 80)
        w(f, f"Triples: {len(g)}")
        w(f)

        class_sets = {}
        w(f, "Class counts")
        w(f, "-" * 80)
        for c in DOMAIN_CLASSES:
            s = set(g.subjects(RDF.type, c))
            class_sets[c] = s
            w(f, f"{c}: {len(s)}")
        w(f)

        w(f, "Address checks")
        w(f, "-" * 80)
        address_literals = []
        for p in [SCHEMA.streetAddress, LOCN.fullAddress]:
            for s, o in g.subject_objects(p):
                if isinstance(o, Literal):
                    address_literals.append((s, p, str(o)))

        dup = [(s,p,v) for s,p,v in address_literals if DUP_STREET.search(v)]
        numeric = [(s,p,v) for s,p,v in address_literals if p == SCHEMA.streetAddress and NUMERIC_ONLY.match(v)]

        street_by_addr = defaultdict(set)
        for s, o in g.subject_objects(SCHEMA.streetAddress):
            street_by_addr[s].add(str(o))
        multi = {s: vals for s, vals in street_by_addr.items() if len(vals) > 1}

        w(f, f"Address literals checked: {len(address_literals)}")
        w(f, f"Duplicate street-type addresses like 'Via Via ...': {len(dup)}")
        for s,p,v in dup[:20]: w(f, f"  {s} {p} {v!r}")
        w(f, f"Numeric-only schema:streetAddress values: {len(numeric)}")
        for s,p,v in numeric[:20]: w(f, f"  {s} {p} {v!r}")
        w(f, f"Address nodes with multiple schema:streetAddress values: {len(multi)}")
        for s, vals in list(multi.items())[:20]: w(f, f"  {s}: {sorted(vals)}")
        w(f)

        w(f, "NIL checks")
        w(f, "-" * 80)
        nils = set(g.subjects(RDF.type, EVT.NILArea))
        dangling = [(s,o) for s,o in g.subject_objects(EVT.inNIL) if o not in nils]
        w(f, f"NILArea resources: {len(nils)}")
        w(f, f"Dangling evt:inNIL references: {len(dangling)}")
        for s,o in dangling[:20]: w(f, f"  {s} -> {o}")
        for c in NIL_RELEVANT:
            ents = class_sets.get(c, set())
            if ents:
                missing = [s for s in ents if not list(g.objects(s, EVT.inNIL))]
                w(f, f"{c}: missing evt:inNIL {len(missing)} / {len(ents)}")
        w(f)

        w(f, "Geometry / provenance checks")
        w(f, "-" * 80)
        spatial = set()
        for c in [EVT.NILArea, EVT.Tree, EVT.Bench, EVT.PicnicTable, EVT.Stop, EVT.RoutePattern,
                  EVT.BicycleParkingArea, EVT.BikeSharingStation, EVT.WiFiAccessPoint, EVT.HistoricShop,
                  EVT.PublicToilet, EVT.ParkingFacility, EVT.EVChargingStation, EVT.DrinkingFountain]:
            spatial.update(g.subjects(RDF.type, c))
        w(f, f"Spatial entities: {len(spatial)}")
        w(f, f"Missing geo:hasDefaultGeometry: {sum(1 for s in spatial if not list(g.objects(s, GEO.hasDefaultGeometry)))}")
        w(f, f"Missing dct:source: {sum(1 for s in spatial if not list(g.objects(s, DCTERMS.source)))}")
        w(f, f"Missing prov:wasDerivedFrom: {sum(1 for s in spatial if not list(g.objects(s, PROV.wasDerivedFrom)))}")
        w(f, f"Missing prov:wasGeneratedBy: {sum(1 for s in spatial if not list(g.objects(s, PROV.wasGeneratedBy)))}")
        w(f)

        w(f, "Concept URI checks")
        w(f, "-" * 80)
        ch = set(g.objects(None, EVT.chargingTypology))
        lower = sorted(str(u) for u in ch if "/charging-typology/" in str(u) and str(u).split("/")[-1].islower())
        upper = sorted(str(u) for u in ch if "/charging-typology/" in str(u) and str(u).split("/")[-1].isupper())
        w(f, f"Charging typology concepts used: {len(ch)}")
        w(f, f"Lowercase charging typology URIs: {len(lower)}")
        for u in lower[:20]: w(f, f"  {u}")
        w(f, f"Uppercase charging typology URIs: {len(upper)}")
        for u in upper[:20]: w(f, f"  {u}")
        w(f)
        w(f, f"Report written to {out}")

if __name__ == "__main__":
    main()

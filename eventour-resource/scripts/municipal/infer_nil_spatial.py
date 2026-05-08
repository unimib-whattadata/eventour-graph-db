#!/usr/bin/env python3
from __future__ import annotations
import argparse, re
from pathlib import Path
from typing import Any
import geopandas as gpd
from rdflib import Literal, Namespace, URIRef

EVT = Namespace("http://eventour.unimib.it/")

def safe_token(v: Any) -> str:
    text = "" if v is None else str(v).strip()
    text = text.replace("/", "-").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^A-Za-z0-9._~:-]+", "-", text)
    return text.strip("-")
    
def normalize_nil_id(value):
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text

def evt_uri(path: str) -> URIRef:
    return URIRef(str(EVT) + path.lstrip("/"))

def render(template: str, row: dict[str, Any]) -> str:
    def repl(m):
        key = m.group(1)
        if key not in row:
            raise KeyError(f"Missing field {key!r}. Available: {sorted(row.keys())}")
        return safe_token(row[key])
    return re.sub(r"\{([^{}]+)\}", repl, template)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nil", required=True, help="NIL polygon GeoJSON")
    ap.add_argument("--output", required=True)
    ap.add_argument("--datasets-dir", default="datasets")
    ap.add_argument("--property", default="inNIL")
    ap.add_argument("--relation", choices=["within", "intersects"], default="within")
    ap.add_argument("--target", nargs=3, action="append", metavar=("GEOJSON", "URI_TEMPLATE", "ID_FIELD"))
    args = ap.parse_args()

    if not args.target:
        raise SystemExit("Use at least one --target GEOJSON URI_TEMPLATE ID_FIELD")

    nil = gpd.read_file(args.nil).to_crs("EPSG:4326")[["ID_NIL", "NIL", "geometry"]]
    prop = EVT[args.property]
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0

    with out_path.open("w", encoding="utf-8") as out:
        for filename, uri_template, id_field in args.target:
            path = Path(filename)
            if not path.exists():
                path = Path(args.datasets_dir) / filename
            target = gpd.read_file(path).to_crs("EPSG:4326")
            if args.relation == "within":
                join_geom = target.copy()
                join_geom["geometry"] = join_geom.geometry.representative_point()
                joined = gpd.sjoin(join_geom, nil, predicate="within", how="left")
                method = "spatial-within-representative-point"
            else:
                joined = gpd.sjoin(target, nil, predicate="intersects", how="left")
                method = "spatial-intersects"

            matched = 0
            for _, row in joined.iterrows():
                if str(row.get("ID_NIL")).lower() in {"nan", "none", ""}:
                    continue
                entity = evt_uri(render(uri_template, row.to_dict()))
                nil_id = normalize_nil_id(row["ID_NIL"])
                nil_uri = evt_uri(f"nil/{safe_token(nil_id)}")
                out.write(f"{entity.n3()} {prop.n3()} {nil_uri.n3()} .\n")
                out.write(f"{entity.n3()} {EVT.nilInferenceMethod.n3()} {Literal(method).n3()} .\n")
                out.write(f"{entity.n3()} {EVT.inferredNILIdentifier.n3()} {Literal(nil_id).n3()} .\n")
                out.write(f"{entity.n3()} {EVT.inferredNILName.n3()} {Literal(str(row['NIL']), lang='it').n3()} .\n")
                matched += 1
            print(f"{path.name}: {matched} inferred NIL links")
            total += matched

    print(f"Wrote {out_path}")
    print(f"Total inferred NIL links: {total}")

if __name__ == "__main__":
    main()

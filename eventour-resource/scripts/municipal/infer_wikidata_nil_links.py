"""Infer NIL membership for Eventour Wikidata places.

The script performs a deterministic point-in-polygon assignment from Wikidata
place coordinates to the Comune di Milano NIL polygons. It emits RDF triples
that can be appended to the Wikidata place layer and the final KG.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EVT = "http://eventour.unimib.it/"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"

RETAINED_LABELS = {"primary_poi", "secondary_poi", "secondary_cultural_poi", "context_entity"}


def escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def nt_uri(value: str) -> str:
    return f"<{value}>"


def nt_literal(value: str, *, lang: str | None = None, datatype: str | None = None) -> str:
    text = f'"{escape_literal(value)}"'
    if lang is not None:
        return f"{text}@{lang}"
    if datatype is not None:
        return f"{text}^^<{datatype}>"
    return text


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 4:
        return False

    x = lon
    y = lat
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]

        # Treat points on polygon boundaries as inside.
        cross = (x - xi) * (yj - yi) - (y - yi) * (xj - xi)
        if abs(cross) < 1e-12 and min(xi, xj) - 1e-12 <= x <= max(xi, xj) + 1e-12 and min(yi, yj) - 1e-12 <= y <= max(yi, yj) + 1e-12:
            return True

        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def point_in_polygon(lon: float, lat: float, polygon: list[list[list[float]]]) -> bool:
    if not polygon:
        return False
    if not point_in_ring(lon, lat, polygon[0]):
        return False
    return not any(point_in_ring(lon, lat, hole) for hole in polygon[1:])


def point_in_geometry(lon: float, lat: float, geometry: dict[str, Any]) -> bool:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geom_type == "Polygon":
        return point_in_polygon(lon, lat, coordinates)
    if geom_type == "MultiPolygon":
        return any(point_in_polygon(lon, lat, polygon) for polygon in coordinates)
    return False


def geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    points: list[list[float]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
            points.append(value)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(geometry.get("coordinates", []))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_nil_polygons(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    polygons: list[dict[str, Any]] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geometry = feature.get("geometry")
        if not geometry:
            continue
        nil_id = str(props.get("ID_NIL")).strip()
        nil_name = str(props.get("NIL")).strip()
        polygons.append(
            {
                "nil_id": nil_id,
                "nil_name": nil_name,
                "iri": f"{EVT}milan/nil/{nil_id}",
                "geometry": geometry,
                "bbox": geometry_bbox(geometry),
            }
        )
    return polygons


def load_retained_wikidata_places(path: Path) -> list[dict[str, Any]]:
    places: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("final_label") not in RETAINED_LABELS:
                continue
            lon = row.get("longitude")
            lat = row.get("latitude")
            qid = row.get("item_qid")
            if qid is None or lon is None or lat is None:
                continue
            places.append(
                {
                    "qid": str(qid),
                    "iri": f"{EVT}milan/entity/wikidata/{qid}",
                    "longitude": float(lon),
                    "latitude": float(lat),
                }
            )
    return places


def assign_nil(place: dict[str, Any], nil_polygons: list[dict[str, Any]]) -> dict[str, Any] | None:
    lon = place["longitude"]
    lat = place["latitude"]
    for nil in nil_polygons:
        min_lon, min_lat, max_lon, max_lat = nil["bbox"]
        if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
            continue
        if point_in_geometry(lon, lat, nil["geometry"]):
            return nil
    return None


def infer_links(wikidata_path: Path, nil_geojson_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nil_polygons = load_nil_polygons(nil_geojson_path)
    places = load_retained_wikidata_places(wikidata_path)
    assignments: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    for place in places:
        nil = assign_nil(place, nil_polygons)
        if nil is None:
            unmatched.append(place)
            continue
        assignments.append({**place, "nil_id": nil["nil_id"], "nil_name": nil["nil_name"], "nil_iri": nil["iri"]})

    return assignments, unmatched


def write_links(assignments: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in assignments:
            entity = nt_uri(row["iri"])
            handle.write(f"{entity} <{EVT}inNIL> {nt_uri(row['nil_iri'])} .\n")
            handle.write(
                f"{entity} <{EVT}nilInferenceMethod> {nt_literal('point-in-polygon from Wikidata coordinates and Comune di Milano NIL polygons', lang='en')} .\n"
            )
            handle.write(f"{entity} <{EVT}inferredNILIdentifier> {nt_literal(row['nil_id'], datatype=XSD_STRING)} .\n")
            handle.write(f"{entity} <{EVT}inferredNILName> {nt_literal(row['nil_name'], lang='it')} .\n")


def write_report(assignments: list[dict[str, Any]], unmatched: list[dict[str, Any]], report_path: Path) -> None:
    report = {
        "assigned_count": len(assignments),
        "unmatched_count": len(unmatched),
        "unmatched": unmatched,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Infer NIL links for Eventour Wikidata places.")
    parser.add_argument("--wikidata-curated", required=True, help="Curated Wikidata JSONL")
    parser.add_argument("--nil-geojson", required=True, help="NIL GeoJSON polygons")
    parser.add_argument("--out", required=True, help="Output N-Triples file")
    parser.add_argument("--report", required=True, help="Output JSON report")
    args = parser.parse_args()

    assignments, unmatched = infer_links(Path(args.wikidata_curated), Path(args.nil_geojson))
    write_links(assignments, Path(args.out))
    write_report(assignments, unmatched, Path(args.report))
    print({"assigned_count": len(assignments), "unmatched_count": len(unmatched), "out": args.out, "report": args.report})


if __name__ == "__main__":
    main()

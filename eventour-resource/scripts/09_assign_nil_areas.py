#!/usr/bin/env python
"""Generate inferred NIL links for municipal entities and curated Wikidata places."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MUNICIPAL_TARGETS = (
    ("ds2484_alberi_20240331.geojson", "tree/{obj_id}", "obj_id"),
    ("ds2748_panchine.geojson", "bench/{obj_id}", "obj_id"),
    ("ds2749_tavoli_picnic.geojson", "picnic-table/{obj_id}", "obj_id"),
    ("tpl_fermate.geojson", "stop/surface/{id_amat}", "id_amat"),
    ("tpl_metrofermate.geojson", "stop/metro/{id_amat}", "id_amat"),
    ("bike_areesosta.geojson", "bicycle-parking-area/{id_amat}", "id_amat"),
    ("bikemi_stazioni.geojson", "bike-sharing-station/{id_amat}", "id_amat"),
    ("ds69_openwifi_layer_0_open_wifi_outdoor_4326_final.geojson", "wifi-access-point/{AP}", "AP"),
    ("park_interscambio.geojson", "parking-facility/interchange/{Nome}", "Nome"),
    ("park_pub.geojson", "parking-facility/public/{id}", "id"),
)


def run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default="data/source-snapshots/geojson")
    parser.add_argument("--curated-wikidata", default="curation/final/final-wikidata-places.jsonl")
    parser.add_argument("--output-dir", default="data/work")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    (ROOT / output_dir).mkdir(parents=True, exist_ok=True)
    nil_geojson = str(Path(args.datasets) / "ds964_nil_wm.geojson")

    municipal_cmd = [
        sys.executable,
        "scripts/municipal/infer_nil_spatial.py",
        "--nil",
        nil_geojson,
        "--datasets-dir",
        args.datasets,
        "--output",
        str(output_dir / "eventour_municipal_nil_inferred.nt"),
    ]
    for filename, uri_template, identifier_field in MUNICIPAL_TARGETS:
        municipal_cmd.extend(["--target", filename, uri_template, identifier_field])
    run(municipal_cmd)

    run(
        [
            sys.executable,
            "scripts/municipal/infer_wikidata_nil_links.py",
            "--wikidata-curated",
            args.curated_wikidata,
            "--nil-geojson",
            nil_geojson,
            "--out",
            str(output_dir / "eventour_wikidata_nil_links.nt"),
            "--report",
            str(output_dir / "eventour_wikidata_nil_links_report.json"),
        ]
    )


if __name__ == "__main__":
    main()

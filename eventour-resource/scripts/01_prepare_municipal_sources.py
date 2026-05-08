#!/usr/bin/env python
"""Check that the municipal GeoJSON source snapshots required by the release exist."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_GEOJSON = (
    "bike_areesosta.geojson",
    "bikemi_stazioni.geojson",
    "ds2484_alberi_20240331.geojson",
    "ds2748_panchine.geojson",
    "ds2749_tavoli_picnic.geojson",
    "ds290_economia_botteghe_storiche_2024.geojson",
    "ds630_servizi_igienici_pubblici_final.geojson",
    "ds69_openwifi_layer_0_open_wifi_outdoor_4326_final.geojson",
    "ds964_nil_wm.geojson",
    "park_interscambio.geojson",
    "park_pub.geojson",
    "ricarica_colonnine.geojson",
    "tpl_fermate.geojson",
    "tpl_metrofermate.geojson",
    "tpl_metroorari.geojson",
    "tpl_metropercorsi.geojson",
    "tpl_metrosequenza.geojson",
    "tpl_orari.geojson",
    "tpl_percorsi.geojson",
    "tpl_sequenza.geojson",
    "vedovelle_20260315-233003_final.geojson",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default="data/source-snapshots/geojson")
    args = parser.parse_args()

    datasets = Path(args.datasets)
    missing = [name for name in REQUIRED_GEOJSON if not (datasets / name).exists()]
    if missing:
        raise SystemExit(
            "Missing source snapshots in "
            f"{datasets}:\n"
            + "\n".join(f"- {name}" for name in missing)
            + "\n\nThe GitHub repository does not bundle raw Comune di Milano "
            "source snapshots. See data/source-snapshots/source-snapshots.csv "
            "for public dataset URLs, or run scripts/00_download_sources.py "
            "--download to populate this directory."
        )

    print(f"Found {len(REQUIRED_GEOJSON)} required municipal GeoJSON snapshots in {datasets}.")


if __name__ == "__main__":
    main()

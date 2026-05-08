# Municipal Source Catalog

This directory does not store the full Comune di Milano source datasets.
Instead, `source-snapshots.csv` records the public landing page, expected local
filename, feature count used in the Eventour v1.0.0 construction, snapshot
description, and transformation date for each of the 21 municipal datasets.

To rebuild the municipal layer locally, download the datasets into:

```text
data/source-snapshots/geojson/
```

The helper script can list or resolve the catalog:

```bash
python scripts/00_download_sources.py
python scripts/00_download_sources.py --download
```

Automatic downloading depends on the availability of machine-readable resource
metadata in the Comune di Milano open-data portal. If a dataset cannot be
resolved automatically, use the landing page in `source-snapshots.csv` and save
the GeoJSON with the `source_file` name shown in the catalog.

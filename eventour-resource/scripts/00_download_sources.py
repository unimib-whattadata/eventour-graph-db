#!/usr/bin/env python
"""Download or list the public municipal source datasets used by Eventour.

The GitHub repository intentionally does not store the full Comune di Milano
source snapshots. The source catalog in ``data/source-snapshots/source-snapshots.csv``
records the public landing page for each dataset. When ``--download`` is used,
this script resolves those landing pages through the Comune di Milano CKAN API
and downloads a GeoJSON resource when one is available.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen


CKAN_PACKAGE_SHOW = "https://dati.comune.milano.it/api/3/action/package_show?id={slug}"


def dataset_slug(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1]


def read_catalog(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fetch_json(url: str) -> dict:
    with urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def choose_resource(resources: list[dict]) -> dict | None:
    preferred_formats = ("geojson", "json", "csv")
    for preferred in preferred_formats:
        for resource in resources:
            fmt = str(resource.get("format", "")).lower()
            url = str(resource.get("url", ""))
            if preferred in fmt or url.lower().endswith(f".{preferred}"):
                return resource
    return resources[0] if resources else None


def download_file(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=120) as response:
        output.write_bytes(response.read())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/source-snapshots/source-snapshots.csv")
    parser.add_argument("--output-dir", default="data/source-snapshots/geojson")
    parser.add_argument("--download", action="store_true", help="Download source files instead of only listing URLs.")
    args = parser.parse_args()

    catalog = read_catalog(Path(args.catalog))
    output_dir = Path(args.output_dir)

    if not args.download:
        print("Comune di Milano source datasets used by Eventour:")
        for row in catalog:
            print(f"- {row['dataset_id']}: {row['source_url']}")
        print("\nUse --download to resolve CKAN resources and populate data/source-snapshots/geojson/.")
        return

    failures: list[str] = []
    for row in catalog:
        dataset_id = row["dataset_id"]
        slug = dataset_slug(row["source_url"])
        package_url = CKAN_PACKAGE_SHOW.format(slug=slug)
        output_path = output_dir / row["source_file"]
        try:
            metadata = fetch_json(package_url)
            resources = metadata.get("result", {}).get("resources", [])
            resource = choose_resource(resources)
            if not resource or not resource.get("url"):
                raise RuntimeError("no downloadable resource found")
            download_file(str(resource["url"]), output_path)
            print(f"{dataset_id}: downloaded {output_path}")
        except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as exc:
            failures.append(f"{dataset_id} ({row['source_url']}): {exc}")

    if failures:
        print("\nSome datasets could not be downloaded automatically:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

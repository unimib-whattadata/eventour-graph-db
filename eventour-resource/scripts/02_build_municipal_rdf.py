#!/usr/bin/env python
"""Build the municipal backbone RDF layers from released source snapshots."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default="data/source-snapshots/geojson")
    parser.add_argument("--mapping-dir", "--config", default="mappings/municipal")
    parser.add_argument("--output-dir", default="data/work")
    args = parser.parse_args()

    datasets = Path(args.datasets)
    mapping_dir = Path(args.mapping_dir)
    output_dir = Path(args.output_dir)
    (ROOT / output_dir).mkdir(parents=True, exist_ok=True)

    phases = (
        (
            "scripts/municipal/convert_phase1_streaming.py",
            mapping_dir / "phase1_admin_environment.yaml",
            output_dir / "eventour_phase1_data.nt",
        ),
        (
            "scripts/municipal/convert_phase2_transport_streaming.py",
            mapping_dir / "phase2_transport.yaml",
            output_dir / "eventour_phase2_transport_data.nt",
        ),
        (
            "scripts/municipal/convert_phase3_services_streaming.py",
            mapping_dir / "phase3_services_facilities.yaml",
            output_dir / "eventour_phase3_services_data.nt",
        ),
    )

    for script, mapping, output in phases:
        run(
            [
                sys.executable,
                script,
                "--datasets",
                str(datasets),
                "--mapping",
                str(mapping),
                "--output",
                str(output),
            ]
        )

    full_data = ROOT / output_dir / "eventour_municipal_backbone.nt"
    with full_data.open("wb") as out:
        for _, _, output in phases:
            with (ROOT / output).open("rb") as handle:
                out.write(handle.read())

    print(f"Wrote {full_data.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

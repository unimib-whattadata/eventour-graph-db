#!/usr/bin/env python
"""Create checksum entries for release files present in the repository."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKSUM_TARGETS = (
    "ontology/eventour.ttl",
    "ontology/eventour.nt",
    "metadata/eventour-catalog.ttl",
    "shapes/eventour-shapes.ttl",
    "queries/competency/all_competency_queries.rq",
    "data/sample/eventour-milan-sample.nt",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    lines: list[str] = []
    for rel in CHECKSUM_TARGETS:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"Missing checksum target: {rel}")
        lines.append(f"{sha256(path)}  {rel}")

    output = ROOT / "data/checksums-sha256.txt"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "metadata/checksums-sha256.txt").write_text(output.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")
    print("Before Zenodo release, add the checksum for the compressed full KG dump.")


if __name__ == "__main__":
    main()

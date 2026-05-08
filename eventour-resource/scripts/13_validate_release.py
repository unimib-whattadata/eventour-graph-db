#!/usr/bin/env python
"""Print the release validation summary."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    reports = Path("validation/reports")
    for name in [
        "rdf-parse-report.md",
        "geometry-validation-report.csv",
        "provenance-coverage-report.csv",
        "source-identity-report.csv",
        "nil-links-report.csv",
        "wikidata-identity-report.csv",
        "shacl-report.md",
    ]:
        path = reports / name
        print(f"== {path} ==")
        print(path.read_text(encoding="utf-8")[:2000])
        print()


if __name__ == "__main__":
    main()


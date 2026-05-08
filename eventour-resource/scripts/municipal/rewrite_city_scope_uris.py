"""Rewrite Eventour city resources from flat URIs to city-scoped URIs.

The converter output uses global ontology terms and many Milan-specific
resources under the same base URI. This streaming pass moves only known
city-resource subject/object prefixes under /{city}/ while leaving predicates,
classes, properties, and shared concept schemes untouched.
"""

from __future__ import annotations

import argparse
from pathlib import Path


BASE = "http://eventour.unimib.it/"

CITY_SCOPED_PREFIXES = {
    "activity",
    "bench",
    "bicycle-parking-area",
    "bike-sharing-station",
    "dataset",
    "distribution",
    "drinking-fountain",
    "ev-charging-station",
    "historic-shop",
    "municipality",
    "nil",
    "parking-facility",
    "picnic-table",
    "project",
    "public-toilet",
    "route-pattern",
    "service-pattern",
    "source-record",
    "stop",
    "stop-in-route",
    "timetable-summary",
    "transit-line",
    "tree",
    "wifi-access-point",
}


def rewrite_uri_token(token: str, *, city: str) -> tuple[str, bool]:
    prefix = f"<{BASE}"
    if not token.startswith(prefix) or not token.endswith(">"):
        return token, False

    path = token[len(prefix) : -1]
    if path.startswith(f"{city}/"):
        return token, False

    first_segment = path.split("/", 1)[0]
    if first_segment not in CITY_SCOPED_PREFIXES:
        return token, False

    return f"<{BASE}{city}/{path}>", True


def rewrite_nt_line(line: str, *, city: str) -> tuple[str, int]:
    parts = line.rstrip("\n").split(" ", 2)
    if len(parts) < 3:
        return line, 0

    replacements = 0
    subject, changed = rewrite_uri_token(parts[0], city=city)
    replacements += int(changed)

    # The predicate position is intentionally not rewritten: Eventour
    # predicates remain global ontology terms.
    predicate = parts[1]
    rest = parts[2]

    if rest.startswith("<"):
        object_token, separator, tail = rest.partition(" ")
        rewritten_object, changed = rewrite_uri_token(object_token, city=city)
        if changed:
            rest = rewritten_object + separator + tail
            replacements += 1

    return f"{subject} {predicate} {rest}\n", replacements


def rewrite_file(input_path: Path, output_path: Path, *, city: str) -> dict[str, int | str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    line_count = 0
    replacement_count = 0

    with input_path.open("r", encoding="utf-8") as source, output_path.open("w", encoding="utf-8") as target:
        for line in source:
            rewritten, replacements = rewrite_nt_line(line, city=city)
            target.write(rewritten)
            line_count += 1
            replacement_count += replacements

    return {
        "input": str(input_path),
        "output": str(output_path),
        "city": city,
        "lines": line_count,
        "rewritten_uri_occurrences": replacement_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite Eventour city resources under /{city}/.")
    parser.add_argument("--input", required=True, help="Input N-Triples file")
    parser.add_argument("--output", required=True, help="Output N-Triples file")
    parser.add_argument("--city", default="milan", help="City URI segment")
    args = parser.parse_args()

    summary = rewrite_file(Path(args.input), Path(args.output), city=args.city)
    print(summary)


if __name__ == "__main__":
    main()

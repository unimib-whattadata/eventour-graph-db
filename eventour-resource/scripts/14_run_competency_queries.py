#!/usr/bin/env python
"""Print expected competency-query results for the release."""

from pathlib import Path


def main() -> None:
    print(Path("queries/expected-results/runtime-summary.csv").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()


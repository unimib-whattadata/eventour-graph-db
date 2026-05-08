"""Export Wikidata SPARQL query files for a configured city profile."""

from __future__ import annotations

import argparse
from pathlib import Path

from eventour_kg.config.loaders import load_city_profile
from eventour_kg.extraction.wikidata import build_city_candidate_query, build_class_inventory_query


def export_queries(city_id: str, out_dir: Path) -> tuple[Path, Path]:
    profile = load_city_profile(city_id)
    if not profile.wikidata_qid:
        raise ValueError(f"City profile {city_id} has no Wikidata QID configured")

    language = profile.language_priority[0] if profile.language_priority else "en"
    candidate_query = build_city_candidate_query(profile.wikidata_qid, language=language)
    inventory_query = build_class_inventory_query(profile.wikidata_qid, language=language)

    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = out_dir / "wikidata_candidates.rq"
    inventory_path = out_dir / "wikidata_class_inventory.rq"
    candidate_path.write_text(candidate_query + "\n", encoding="utf-8")
    inventory_path.write_text(inventory_query + "\n", encoding="utf-8")
    return candidate_path, inventory_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export city-specific Wikidata SPARQL queries.")
    parser.add_argument("city_id", help="City profile identifier, e.g. milan")
    parser.add_argument("--out-dir", required=True, help="Directory where query files will be written")
    args = parser.parse_args()

    candidate_path, inventory_path = export_queries(args.city_id, Path(args.out_dir))
    print(f"Wrote {candidate_path}")
    print(f"Wrote {inventory_path}")


if __name__ == "__main__":
    main()

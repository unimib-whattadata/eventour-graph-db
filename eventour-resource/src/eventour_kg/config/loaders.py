"""Load and validate Eventour KG configuration artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
CITY_PROFILES_DIR = PACKAGE_ROOT / "config" / "city_profiles"


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    label: str
    format: str
    path: Path
    domain: str
    entity_family: str
    integration_role: str
    enabled: bool = True
    priority: str = "secondary"


@dataclass(frozen=True)
class CityProfile:
    city_id: str
    city_name: str
    country: str
    wikidata_qid: str | None
    language_priority: tuple[str, ...]
    boundary_strategy: str
    dataset_root: Path
    transport_gtfs_dir: Path | None
    sources: tuple[SourceConfig, ...]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_profile_path(city_id: str) -> Path:
    return CITY_PROFILES_DIR / f"{city_id}.json"


def load_city_profile(city_id: str) -> CityProfile:
    raw = _read_json(resolve_profile_path(city_id))
    dataset_root = Path(raw["dataset_root"])
    transport_gtfs_dir = raw.get("transport", {}).get("gtfs_dir")
    sources = []

    for source in raw["sources"]:
        sources.append(
            SourceConfig(
                source_id=source["source_id"],
                label=source["label"],
                format=source["format"],
                path=Path(source["path"]),
                domain=source["domain"],
                entity_family=source["entity_family"],
                integration_role=source["integration_role"],
                enabled=source.get("enabled", True),
                priority=source.get("priority", "secondary"),
            )
        )

    return CityProfile(
        city_id=raw["city_id"],
        city_name=raw["city_name"],
        country=raw["country"],
        wikidata_qid=raw.get("wikidata_qid"),
        language_priority=tuple(raw["language_priority"]),
        boundary_strategy=raw["boundary"]["strategy"],
        dataset_root=dataset_root,
        transport_gtfs_dir=Path(transport_gtfs_dir) if transport_gtfs_dir else None,
        sources=tuple(sources),
    )


def validate_city_profile(city_id: str) -> list[str]:
    profile = load_city_profile(city_id)
    errors: list[str] = []

    if not profile.dataset_root.exists():
        errors.append(f"Dataset root does not exist: {profile.dataset_root}")

    if profile.transport_gtfs_dir and not profile.transport_gtfs_dir.exists():
        errors.append(f"GTFS directory does not exist: {profile.transport_gtfs_dir}")

    for source in profile.sources:
        if source.enabled and not source.path.exists():
            errors.append(f"Missing source path: {source.source_id} -> {source.path}")

    return errors

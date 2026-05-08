"""Load source-specific field mappings used by the normalization layer."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
SOURCE_MAPPINGS_DIR = PROJECT_ROOT / "config" / "source_mappings"


@dataclass(frozen=True)
class FieldMapping:
    label_fields: tuple[str, ...] = ()
    label_template: str | None = None
    address_fields: tuple[str, ...] = ()
    address_template: str | None = None
    category_fields: tuple[str, ...] = ()
    category_literal: str | None = None
    status_fields: tuple[str, ...] = ()
    municipality_fields: tuple[str, ...] = ()
    nil_id_fields: tuple[str, ...] = ()
    nil_name_fields: tuple[str, ...] = ()
    longitude_fields: tuple[str, ...] = ()
    latitude_fields: tuple[str, ...] = ()
    extra_fields: dict[str, tuple[str, ...]] | None = None


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_source_mappings(version: str = "milan_v1") -> dict[str, FieldMapping]:
    raw = _read_json(SOURCE_MAPPINGS_DIR / f"{version}.json")
    mappings: dict[str, FieldMapping] = {}

    for source_id, spec in raw["sources"].items():
        extra_fields = {
            field_name: tuple(field_keys)
            for field_name, field_keys in spec.get("extra_fields", {}).items()
        }
        mappings[source_id] = FieldMapping(
            label_fields=tuple(spec.get("label_fields", [])),
            label_template=spec.get("label_template"),
            address_fields=tuple(spec.get("address_fields", [])),
            address_template=spec.get("address_template"),
            category_fields=tuple(spec.get("category_fields", [])),
            category_literal=spec.get("category_literal"),
            status_fields=tuple(spec.get("status_fields", [])),
            municipality_fields=tuple(spec.get("municipality_fields", [])),
            nil_id_fields=tuple(spec.get("nil_id_fields", [])),
            nil_name_fields=tuple(spec.get("nil_name_fields", [])),
            longitude_fields=tuple(spec.get("longitude_fields", [])),
            latitude_fields=tuple(spec.get("latitude_fields", [])),
            extra_fields=extra_fields,
        )

    return mappings

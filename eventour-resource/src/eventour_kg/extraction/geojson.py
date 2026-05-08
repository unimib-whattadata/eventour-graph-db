"""Helpers for reading local GeoJSON datasets without external dependencies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_geojson(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize_geojson(path: Path) -> dict[str, Any]:
    payload = load_geojson(path)
    features = payload.get("features", [])
    geometry_types = sorted(
        {
            (feature.get("geometry") or {}).get("type", "UNKNOWN")
            for feature in features
            if isinstance(feature, dict)
        }
    )
    property_keys = sorted(
        {
            key
            for feature in features
            for key in feature.get("properties", {}).keys()
            if isinstance(feature, dict)
        }
    )

    return {
        "path": str(path),
        "feature_count": len(features),
        "geometry_types": geometry_types,
        "property_keys": property_keys,
    }

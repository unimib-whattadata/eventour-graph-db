"""Conservative blocking helpers for same-entity matching."""

from __future__ import annotations

import re
from typing import Iterable


NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")


def normalize_name(value: str) -> str:
    lowered = value.strip().lower()
    return NON_ALNUM_RE.sub(" ", lowered).strip()


def name_block_keys(name: str) -> list[str]:
    normalized = normalize_name(name)
    if not normalized:
        return []

    tokens = normalized.split()
    keys = [normalized]
    if tokens:
        keys.append(tokens[0])
        keys.append(" ".join(tokens[:2]))
    return list(dict.fromkeys(keys))


def overlap(left: Iterable[str], right: Iterable[str]) -> bool:
    return not set(left).isdisjoint(set(right))

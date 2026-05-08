"""Shared RDF namespace constants for Eventour KG generation."""

from __future__ import annotations

from urllib.parse import urljoin


EVENTOUR_BASE = "http://eventour.unimib.it/"
ONTOLOGY_BASE = EVENTOUR_BASE
CITY_ID = "milan"
MILAN_KG_BASE = f"{EVENTOUR_BASE}{CITY_ID}/"
CONCEPT_BASE = EVENTOUR_BASE


def ontology_term(local_name: str) -> str:
    return urljoin(ONTOLOGY_BASE, local_name)


def milan_resource(*segments: str) -> str:
    cleaned = "/".join(segment.strip("/") for segment in segments if segment)
    return urljoin(MILAN_KG_BASE, cleaned)


def concept_resource(*segments: str) -> str:
    cleaned = "/".join(segment.strip("/") for segment in segments if segment)
    return urljoin(CONCEPT_BASE, cleaned)

"""Deterministic IRI builders for Eventour KG resources."""

from __future__ import annotations

import re

from eventour_kg.rdf.namespaces import concept_resource, milan_resource


_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def slug_segment(value: str) -> str:
    text = value.strip()
    text = text.replace(":", "-").replace("/", "-").replace("_", "-")
    text = _UNSAFE_RE.sub("-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "unknown"


def concept_segment(value: str) -> str:
    return slug_segment(value)


def build_entity_iri(source_id: str, record_id: str) -> str:
    return milan_resource("entity", slug_segment(source_id), slug_segment(record_id))


def build_geometry_iri(source_id: str, record_id: str) -> str:
    return milan_resource("geometry", slug_segment(source_id), slug_segment(record_id))


def build_gtfs_stop_iri(stop_id: str) -> str:
    return milan_resource("entity", "gtfs-stop", slug_segment(stop_id))


def build_gtfs_route_iri(route_id: str) -> str:
    return milan_resource("route", "gtfs", slug_segment(route_id))


def build_category_iri(category_id: str) -> str:
    return concept_resource("category", concept_segment(category_id))


def build_curation_label_iri(label_id: str) -> str:
    return concept_resource("curation-label", concept_segment(label_id))


def build_eventour_role_iri(role_id: str) -> str:
    return concept_resource("role", concept_segment(role_id))


def build_source_iri(source_id: str) -> str:
    return milan_resource("source", slug_segment(source_id))

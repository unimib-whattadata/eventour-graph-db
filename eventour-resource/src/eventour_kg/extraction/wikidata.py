"""Build SPARQL queries for Wikidata candidate extraction and parse WDQS values."""

from __future__ import annotations

import re


ENTITY_URI_RE = re.compile(r"/([PQ]\d+)$")
POINT_WKT_RE = re.compile(r"Point\(([-0-9.]+)\s+([-0-9.]+)\)")


def build_city_candidate_query(city_qid: str, language: str = "it") -> str:
    return f"""
PREFIX schema: <http://schema.org/>

SELECT DISTINCT
  ?item ?itemLabel ?itemDescription ?coord
  ?directClass ?directClassLabel
WHERE {{
  ?item wdt:P625 ?coord ;
        wdt:P131+ wd:{city_qid} ;
        wdt:P31 ?directClass .

  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],{language},en" .
    ?item rdfs:label ?itemLabel .
    ?item schema:description ?itemDescription .
    ?directClass rdfs:label ?directClassLabel .
  }}
}}
ORDER BY ?itemLabel
LIMIT 10000
""".strip()


def build_class_inventory_query(city_qid: str, language: str = "it") -> str:
    return f"""
SELECT ?directClass ?directClassLabel (COUNT(DISTINCT ?item) AS ?count)
WHERE {{
  ?item wdt:P625 ?coord ;
        wdt:P131+ wd:{city_qid} ;
        wdt:P31 ?directClass .

  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],{language},en" .
  }}
}}
GROUP BY ?directClass ?directClassLabel
ORDER BY DESC(?count)
LIMIT 1000
""".strip()


def build_entity_subgraph_query(item_qids: list[str], language: str = "it") -> str:
    values = " ".join(f"wd:{item_qid}" for item_qid in item_qids)
    return f"""
PREFIX schema: <http://schema.org/>

SELECT
  ?item ?property ?propertyLabel
  ?valueEntity ?valueEntityLabel
  ?valueLiteral ?valueDatatype ?valueLang
WHERE {{
  VALUES ?item {{ {values} }}

  ?property wikibase:directClaim ?wdt .
  ?item ?wdt ?value .

  OPTIONAL {{
    FILTER(isIRI(?value))
    BIND(?value AS ?valueEntity)
  }}

  OPTIONAL {{
    FILTER(isLiteral(?value))
    BIND(STR(?value) AS ?valueLiteral)
    BIND(DATATYPE(?value) AS ?valueDatatype)
    BIND(LANG(?value) AS ?valueLang)
  }}

  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],{language},en" .
    ?property rdfs:label ?propertyLabel .
    ?valueEntity rdfs:label ?valueEntityLabel .
  }}
}}
ORDER BY ?item ?property ?valueEntity ?valueLiteral
""".strip()


def build_property_catalog_query(property_qids: list[str], language: str = "it") -> str:
    values = " ".join(f"wd:{property_qid}" for property_qid in property_qids)
    return f"""
PREFIX schema: <http://schema.org/>

SELECT
  ?property ?propertyLabel ?propertyDescription
  ?propertyType ?propertyTypeLabel
WHERE {{
  VALUES ?property {{ {values} }}

  OPTIONAL {{ ?property wikibase:propertyType ?propertyType . }}

  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],{language},en" .
    ?property rdfs:label ?propertyLabel .
    ?property schema:description ?propertyDescription .
    ?propertyType rdfs:label ?propertyTypeLabel .
  }}
}}
ORDER BY ?property
""".strip()


def build_class_ancestor_query(class_qids: list[str], language: str = "it") -> str:
    values = " ".join(f"wd:{class_qid}" for class_qid in class_qids)
    return f"""
PREFIX schema: <http://schema.org/>

SELECT
  ?directClass ?directClassLabel
  ?ancestorClass ?ancestorClassLabel
WHERE {{
  VALUES ?directClass {{ {values} }}

  OPTIONAL {{ ?directClass wdt:P279 ?ancestorClass . }}

  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],{language},en" .
    ?directClass rdfs:label ?directClassLabel .
    ?ancestorClass rdfs:label ?ancestorClassLabel .
  }}
}}
ORDER BY ?directClass ?ancestorClass
""".strip()


def qid_from_uri(value: str | None) -> str | None:
    if not value:
        return None
    match = ENTITY_URI_RE.search(value)
    if match:
        return match.group(1)
    if value[:1] in {"Q", "P"} and value[1:].isdigit():
        return value
    return None


def term_from_uri(value: str | None) -> str | None:
    if not value:
        return None
    if "#" in value:
        return value.rsplit("#", 1)[-1] or None
    if "/" in value:
        return value.rsplit("/", 1)[-1] or None
    return value or None


def parse_wkt_point(value: str | None) -> tuple[float | None, float | None]:
    if not value:
        return None, None
    match = POINT_WKT_RE.search(value)
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))

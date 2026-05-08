"""Classifier backends for Eventour semantic curation."""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Any

from eventour_kg.classification.policy import ClassificationResult, Decision
from eventour_kg.classification.openai_backend import OpenAIBackend


def _fold(values: list[str]) -> str:
    return " | ".join(value.lower() for value in values if value)


def _labels_from_section(items: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for item in items:
        value = item.get(key)
        if value:
            values.append(str(value))
    return values


class ClassifierBackend(ABC):
    name: str

    @abstractmethod
    def classify(self, entity: dict[str, Any]) -> ClassificationResult:
        raise NotImplementedError


class HeuristicBackend(ClassifierBackend):
    name = "heuristic_v1"

    transport_keywords = {
        "stazione metropolitana",
        "stazione sotterranea",
        "fermata dell'autobus",
        "stazione ferroviaria",
        "stazione di interscambio",
        "tram stop",
        "railway station",
        "metro station",
    }
    context_keywords = {
        "quartiere",
        "quartiere di milano",
        "rione",
        "distretto storico",
        "chinatown",
        "innovation district",
        "arts district",
        "borgo",
    }
    exclude_keywords = {
        "stagione sportiva",
        "campionati",
        "società sportiva",
        "societa sportiva",
        "organizzazione",
        "movimento artistico",
        "marchio di moda",
        "art publisher",
        "strada urbana",
        "scuola primaria",
        "scuola privata",
        "evento",
        "sports event",
        "brand",
    }
    candidate_keywords = {
        "edificio",
        "casa",
        "edificio per uffici",
        "casa multifamiliare",
        "edificio abitativo",
        "complesso residenziale",
        "grattacielo",
        "palazzina",
        "abitazione",
        "edificio pubblico",
        "attrazione turistica",
    }
    positive_ambiguity_signals = {
        "storic",
        "historic",
        "heritage",
        "palazzo comunale",
        "palazzo cittadino",
        "residenza reale",
        "city hall",
        "royal",
        "museo",
        "landmark",
        "monument",
        "cathedral",
        "basilica",
    }

    category_rules = (
        ("museum_collection", {"museo", "pinacoteca", "casa museo", "antiquarium", "museum", "museo etnografico", "museo archeologico", "museo storico", "museo diocesano", "museo egizio", "museo locale", "museo universitario", "museo nazionale italiano", "museo del design"}),
        ("gallery_art_space", {"galleria d'arte", "commercial art gallery", "galleria di arte fotografica", "edificio museale"}),
        ("religious_heritage", {"chiesa", "basilica", "basilica minore", "duomo", "cattedrale", "cattedrale cattolica", "santuario", "abbazia", "certosa", "convento", "monastero", "cappella", "battistero", "sinagoga", "chiesa protestante", "chiesa abbaziale", "chiesa cattolica", "chiesa parrocchiale", "chiesa parrocchiale cattolica"}),
        ("historic_architecture", {"palazzo", "villa", "castello", "edificio storico", "edificio civile storico", "villino", "casa di ringhiera", "residenza reale", "palazzo comunale", "palazzo cittadino", "complesso di edifici"}),
        ("monument_memorial", {"monumento", "monumento commemorativo", "memoriale di guerra", "monumento votivo", "monumento storico", "targa commemorativa", "pietra commemorativa", "monumento ai caduti", "mausoleo"}),
        ("public_art", {"scultura", "statua", "outdoor sculpture", "murale", "installazione", "fontana", "affresco", "dipinto murale", "gruppo di sculture", "opera d'arte"}),
        ("archaeological_ancient_site", {"sito archeologico", "anfiteatro romano", "teatro romano", "terme romane", "città romana", "città antica", "ancient roman imperial palace", "rovine", "parco archeologico", "circo romano", "edificio romano"}),
        ("urban_landmark", {"piazza", "porta cittadina", "arco trionfale", "torre", "torre campanaria", "mura", "baluardo", "fortificazione", "loggia", "colonnato", "portico", "broletto", "piazza della cattedrale", "piazza della chiesa"}),
        ("performing_arts_entertainment", {"teatro", "teatro d'opera", "cinema", "cineteca", "cabaret", "locale di pubblico spettacolo", "cinema multisala"}),
        ("park_garden_nature", {"parco cittadino", "parco", "giardino cittadino", "giardino pubblico", "orto botanico", "parco naturale", "verde urbano", "pianta monumentale", "giardino zoologico"}),
        ("cemetery_funerary_heritage", {"cimitero", "cimitero monumentale", "cimitero di guerra", "ossario", "cripta", "sepoltura", "cappella cimiteriale"}),
        ("science_education_attraction", {"planetario", "osservatorio astronomico", "acquario", "museo scientifico", "museo della tecnologia", "museo di strumenti musicali", "museo dello sport"}),
        ("special_interest_attraction", {"ippodromo", "stadio del ghiaccio", "punto di vista panoramico", "lungofiume", "canale artificiale", "porto naturale", "veliero", "preserved watercraft"}),
    )

    def classify(self, entity: dict[str, Any]) -> ClassificationResult:
        label = (entity.get("preferred_label") or "").strip()
        description = (entity.get("description") or "").strip()
        payload = entity.get("classification_payload") or {}
        class_labels = list(entity.get("direct_class_labels") or [])
        if not class_labels:
            class_labels.extend(_labels_from_section(entity.get("direct_classes") or [], "label"))
        class_labels.extend(payload.get("direct_class_labels") or [])
        ancestor_labels = payload.get("class_ancestor_labels") or _labels_from_section(entity.get("class_ancestors") or [], "label")
        semantic_fact_texts = payload.get("semantic_fact_texts") or _labels_from_section(entity.get("semantic_facts") or [], "prompt_text")
        combined = _fold([label, description, *class_labels, *ancestor_labels, *semantic_fact_texts])

        if any(keyword in combined for keyword in self.transport_keywords):
            return ClassificationResult(
                decision=Decision.EXCLUDE,
                eventour_category=None,
                confidence=0.98,
                rationale="Transport infrastructure is handled by dedicated local mobility datasets.",
                backend=self.name,
            )

        if any(keyword in combined for keyword in self.exclude_keywords):
            return ClassificationResult(
                decision=Decision.EXCLUDE,
                eventour_category=None,
                confidence=0.97,
                rationale="The entity is an event, organization, brand, or other non-place concept.",
                backend=self.name,
            )

        if any(keyword in combined for keyword in self.context_keywords):
            return ClassificationResult(
                decision=Decision.KEEP_CONTEXT,
                eventour_category=None,
                confidence=0.93,
                rationale="The entity is useful as district or urban context rather than as a primary POI.",
                backend=self.name,
            )

        for category, keywords in self.category_rules:
            if any(keyword in combined for keyword in keywords):
                return ClassificationResult(
                    decision=Decision.KEEP_POI,
                    eventour_category=category,
                    confidence=0.94,
                    rationale=f"The entity matches the {category} category through its classes or description.",
                    backend=self.name,
                )

        if any(keyword in combined for keyword in self.candidate_keywords):
            if any(signal in combined for signal in self.positive_ambiguity_signals):
                return ClassificationResult(
                    decision=Decision.KEEP_POI,
                    eventour_category="historic_architecture",
                    confidence=0.84,
                    rationale="The entity has an ambiguous building-like class but the description suggests cultural or historic relevance.",
                    backend=self.name,
                )
            return ClassificationResult(
                decision=Decision.CANDIDATE_EXCEPTION,
                eventour_category=None,
                confidence=0.74,
                rationale="The entity belongs to a generic or ambiguous building-like class and should be reviewed.",
                backend=self.name,
            )

        if "attrazione turistica" in combined or "tourist attraction" in combined:
            return ClassificationResult(
                decision=Decision.CANDIDATE_EXCEPTION,
                eventour_category=None,
                confidence=0.68,
                rationale="Touristic relevance is suggested, but the semantic type is too broad for automatic acceptance.",
                backend=self.name,
            )

        return ClassificationResult(
            decision=Decision.EXCLUDE,
            eventour_category=None,
            confidence=0.65,
            rationale="No strong Eventour-relevant semantic signal was found in the current metadata.",
            backend=self.name,
        )


def get_backend(name: str) -> ClassifierBackend:
    if name == "heuristic":
        return HeuristicBackend()
    if name == "openai":
        return OpenAIBackend()
    if name.startswith("openai:"):
        _, model = name.split(":", 1)
        return OpenAIBackend(model=model or os.getenv("EVENTOUR_OPENAI_MODEL"))
    raise ValueError(f"Unsupported backend: {name}")

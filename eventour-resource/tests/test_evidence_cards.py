from __future__ import annotations

import unittest

from eventour_kg.classification.backends import HeuristicBackend
from eventour_kg.classification.evidence_cards import (
    build_classification_payload,
    build_evidence_card,
)
from eventour_kg.classification.prompt_builder import build_prompt


def _claim(
    property_qid: str,
    property_label: str,
    *,
    value_type: str,
    value_qid: str | None = None,
    value_label: str | None = None,
    value_literal: str | None = None,
    value_datatype: str | None = None,
    value_lang: str | None = None,
) -> dict[str, object]:
    return {
        "property_qid": property_qid,
        "property_label": property_label,
        "value_type": value_type,
        "value_qid": value_qid,
        "value_label": value_label,
        "value_literal": value_literal,
        "value_datatype": value_datatype,
        "value_lang": value_lang,
    }


class EvidenceCardTests(unittest.TestCase):
    def test_build_evidence_card_selects_ranked_nonredundant_facts(self) -> None:
        entity = {
            "city_id": "milan",
            "item_qid": "QTEST1",
            "item_uri": "http://www.wikidata.org/entity/QTEST1",
            "preferred_label": "Casa Example",
            "description": "historic building in Milan",
            "direct_class_qids": ["Q41176"],
            "direct_class_labels": ["edificio"],
            "claims": [
                _claim("P31", "istanza di", value_type="wikibase-item", value_qid="Q41176", value_label="edificio"),
                _claim("P1435", "designazione del bene culturale", value_type="wikibase-item", value_qid="Q100", value_label="monumento culturale"),
                _claim("P84", "architetto", value_type="wikibase-item", value_qid="Q200", value_label="Giuseppe Rossi"),
                _claim("P131", "unità amministrativa in cui è situato", value_type="wikibase-item", value_qid="Q490", value_label="Milano"),
                _claim("P17", "Paese", value_type="wikibase-item", value_qid="Q38", value_label="Italia"),
                _claim("P361", "parte di", value_type="wikibase-item", value_qid="Q300", value_label="Brera"),
                _claim("P149", "stile architettonico", value_type="wikibase-item", value_qid="Q400", value_label="neoclassicismo"),
                _claim("P571", "data di fondazione o creazione", value_type="time", value_literal="1890-01-01T00:00:00Z"),
                _claim("P6375", "indirizzo", value_type="monolingualtext", value_literal="Via Example 10"),
                _claim("P276", "luogo", value_type="wikibase-item", value_qid="Q300", value_label="Brera"),
            ],
        }
        class_ancestor_index = {
            "Q41176": {
                "direct_class_qid": "Q41176",
                "direct_class_label": "edificio",
                "ancestors": [
                    {"qid": "Q811979", "label": "struttura architettonica"},
                ],
            }
        }
        property_idf = {
            "P1435": 1.0,
            "P84": 0.95,
            "P149": 0.9,
            "P361": 0.85,
            "P6375": 0.7,
            "P571": 0.6,
            "P131": 0.2,
            "P17": 0.1,
            "P276": 0.2,
        }
        object_idf = {
            "Q100": 1.0,
            "Q200": 0.95,
            "Q300": 0.5,
            "Q400": 0.92,
            "Q490": 0.1,
            "Q38": 0.05,
            "literal:Via Example 10": 0.8,
            "literal:1890-01-01T00:00:00Z": 0.65,
        }

        card = build_evidence_card(
            entity,
            class_ancestor_index=class_ancestor_index,
            property_idf=property_idf,
            object_idf=object_idf,
        )

        self.assertEqual([item["label"] for item in card["direct_classes"]], ["edificio"])
        self.assertEqual([item["label"] for item in card["class_ancestors"]], ["struttura architettonica"])

        fact_texts = [fact["prompt_text"] for fact in card["semantic_facts"]]
        self.assertIn("designazione del bene culturale: monumento culturale", fact_texts)
        self.assertIn("architetto: Giuseppe Rossi", fact_texts)
        self.assertIn("stile architettonico: neoclassicismo", fact_texts)
        self.assertNotIn("istanza di: edificio", fact_texts)
        self.assertLessEqual(len(fact_texts), 8)
        self.assertLessEqual(sum("Milano" in text or "Italia" in text or "Brera" in text for text in fact_texts), 2)

        property_counts: dict[str, int] = {}
        for fact in card["semantic_facts"]:
            property_counts[fact["property_qid"]] = property_counts.get(fact["property_qid"], 0) + 1
            self.assertIn(fact["tier"], {"A", "B", "C"})
        self.assertTrue(all(count <= 2 for count in property_counts.values()))
        self.assertEqual(len(fact_texts), len(set(fact_texts)))

    def test_build_classification_payload_uses_labels_only(self) -> None:
        card = {
            "city_id": "milan",
            "preferred_label": "Casa Example",
            "description": "historic building in Milan",
            "direct_classes": [{"qid": "Q1", "label": "edificio"}],
            "class_ancestors": [{"qid": "Q2", "label": "struttura architettonica", "source_direct_class_qids": ["Q1"]}],
            "semantic_facts": [
                {
                    "property_qid": "P84",
                    "property_label": "architetto",
                    "value_qid": "Q3",
                    "value_label": "Giuseppe Rossi",
                    "value_literal": None,
                    "prompt_text": "architetto: Giuseppe Rossi",
                    "tier": "A",
                    "rank_features": {},
                }
            ],
        }

        payload = build_classification_payload(card)

        self.assertEqual(payload["city_name"], "milan")
        self.assertEqual(payload["entity_label"], "Casa Example")
        self.assertEqual(payload["entity_description"], "historic building in Milan")
        self.assertEqual(payload["direct_class_labels"], ["edificio"])
        self.assertEqual(payload["class_ancestor_labels"], ["struttura architettonica"])
        self.assertEqual(payload["semantic_fact_texts"], ["architetto: Giuseppe Rossi"])
        self.assertNotIn("Q1", str(payload))
        self.assertNotIn("Q2", str(payload))
        self.assertNotIn("Q3", str(payload))

    def test_prompt_builder_prefers_existing_classification_payload(self) -> None:
        entity = {
            "city_id": "milan",
            "preferred_label": "Casa Example",
            "description": "historic building in Milan",
            "classification_payload": {
                "city_name": "milan",
                "entity_label": "Casa Example",
                "entity_description": "historic building in Milan",
                "direct_class_labels": ["edificio"],
                "class_ancestor_labels": ["struttura architettonica"],
                "semantic_fact_texts": ["architetto: Giuseppe Rossi"],
            },
        }

        prompt = build_prompt(entity)

        self.assertIn('"class_ancestor_labels"', prompt)
        self.assertIn('"semantic_fact_texts"', prompt)
        self.assertIn("architetto: Giuseppe Rossi", prompt)
        self.assertNotIn('"Q1"', prompt)

    def test_heuristic_backend_reads_evidence_payload_signals(self) -> None:
        entity = {
            "preferred_label": "Museo Example",
            "description": "cultural site",
            "classification_payload": {
                "direct_class_labels": ["museo"],
                "class_ancestor_labels": ["istituzione culturale"],
                "semantic_fact_texts": ["designazione del patrimonio: monumento culturale"],
            },
        }

        result = HeuristicBackend().classify(entity)

        self.assertEqual(result.decision.value, "keep_poi")
        self.assertEqual(result.eventour_category, "museum_collection")

    def test_datetime_literals_are_rendered_as_compact_dates(self) -> None:
        entity = {
            "city_id": "milan",
            "item_qid": "QDATE1",
            "item_uri": "http://www.wikidata.org/entity/QDATE1",
            "preferred_label": "Casa Date",
            "description": "historic house",
            "direct_class_qids": ["Q41176"],
            "direct_class_labels": ["edificio"],
            "claims": [
                {
                    "property_qid": "P571",
                    "property_label": "data di fondazione o creazione",
                    "value_type": "literal",
                    "value_qid": None,
                    "value_label": None,
                    "value_literal": "1923-01-01T00:00:00Z",
                    "value_datatype": "http://www.w3.org/2001/XMLSchema#dateTime",
                }
            ],
        }

        card = build_evidence_card(
            entity,
            class_ancestor_index={"Q41176": {"ancestors": []}},
            property_idf={"P571": 0.8},
            object_idf={"literal:1923-01-01T00:00:00Z": 0.9},
        )

        self.assertEqual(card["semantic_facts"][0]["prompt_text"], "data di fondazione o creazione: 1923-01-01")
        self.assertEqual(card["semantic_facts"][0]["tier"], "B")

    def test_country_and_city_facts_are_not_selected_when_richer_facts_exist(self) -> None:
        entity = {
            "city_id": "milan",
            "item_qid": "QLOC1",
            "item_uri": "http://www.wikidata.org/entity/QLOC1",
            "preferred_label": "Evento Example",
            "description": "sporting event in Milan",
            "direct_class_qids": ["Q27020041"],
            "direct_class_labels": ["stagione sportiva"],
            "claims": [
                _claim("P17", "Paese", value_type="wikibase-item", value_qid="Q38", value_label="Italia"),
                _claim("P276", "luogo", value_type="wikibase-item", value_qid="Q490", value_label="Milano"),
                _claim("P580", "data di inizio", value_type="literal", value_literal="1957-08-25T00:00:00Z", value_datatype="http://www.w3.org/2001/XMLSchema#dateTime"),
                _claim("P582", "data di fine", value_type="literal", value_literal="1957-08-30T00:00:00Z", value_datatype="http://www.w3.org/2001/XMLSchema#dateTime"),
                _claim("P1132", "numero di partecipanti", value_type="literal", value_literal="635"),
            ],
        }

        card = build_evidence_card(
            entity,
            class_ancestor_index={},
            property_idf={"P17": 0.0, "P276": 0.2, "P580": 0.8, "P582": 0.82, "P1132": 0.9},
            object_idf={
                "Q38": 0.0,
                "Q490": 0.01,
                "literal:1957-08-25T00:00:00Z": 1.0,
                "literal:1957-08-30T00:00:00Z": 1.0,
                "literal:635": 1.0,
            },
        )

        fact_texts = [fact["prompt_text"] for fact in card["semantic_facts"]]
        self.assertNotIn("Paese: Italia", fact_texts)
        self.assertNotIn("luogo: Milano", fact_texts)
        self.assertIn("data di inizio: 1957-08-25", fact_texts)
        self.assertIn("data di fine: 1957-08-30", fact_texts)

    def test_city_location_can_survive_as_single_fallback_when_no_better_fact_exists(self) -> None:
        entity = {
            "city_id": "milan",
            "item_qid": "QLOC2",
            "item_uri": "http://www.wikidata.org/entity/QLOC2",
            "preferred_label": "Luogo Example",
            "description": "generic place in Milan",
            "direct_class_qids": ["Q41176"],
            "direct_class_labels": ["edificio"],
            "claims": [
                _claim("P17", "Paese", value_type="wikibase-item", value_qid="Q38", value_label="Italia"),
                _claim("P131", "unità amministrativa in cui è situato", value_type="wikibase-item", value_qid="Q490", value_label="Milano"),
            ],
        }

        card = build_evidence_card(
            entity,
            class_ancestor_index={},
            property_idf={"P17": 0.0, "P131": 0.1},
            object_idf={"Q38": 0.0, "Q490": 0.01},
        )

        fact_texts = [fact["prompt_text"] for fact in card["semantic_facts"]]
        self.assertNotIn("Paese: Italia", fact_texts)
        self.assertEqual(fact_texts, ["unità amministrativa in cui è situato: Milano"])


if __name__ == "__main__":
    unittest.main()

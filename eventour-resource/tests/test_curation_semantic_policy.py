from __future__ import annotations

import unittest

from eventour_kg.curation.semantic_policy import (
    apply_semantic_policy,
    match_policy_groups,
    resolve_policy_groups,
)


def make_entity(
    *,
    preferred_label: str = "",
    description: str = "",
    direct_labels: list[str] | None = None,
    ancestor_labels: list[str] | None = None,
    fact_texts: list[str] | None = None,
) -> dict[str, object]:
    return {
        "preferred_label": preferred_label,
        "description": description,
        "direct_classes": [{"label": label} for label in (direct_labels or [])],
        "class_ancestors": [{"label": label} for label in (ancestor_labels or [])],
        "semantic_facts": [{"prompt_text": text} for text in (fact_texts or [])],
    }


class SemanticPolicyTests(unittest.TestCase):
    def test_basic_groups_match_expected_defaults(self) -> None:
        cases = [
            (
                "religious_sites",
                "primary_poi",
                make_entity(description="historic church in Milan", direct_labels=["church"]),
            ),
            (
                "historic_buildings_palazzi",
                "primary_poi",
                make_entity(preferred_label="Palazzo Marino", ancestor_labels=["palazzo"]),
            ),
            (
                "cinemas_theatres_performance",
                "primary_poi",
                make_entity(description="cinema di Milano", direct_labels=["cinema"]),
            ),
            (
                "named_urban_landmarks",
                "primary_poi",
                make_entity(
                    preferred_label="Arco della Pace",
                    fact_texts=["instance described as a landmark in the city center"],
                ),
            ),
            (
                "libraries_archives",
                "secondary_poi",
                make_entity(description="biblioteca italiana", direct_labels=["biblioteca"]),
            ),
            (
                "institutional_education",
                "context_entity",
                make_entity(description="public university in Milan", direct_labels=["university"]),
            ),
            (
                "branded_venues",
                "exclude",
                make_entity(preferred_label="Apple Store Piazza Liberty", direct_labels=["store"]),
            ),
            (
                "hotels_lodging",
                "exclude",
                make_entity(description="hotel in Milan", direct_labels=["albergo"]),
            ),
        ]

        for expected_group, expected_label, entity in cases:
            with self.subTest(group=expected_group):
                groups = match_policy_groups(entity)
                result = resolve_policy_groups(groups)

                self.assertIn(expected_group, groups)
                self.assertEqual(result["policy_group"], expected_group)
                self.assertEqual(result["final_label"], expected_label)

    def test_multi_match_prefers_higher_priority_and_stricter_cap(self) -> None:
        entity = make_entity(
            preferred_label="Biblioteca dell'Accademia",
            description="library of a university academy in Milan",
            direct_labels=["library"],
            ancestor_labels=["academy"],
            fact_texts=["part of the university institution and archive services"],
        )

        groups = match_policy_groups(entity)
        result = resolve_policy_groups(groups)

        self.assertIn("libraries_archives", groups)
        self.assertIn("institutional_education", groups)
        self.assertEqual(result["policy_group"], "institutional_education")
        self.assertEqual(result["final_label"], "context_entity")

    def test_apply_semantic_policy_returns_structured_resolution(self) -> None:
        entity = make_entity(description="cinema di Milano", direct_labels=["cinema"])

        result = apply_semantic_policy(entity)

        self.assertEqual(result["matched_groups"], ["cinemas_theatres_performance"])
        self.assertEqual(result["policy_group"], "cinemas_theatres_performance")
        self.assertEqual(result["final_label"], "primary_poi")

    def test_boundary_matching_avoids_false_positive_landmark_and_performance_hits(self) -> None:
        archive_entity = make_entity(
            preferred_label="Archivio di Stato di Milano",
            description="archivio di Stato italiano",
            direct_labels=["archive"],
        )
        operator_entity = make_entity(
            preferred_label="Affori FN",
            description="stazione della metropolitana di Milano",
            fact_texts=["operator: Azienda Trasporti Milanesi"],
        )

        archive_groups = match_policy_groups(archive_entity)
        operator_groups = match_policy_groups(operator_entity)

        self.assertIn("libraries_archives", archive_groups)
        self.assertNotIn("named_urban_landmarks", archive_groups)
        self.assertNotIn("cinemas_theatres_performance", operator_groups)

    def test_boundary_matching_avoids_workshop_false_positive_brand_match(self) -> None:
        entity = make_entity(
            preferred_label="Community Workshop",
            description="community workshop space for neighborhood activities",
        )

        groups = match_policy_groups(entity)

        self.assertNotIn("branded_venues", groups)


if __name__ == "__main__":
    unittest.main()

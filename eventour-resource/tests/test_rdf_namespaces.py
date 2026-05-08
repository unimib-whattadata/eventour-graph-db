from __future__ import annotations

import unittest

from eventour_kg.rdf.iris import (
    build_category_iri,
    build_curation_label_iri,
    build_entity_iri,
    build_eventour_role_iri,
    build_geometry_iri,
    build_gtfs_route_iri,
    build_gtfs_stop_iri,
)
from eventour_kg.rdf.namespaces import MILAN_KG_BASE, ONTOLOGY_BASE, CITY_ID


class RdfNamespaceTests(unittest.TestCase):
    def test_namespace_constants_match_eventour_bases(self) -> None:
        self.assertEqual(ONTOLOGY_BASE, "http://eventour.unimib.it/")
        self.assertEqual(MILAN_KG_BASE, "http://eventour.unimib.it/milan/")
        self.assertEqual(CITY_ID, "milan")

    def test_entity_and_geometry_iris_are_deterministic_and_uri_safe(self) -> None:
        self.assertEqual(
            build_entity_iri("historic_shops", "historic_shops:1"),
            "http://eventour.unimib.it/milan/entity/historic-shops/historic-shops-1",
        )
        self.assertEqual(
            build_geometry_iri("historic_shops", "historic_shops:1"),
            "http://eventour.unimib.it/milan/geometry/historic-shops/historic-shops-1",
        )

    def test_gtfs_and_category_iris_are_deterministic(self) -> None:
        self.assertEqual(
            build_gtfs_stop_iri("1234"),
            "http://eventour.unimib.it/milan/entity/gtfs-stop/1234",
        )
        self.assertEqual(
            build_gtfs_route_iri("M1"),
            "http://eventour.unimib.it/milan/route/gtfs/M1",
        )
        self.assertEqual(
            build_category_iri("historic_architecture"),
            "http://eventour.unimib.it/category/historic-architecture",
        )
        self.assertEqual(
            build_curation_label_iri("primary_poi"),
            "http://eventour.unimib.it/curation-label/primary-poi",
        )
        self.assertEqual(
            build_eventour_role_iri("secondary_poi"),
            "http://eventour.unimib.it/role/secondary-poi",
        )


if __name__ == "__main__":
    unittest.main()

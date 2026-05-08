# Eventour Milan KG Resource Statistics

Generated from `eventour_final_kg_milan.nt` on 2026-05-03. Ontology and metadata counts updated on 2026-05-05.

## Release Files

| Artifact | Path | Size | Count |
|---|---:|---:|---:|
| Final merged KG | `eventour_converter_starter/output/eventour_final_kg_milan.nt` | 1,379,859,675 bytes | 9,374,065 triples |
| Final ontology, Turtle | `eventour_converter_starter/output/eventour_final_ontology.ttl` | 28,079 bytes | 593 triples |
| Final ontology, N-Triples | `eventour_converter_starter/output/eventour_final_ontology.nt` | 81,751 bytes | 593 triples |
| VoID/DCAT metadata | `eventour_converter_starter/output/eventour_metadata_void_dcat.ttl` | see file | 199 triples |
| SHACL shapes | `eventour_converter_starter/output/eventour_shapes.ttl` | see file | validation shapes |
| Wikidata NIL links | `eventour_converter_starter/output/eventour_wikidata_nil_links.nt` | 2,026,747 bytes | 13,152 triples |

## KG Size

| Statistic | Value |
|---|---:|
| Triples | 9,374,065 |
| Distinct subjects | 906,923 |
| Distinct URI objects | 906,945 |
| Distinct predicates | 134 |
| Distinct Eventour predicates used | 91 |
| Official source datasets | 21 |

## Ontology

| Statistic | Value |
|---|---:|
| Ontology triples | 593 |
| Classes | 37 |
| Properties | 123 |
| Eventour role concepts | 3 |
| Eventour category concepts | 14 |
| Curation label concepts | 3 |

## Geometry And Provenance Coverage

| Check | Value |
|---|---:|
| `geo:Feature` resources | 293,165 |
| `geo:Geometry` resources | 293,165 |
| Features missing `geo:hasGeometry` | 0 |
| Features missing `geo:hasDefaultGeometry` | 0 |
| Geometries missing `geo:asWKT` | 0 |
| Features missing `dct:source` | 0 |
| Features missing `prov:wasDerivedFrom` | 0 |
| Features missing `rdfs:label` | 129 |

The 129 missing labels are treated as SHACL warnings rather than hard violations because they do not affect spatial reuse, provenance, or integration integrity.

## Wikidata Semantic Place Layer

| Statistic | Value |
|---|---:|
| Retained Wikidata places | 3,288 |
| Missing Eventour role | 0 |
| Missing `owl:sameAs` Wikidata link | 0 |
| Missing default geometry | 0 |
| Missing NIL link | 0 |
| Primary POIs | 1,114 |
| Secondary POIs | 892 |
| Context entities | 1,282 |
| Out-of-NIL Wikidata records excluded from published layer | 8 |

## Main Class Counts

Counts are distinct subjects typed with each class. Multi-typed resources are counted under each asserted class.

| Class | Entities |
|---|---:|
| `evt:SourceRecord` | 301,480 |
| `geo:Feature` | 293,165 |
| `geo:Geometry` | 293,165 |
| `evt:PhysicalAsset` | 278,387 |
| `evt:Tree` | 247,779 |
| `evt:StreetFurniture` | 30,608 |
| `evt:Bench` | 30,130 |
| `evt:TransportEntity` | 12,378 |
| `evt:ServiceAccessPoint` | 10,936 |
| `evt:StopInRoute` | 10,404 |
| `evt:Facility` | 9,787 |
| `evt:Stop` | 4,820 |
| `evt:ParkingFacility` | 3,323 |
| `evt:Place` | 3,288 |
| `evt:UrbanEntity` | 3,288 |
| `evt:BicycleParkingArea` | 3,249 |
| `evt:Infrastructure` | 1,632 |
| `evt:TimetableSummary` | 1,199 |
| `evt:DrinkingFountain` | 721 |
| `evt:HistoricShop` | 626 |
| `evt:EVChargingStation` | 483 |
| `evt:PicnicTable` | 478 |
| `evt:RoutePattern` | 466 |
| `evt:WiFiAccessPoint` | 428 |
| `evt:BikeSharingStation` | 325 |
| `evt:TransitLine` | 306 |
| `evt:PublicToilet` | 210 |
| `evt:MetroStation` | 130 |
| `evt:NILArea` | 88 |
| `evt:AdministrativeArea` | 88 |
| `evt:InterchangeParkingFacility` | 21 |

## Source Datasets

The KG integrates 21 official city datasets plus the Wikidata semantic place layer:

| Source dataset |
|---|
| `bike_areesosta` |
| `bikemi_stazioni` |
| `ds2484_alberi_20240331` |
| `ds2748_panchine` |
| `ds2749_tavoli_picnic` |
| `ds290_economia_botteghe_storiche_2024` |
| `ds630_servizi_igienici_pubblici_final` |
| `ds69_openwifi_layer_0_open_wifi_outdoor_4326_final` |
| `ds964_nil_wm` |
| `park_interscambio` |
| `park_pub` |
| `ricarica_colonnine` |
| `tpl_fermate` |
| `tpl_metrofermate` |
| `tpl_metroorari` |
| `tpl_metropercorsi` |
| `tpl_metrosequenza` |
| `tpl_orari` |
| `tpl_percorsi` |
| `tpl_sequenza` |
| `vedovelle_20260315-233003_final` |

## Namespace Policy

Global ontology terms and controlled vocabularies use:

```text
http://eventour.unimib.it/
http://eventour.unimib.it/role/
http://eventour.unimib.it/category/
```

Milan-specific resources use:

```text
http://eventour.unimib.it/milan/
```

This makes the resource directly extensible to other cities, for example `http://eventour.unimib.it/rome/`.

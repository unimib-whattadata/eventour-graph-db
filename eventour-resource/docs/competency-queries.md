# Competency Queries

This page embeds the competency questions, the exact SPARQL query files, and the recorded results used for the Eventour Milan release. Result counts and runtimes are copied from `queries/expected-results/runtime-summary.csv`; per-query result files are stored in `queries/expected-results/`.

## Summary

| Query | Purpose | Result count | Runtime (s) | Notes |
|---|---|---:|---:|---|
| CQ01 | count Wikidata places by Eventour role | 3 | 0.000 | role counts |
| CQ02 | retrieve entities in NIL 1 | 3097 | 0.012 | local WKT evaluation |
| CQ03 | primary POI-stop pairs within 300m | 200 | 0.085 | limit reached |
| CQ04 | toilets/fountains within 250m of primary POIs | 300 | 0.131 | limit reached |
| CQ05 | event-near secondary POI-stop rows | 100 | 0.034 | limit reached |
| CQ06 | NIL infrastructure profiles | 50 | 0.000 | limit reached |
| CQ07 | underserved primary POIs returned | 100 | 0.185 | limit reached |
| CQ08 | primary POI accessibility profiles | 100 | 0.000 | limit reached |
| CQ09 | provenance rows for selected Wikidata place | 1 | 0.000 | use Q1649868 or Q338472 |
| CQ10 | ranked primary POI support profiles | 100 | 0.000 | limit reached |

## Detailed Queries and Results

### CQ01: count Wikidata places by Eventour role

- Query file: `queries/competency/CQ01_how_many_wikidata-derived_semantic_places_are_avai.rq`
- Result file: `queries/expected-results/CQ01_results.csv`
- Result count: `3`
- Runtime: `0.000` seconds
- Notes: `role counts`

Result:

```csv
role,count
primary-poi,1114
secondary-poi,892
context-entity,1282
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ1. How many Wikidata-derived semantic places are available for each
# Eventour role?
################################################################################

SELECT ?role ?roleLabel (COUNT(DISTINCT ?place) AS ?places)
WHERE {
  ?place a evt:Place ;
         evt:hasEventourRole ?role .
  OPTIONAL { ?role skos:prefLabel ?roleLabel . }
}
GROUP BY ?role ?roleLabel
ORDER BY DESC(?places)

################################################################################
```

### CQ02: retrieve entities in NIL 1

- Query file: `queries/competency/CQ02_which_eventour_entities_are_located_in_a_given_nil.rq`
- Result file: `queries/expected-results/CQ02_results.csv`
- Result count: `3097`
- Runtime: `0.012` seconds
- Notes: `local WKT evaluation`

Result:

```csv
query,result_count
CQ02_entities_in_nil_1,3097
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ2. Which Eventour entities are located in a given NIL area, including
# official city entities and Wikidata semantic places?
################################################################################

SELECT ?entity ?label ?class ?role ?roleLabel ?wkt
WHERE {
  VALUES ?nil {
    <http://eventour.unimib.it/milan/nil/1>
  }

  ?entity evt:inNIL ?nil ;
          a ?class ;
          geo:hasDefaultGeometry/geo:asWKT ?wkt .
  OPTIONAL { ?entity rdfs:label ?label . }
  OPTIONAL {
    ?entity evt:hasEventourRole ?role .
    OPTIONAL { ?role skos:prefLabel ?roleLabel . }
  }
}
ORDER BY ?class LCASE(STR(?label))
LIMIT 500

################################################################################
```

### CQ03: primary POI-stop pairs within 300m

- Query file: `queries/competency/CQ03_which_primary_pois_are_within_300_metres_of_a_publ.rq`
- Result file: `queries/expected-results/CQ03_results.csv`
- Result count: `200`
- Runtime: `0.085` seconds
- Notes: `limit reached`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ03,200,0.085,limit reached
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ3. Which primary POIs are within 300 metres of a public transport stop?
# Requires GeoSPARQL distance support.
################################################################################

SELECT ?poi ?poiLabel ?stop ?stopLabel ?distanceM
WHERE {
  ?poi a evt:Place ;
       evt:hasEventourRole <http://eventour.unimib.it/role/primary-poi> ;
       rdfs:label ?poiLabel ;
       geo:hasDefaultGeometry/geo:asWKT ?poiWKT .

  ?stop a evt:Stop ;
        rdfs:label ?stopLabel ;
        geo:hasDefaultGeometry/geo:asWKT ?stopWKT .

  BIND(geof:distance(?poiWKT, ?stopWKT, uom:metre) AS ?distanceM)
  FILTER(?distanceM <= 300)
}
ORDER BY ?poiLabel ?distanceM
LIMIT 200

################################################################################
```

### CQ04: toilets/fountains within 250m of primary POIs

- Query file: `queries/competency/CQ04_for_each_primary_poi_which_public_toilets_and_drin.rq`
- Result file: `queries/expected-results/CQ04_results.csv`
- Result count: `300`
- Runtime: `0.131` seconds
- Notes: `limit reached`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ04,300,0.131,limit reached
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ4. For each primary POI, which public toilets and drinking fountains are
# available within 250 metres?
# Requires GeoSPARQL distance support.
################################################################################

SELECT ?poi ?poiLabel ?service ?serviceLabel ?serviceType ?distanceM
WHERE {
  ?poi a evt:Place ;
       evt:hasEventourRole <http://eventour.unimib.it/role/primary-poi> ;
       rdfs:label ?poiLabel ;
       geo:hasDefaultGeometry/geo:asWKT ?poiWKT .

  VALUES (?serviceType ?serviceClass) {
    ("public toilet" evt:PublicToilet)
    ("drinking fountain" evt:DrinkingFountain)
  }

  ?service a ?serviceClass ;
           rdfs:label ?serviceLabel ;
           geo:hasDefaultGeometry/geo:asWKT ?serviceWKT .

  BIND(geof:distance(?poiWKT, ?serviceWKT, uom:metre) AS ?distanceM)
  FILTER(?distanceM <= 250)
}
ORDER BY ?poiLabel ?serviceType ?distanceM
LIMIT 300

################################################################################
```

### CQ05: event-near secondary POI-stop rows

- Query file: `queries/competency/CQ05_crowd-staggering_query_given_an_event_location_ret.rq`
- Result file: `queries/expected-results/CQ05_results.csv`
- Result count: `100`
- Runtime: `0.034` seconds
- Notes: `limit reached`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ05,100,0.034,limit reached
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ5. Crowd-staggering query: given an event location, retrieve secondary POIs
# within 1 km that also have a public transport stop within 300 m.
# Replace the VALUES WKT with the event venue/event coordinate.
# Requires GeoSPARQL distance support.
################################################################################

SELECT ?secondaryPoi ?label ?poiDistanceM ?nearestStop ?nearestStopLabel ?stopDistanceM
WHERE {
  VALUES ?eventWKT {
    "POINT (9.1919 45.4642)"^^geo:wktLiteral
  }

  ?secondaryPoi a evt:Place ;
      evt:hasEventourRole <http://eventour.unimib.it/role/secondary-poi> ;
      rdfs:label ?label ;
      geo:hasDefaultGeometry/geo:asWKT ?poiWKT .

  BIND(geof:distance(?eventWKT, ?poiWKT, uom:metre) AS ?poiDistanceM)
  FILTER(?poiDistanceM <= 1000)

  ?nearestStop a evt:Stop ;
      rdfs:label ?nearestStopLabel ;
      geo:hasDefaultGeometry/geo:asWKT ?stopWKT .
  BIND(geof:distance(?poiWKT, ?stopWKT, uom:metre) AS ?stopDistanceM)
  FILTER(?stopDistanceM <= 300)
}
ORDER BY ?poiDistanceM ?stopDistanceM
LIMIT 100

################################################################################
```

### CQ06: NIL infrastructure profiles

- Query file: `queries/competency/CQ06_which_nil_areas_have_the_richest_urban_support_inf.rq`
- Result file: `queries/expected-results/CQ06_results.csv`
- Result count: `50`
- Runtime: `0.000` seconds
- Notes: `limit reached`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ06,50,0.000,limit reached
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ6. Which NIL areas have the richest urban support infrastructure?
################################################################################

SELECT ?nil ?nilLabel
       (COUNT(DISTINCT ?bench) AS ?benches)
       (COUNT(DISTINCT ?fountain) AS ?drinkingFountains)
       (COUNT(DISTINCT ?toilet) AS ?publicToilets)
       (COUNT(DISTINCT ?stop) AS ?stops)
       (COUNT(DISTINCT ?bikeStation) AS ?bikeSharingStations)
WHERE {
  ?nil a evt:NILArea .
  OPTIONAL { ?nil rdfs:label ?nilLabel . }
  OPTIONAL { ?bench a evt:Bench ; evt:inNIL ?nil . }
  OPTIONAL { ?fountain a evt:DrinkingFountain ; evt:inNIL ?nil . }
  OPTIONAL { ?toilet a evt:PublicToilet ; evt:inNIL ?nil . }
  OPTIONAL { ?stop a evt:Stop ; evt:inNIL ?nil . }
  OPTIONAL { ?bikeStation a evt:BikeSharingStation ; evt:inNIL ?nil . }
}
GROUP BY ?nil ?nilLabel
ORDER BY DESC(?benches + ?drinkingFountains + ?publicToilets + ?stops + ?bikeSharingStations)
LIMIT 50

################################################################################
```

### CQ07: underserved primary POIs returned

- Query file: `queries/competency/CQ07_which_primary_pois_are_underserved_i.e._have_no_pu.rq`
- Result file: `queries/expected-results/CQ07_results.csv`
- Result count: `100`
- Runtime: `0.185` seconds
- Notes: `limit reached`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ07,100,0.185,limit reached
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ7. Which primary POIs are underserved, i.e., have no public toilet or
# drinking fountain within 300 metres?
# Requires GeoSPARQL distance support.
################################################################################

SELECT ?poi ?label ?categoryLabel
WHERE {
  ?poi a evt:Place ;
       evt:hasEventourRole <http://eventour.unimib.it/role/primary-poi> ;
       rdfs:label ?label ;
       geo:hasDefaultGeometry/geo:asWKT ?poiWKT .
  OPTIONAL {
    ?poi evt:hasEventourCategory/skos:prefLabel ?categoryLabel .
  }

  FILTER NOT EXISTS {
    VALUES ?serviceClass { evt:PublicToilet evt:DrinkingFountain }
    ?service a ?serviceClass ;
             geo:hasDefaultGeometry/geo:asWKT ?serviceWKT .
    BIND(geof:distance(?poiWKT, ?serviceWKT, uom:metre) AS ?distanceM)
    FILTER(?distanceM <= 300)
  }
}
ORDER BY LCASE(STR(?label))
LIMIT 100

################################################################################
```

### CQ08: primary POI accessibility profiles

- Query file: `queries/competency/CQ08_multimodal_accessibility_profile_for_primary_pois_.rq`
- Result file: `queries/expected-results/CQ08_results.csv`
- Result count: `100`
- Runtime: `0.000` seconds
- Notes: `limit reached`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ08,100,0.000,limit reached
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ8. Multimodal accessibility profile for primary POIs: count nearby public
# transport stops, BikeMI stations, bicycle parking areas, and parking
# facilities.
# Requires GeoSPARQL distance support.
################################################################################

SELECT ?poi ?label
       (COUNT(DISTINCT ?stop) AS ?nearbyStops)
       (COUNT(DISTINCT ?bikeMi) AS ?nearbyBikeMiStations)
       (COUNT(DISTINCT ?bikeParking) AS ?nearbyBicycleParkingAreas)
       (COUNT(DISTINCT ?parking) AS ?nearbyParkingFacilities)
WHERE {
  ?poi a evt:Place ;
       evt:hasEventourRole <http://eventour.unimib.it/role/primary-poi> ;
       rdfs:label ?label ;
       geo:hasDefaultGeometry/geo:asWKT ?poiWKT .

  OPTIONAL {
    ?stop a evt:Stop ; geo:hasDefaultGeometry/geo:asWKT ?stopWKT .
    BIND(geof:distance(?poiWKT, ?stopWKT, uom:metre) AS ?stopDistanceM)
    FILTER(?stopDistanceM <= 300)
  }
  OPTIONAL {
    ?bikeMi a evt:BikeSharingStation ; geo:hasDefaultGeometry/geo:asWKT ?bikeMiWKT .
    BIND(geof:distance(?poiWKT, ?bikeMiWKT, uom:metre) AS ?bikeMiDistanceM)
    FILTER(?bikeMiDistanceM <= 500)
  }
  OPTIONAL {
    ?bikeParking a evt:BicycleParkingArea ; geo:hasDefaultGeometry/geo:asWKT ?bikeParkingWKT .
    BIND(geof:distance(?poiWKT, ?bikeParkingWKT, uom:metre) AS ?bikeParkingDistanceM)
    FILTER(?bikeParkingDistanceM <= 300)
  }
  OPTIONAL {
    ?parking a evt:ParkingFacility ; geo:hasDefaultGeometry/geo:asWKT ?parkingWKT .
    BIND(geof:distance(?poiWKT, ?parkingWKT, uom:metre) AS ?parkingDistanceM)
    FILTER(?parkingDistanceM <= 700)
  }
}
GROUP BY ?poi ?label
ORDER BY DESC(?nearbyStops) DESC(?nearbyBikeMiStations) DESC(?nearbyBicycleParkingAreas)
LIMIT 100

################################################################################
```

### CQ09: provenance rows for selected Wikidata place

- Query file: `queries/competency/CQ09_provenance_audit_for_a_selected_entity_retrieve_so.rq`
- Result file: `queries/expected-results/CQ09_results.csv`
- Result count: `1`
- Runtime: `0.000` seconds
- Notes: `use Q1649868 or Q338472`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ09,1,0.000,use Q1649868 or Q338472
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ9. Provenance audit: for a selected entity, retrieve source dataset,
# source record, generation activity, and external Wikidata link if present.
################################################################################

SELECT ?entity ?label ?source ?sourceRecord ?activity ?wikidata
WHERE {
  VALUES ?entity {
    <http://eventour.unimib.it/milan/entity/wikidata/Q10986>
  }
  OPTIONAL { ?entity rdfs:label ?label . }
  OPTIONAL { ?entity dct:source ?source . }
  OPTIONAL { ?entity prov:wasDerivedFrom ?sourceRecord . }
  OPTIONAL { ?entity prov:wasGeneratedBy ?activity . }
  OPTIONAL { ?entity owl:sameAs ?wikidata . }
}

################################################################################
```

### CQ10: ranked primary POI support profiles

- Query file: `queries/competency/CQ10_difficult_itinerary-seed_query_rank_primary_pois_b.rq`
- Result file: `queries/expected-results/CQ10_results.csv`
- Result count: `100`
- Runtime: `0.000` seconds
- Notes: `limit reached`

Result:

```csv
query,result_count,runtime_seconds,notes
CQ10,100,0.000,limit reached
```

SPARQL:

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX evt: <http://eventour.unimib.it/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>


# CQ10. Difficult itinerary-seed query: rank primary POIs by nearby operational
# support, combining transport, toilets, drinking fountains, and bike sharing.
# Requires GeoSPARQL distance support.
################################################################################

SELECT ?poi ?label ?categoryLabel
       (COUNT(DISTINCT ?stop) AS ?stops300m)
       (COUNT(DISTINCT ?toilet) AS ?toilets300m)
       (COUNT(DISTINCT ?fountain) AS ?fountains300m)
       (COUNT(DISTINCT ?bikeMi) AS ?bikeMi500m)
       ((COUNT(DISTINCT ?stop) + COUNT(DISTINCT ?toilet) + COUNT(DISTINCT ?fountain) + COUNT(DISTINCT ?bikeMi)) AS ?supportScore)
WHERE {
  ?poi a evt:Place ;
       evt:hasEventourRole <http://eventour.unimib.it/role/primary-poi> ;
       rdfs:label ?label ;
       geo:hasDefaultGeometry/geo:asWKT ?poiWKT .
  OPTIONAL { ?poi evt:hasEventourCategory/skos:prefLabel ?categoryLabel . }

  OPTIONAL {
    ?stop a evt:Stop ; geo:hasDefaultGeometry/geo:asWKT ?stopWKT .
    BIND(geof:distance(?poiWKT, ?stopWKT, uom:metre) AS ?stopDistanceM)
    FILTER(?stopDistanceM <= 300)
  }
  OPTIONAL {
    ?toilet a evt:PublicToilet ; geo:hasDefaultGeometry/geo:asWKT ?toiletWKT .
    BIND(geof:distance(?poiWKT, ?toiletWKT, uom:metre) AS ?toiletDistanceM)
    FILTER(?toiletDistanceM <= 300)
  }
  OPTIONAL {
    ?fountain a evt:DrinkingFountain ; geo:hasDefaultGeometry/geo:asWKT ?fountainWKT .
    BIND(geof:distance(?poiWKT, ?fountainWKT, uom:metre) AS ?fountainDistanceM)
    FILTER(?fountainDistanceM <= 300)
  }
  OPTIONAL {
    ?bikeMi a evt:BikeSharingStation ; geo:hasDefaultGeometry/geo:asWKT ?bikeMiWKT .
    BIND(geof:distance(?poiWKT, ?bikeMiWKT, uom:metre) AS ?bikeMiDistanceM)
    FILTER(?bikeMiDistanceM <= 500)
  }
}
GROUP BY ?poi ?label ?categoryLabel
ORDER BY DESC(?supportScore) LCASE(STR(?label))
LIMIT 50
```

# Repository Readiness Report

Generated on 2026-05-08.

## Scope

This report checks whether the repository contains the files needed to reconstruct
the Eventour Milan knowledge graph and inspect the itinerary-generation use
case.

## Knowledge Graph Reconstruction

Verified command:

```bash
make PYTHON=/Users/blespa/miniconda3/envs/eventour-rdf/bin/python \
  prepare-sources build-municipal build-wikidata nil merge metadata \
  validate competency-report competency package
```

Result: the command completed with exit code 0.

The reconstruction package contains:

- Municipal source catalog with exact feature counts and public Comune di Milano dataset URLs in `data/source-snapshots/source-snapshots.csv`.
- A download/listing helper in `scripts/00_download_sources.py`; raw municipal source snapshots are intentionally excluded from Git and must be downloaded before rebuilding the municipal layer locally.
- Municipal mapping files in `mappings/municipal/`.
- Streaming municipal converters in `scripts/municipal/`.
- Wikidata extraction, cleanup, evidence-card, LLM-output, and adjudication artifacts in `curation/`.
- Wikidata reconstruction workspace in `curation/reconstruction/milan/`.
- Python source package in `src/eventour_kg/`.
- Ontology files in `ontology/`.
- VoID/DCAT metadata in `metadata/`.
- SHACL shapes in `shapes/`.
- Competency queries and generated query report in `queries/` and `docs/competency-queries.md`.
- Validation reports in `validation/reports/`.

Freshly generated reconstruction outputs were produced during validation but are
not stored in Git because the frozen KG is archived in Zenodo:

| File | Lines |
|---|---:|
| `eventour_phase1_data.nt` | 7,477,892 |
| `eventour_phase2_transport_data.nt` | 323,420 |
| `eventour_phase3_services_data.nt` | 361,010 |
| `eventour_municipal_backbone.nt` | 8,162,322 |
| `eventour_municipal_nil_inferred.nt` | 1,140,212 |
| `eventour_wikidata_nil_links.nt` | 13,152 |
| `eventour_wikidata_place_layer.nt` | 70,500 |
| `eventour_reconstructed_kg.nt` | 9,373,631 |

The validation report confirms the frozen release data graph parses as
N-Triples and reports:

- Data graph triples: 9,374,065.
- Ontology triples: 593.
- Ontology classes: 37.
- Ontology properties: 123.
- Spatial features with `geo:hasGeometry`: 100%.
- Spatial features with `geo:hasDefaultGeometry`: 100%.
- Invalid or unparsable WKT literals: 0.
- Dangling `evt:inNIL` references: 0.
- Wikidata places missing NIL: 0.
- Wikidata places missing role: 0.
- SHACL hard violations: 0.
- SHACL warnings: 129 tree-label warnings.

## Itinerary Generation

Verified commands:

```bash
/Users/blespa/miniconda3/envs/eventour-rdf/bin/python \
  app/itinerary-generation/generate_itineraries.py --check-only

/Users/blespa/miniconda3/envs/eventour-rdf/bin/python \
  app/itinerary-generation/build_distance_matrix_osrm.py --check-only
```

Result: both commands completed with exit code 0.

The itinerary-generation package contains:

- Numbered dynamic-planning notebooks in `app/itinerary-generation/dynamic-planning/`.
- POI input file `dynamic-planning/pois_with_wikidata.csv`.
- Released POI distance matrix `dynamic-planning/poi_distances_with_types_and_wikidata_POI_final_subset_20ina_POIs.csv`.
- Archived POI KG artifact `dynamic-planning/knowledge_graph_poi.7z`.
- Spatial data-integration workspace in `app/itinerary-generation/data-integration/`.
- Weather, NIL, taxonomy, and integrated CSV inputs under `data-integration/data-integration/`.
- Lightweight CLI checkers in `app/itinerary-generation/generate_itineraries.py` and `app/itinerary-generation/build_distance_matrix_osrm.py`.

## Publication Metadata

The repository is configured for public release with the Zenodo DOI
`https://doi.org/10.5281/zenodo.20076141`. The KG, ontology, metadata,
documentation, mappings, validation artifacts, competency-query artifacts, and
curation artifacts use `CC BY 4.0`. The source code and itinerary-generation
software use the MIT License.

The SPARQL endpoint is not bundled with the repository. Users can load the
release locally using `docs/graphdb-loading.md`.

## GitHub Upload Note

The repository excludes raw municipal source snapshots and generated KG dumps
from Git. If future releases decide to commit large reconstruction artifacts
instead of referencing Zenodo, use Git LFS for files larger than GitHub's normal
file-size limit.

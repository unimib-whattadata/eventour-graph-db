# Eventour

Eventour is a reusable RDF/GeoSPARQL urban knowledge graph resource for Milan. It integrates official Comune di Milano open datasets with a curated Wikidata semantic-place layer, preserving geometry, source records, provenance, controlled vocabularies, validation artifacts, and competency queries for context-aware urban applications.

## Resource Availability

- Canonical GitHub repository: `https://github.com/unimib-whattadata/eventour-resource`
- Zenodo DOI: `https://doi.org/10.5281/zenodo.20076141`
- SPARQL endpoint: not bundled with the repository; see [`docs/graphdb-loading.md`](docs/graphdb-loading.md) to load the release locally.
- Eventour platform: companion application materials are documented under [`app/`](app/).
- UI repository: `https://github.com/unimib-whattadata/eventour-ui`
- GraphDB repository: `https://github.com/unimib-whattadata/eventour-graph-db`
- Current release version: `v1.0.0`

## What Is Included?

- Final KG release manifest and sample RDF.
- Eventour ontology in Turtle, N-Triples, and OWL-named Turtle form.
- VoID/DCAT metadata and release metadata.
- SHACL validation shapes.
- Municipal mapping files.
- Municipal source URL catalog and downloader for the 21 Comune di Milano datasets.
- Wikidata extraction, cleanup, evidence-card, LLM-curation, and human-curation artifacts.
- Source Python package used for Wikidata extraction, evidence construction, curation, RDF export, and evaluation.
- Human annotation and adjudication artifacts.
- Competency queries and expected runtime summary.
- Validation reports and scripts.
- Pointers to application, UI, and GraphDB loading code.

## Quick Start

```bash
make setup
make download-sources
make prepare-sources
make build-municipal
make build-wikidata
make nil
make merge
make validate
make competency
make graphdb
```

The full frozen KG dump is distributed through Zenodo/GitHub Releases because it contains more than 9.3 million triples. Raw Comune di Milano source snapshots are not committed to Git; the repository contains the public source catalog, downloader, mappings, reconstruction scripts, Wikidata curation artifacts, and validation reports needed to rebuild the release locally.

Some reconstruction artifacts are large. When publishing this repository on
GitHub, use Git LFS for the paths listed in `.gitattributes`, or move those
files to the Zenodo release and keep the same paths as download targets.

## Repository Structure

```text
ontology/     Eventour ontology and diagrams
data/         release manifest, checksums, sample data, download pointers
mappings/     municipal and Wikidata mapping policies
curation/     Wikidata curation artifacts and human evaluation files
metadata/     VoID/DCAT and release metadata
shapes/       SHACL shapes
queries/      competency and application SPARQL queries
validation/   validation reports and scripts
scripts/      construction workflow entry points
src/          Python source package for the Wikidata and RDF construction workflow
tests/        Regression tests from the construction workspace
app/          application links and itinerary-generation artifacts
docs/         human-readable documentation
```

## Citation

Use `CITATION.cff`. Once archived, cite both the Zenodo DOI and the ISWC resource-track paper.

## License and Attribution

The Eventour Milan KG, ontology, metadata, documentation, mappings, validation artifacts, competency-query artifacts, and curation artifacts are released under Creative Commons Attribution 4.0 International (`CC-BY-4.0`). The RDF graph includes data derived from Comune di Milano open data and Wikidata. Users must preserve attribution and comply with source-data licenses. The standalone code and itinerary-generation software are released under the MIT License; see `LICENSES/`.

## Contact and Issues

Please report problems through the GitHub issue tracker. Useful issue reports include broken links, incorrect source metadata, missing labels, geometry problems, duplicate entities, NIL-assignment errors, and suggested ontology alignments.

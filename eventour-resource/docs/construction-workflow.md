# Construction Workflow

The repository contains the files needed to reconstruct the Eventour Milan KG:
municipal GeoJSON source snapshots, YAML mappings, streaming RDF converters,
Wikidata extraction and curation artifacts, ontology files, SHACL shapes,
metadata, competency queries, and validation reports.

Run the main workflow from the repository root:

```bash
make setup
make prepare-sources
make build-municipal
make build-wikidata
make nil
make merge
make metadata
make validate
make competency
```

The municipal conversion is performed by `scripts/02_build_municipal_rdf.py`,
which calls the three streaming converters in `scripts/municipal/` and writes
the generated N-Triples layers to `data/work/`.

The Wikidata workflow is reconstructable from released artifacts under
`curation/reconstruction/milan/`. These include the candidate query, normalized
candidate rows, raw one-hop subgraphs, property catalog, cleaned subgraphs,
class ancestors, evidence cards, prompt batches, raw model outputs, annotation
files, adjudication files, and final decisions. Re-running live Wikidata queries
or the LLM classification is optional; the released artifacts are sufficient for
auditing the published semantic-place layer.

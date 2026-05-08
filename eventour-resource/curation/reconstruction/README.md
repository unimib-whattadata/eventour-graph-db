# Reconstruction Artifacts

This directory preserves the Milan construction workspace artifacts used to
audit and reproduce the Wikidata semantic-place workflow: SPARQL queries,
normalized candidates, raw one-hop subgraph batches, property catalogs, cleaned
subgraphs, evidence cards, prompt batches, raw model outputs, annotation files,
adjudication files, and final decision files.

The authoritative public release files are the ontology in `ontology/`, the
metadata in `metadata/`, the validation reports in `validation/reports/`, and
the final KG dump distributed through Zenodo/GitHub Releases. RDF files inside
this reconstruction directory are intermediate construction artifacts and
should not be cited as the canonical release dump.

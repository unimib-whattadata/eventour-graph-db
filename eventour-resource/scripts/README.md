# Scripts

This folder provides stable workflow entry points for reviewers and reusers.
The executable reconstruction code is included in two places:

- `scripts/municipal/` contains the streaming converters and enrichment scripts used to build the municipal RDF backbone.
- `src/eventour_kg/` contains the Wikidata extraction, cleanup, evidence-card, curation, evaluation, and RDF-export package.

Typical reconstruction order:

```bash
make download-sources
make prepare-sources
make build-municipal
make build-wikidata
make nil
make merge
make metadata
make validate
make competency
```

The Wikidata curation artifacts released under `curation/reconstruction/milan/`
allow the semantic-place layer to be audited or regenerated without treating the
LLM as a hidden dependency. Re-running the LLM classification itself is optional
and requires provider credentials.

# GraphDB Loading

Recommended load order:

1. Load the full data graph release from Zenodo/GitHub Releases.
2. Load `ontology/eventour.ttl` if the release graph does not already include the patched ontology.
3. Load `metadata/eventour-catalog.ttl`.
4. Load `shapes/eventour-shapes.ttl` into the validation context if supported.

The final paper statistics use the data graph count of 9,374,065 triples and the ontology count of 593 triples.


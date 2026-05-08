# Annotation Instructions

This package supports manual evaluation of the Eventour semantic classification layer.

## What each annotator should do

- Label each sampled entity independently using one final decision: `keep_poi`, `keep_context`, or `exclude`.
- If you choose `keep_poi`, also assign exactly one Eventour category.
- Use only the evidence fields shown in the CSV: label, description, direct classes, class ancestors, and semantic facts. Assign labels using only the evidence shown in the annotation sheet. Do not rely on personal knowledge or external lookup during the primary annotation pass.
- Do not use the LLM prediction during annotation. The annotator files are intentionally blinded.
- Use `annotator_is_ambiguous` only as a secondary flag when the case is genuinely borderline for a human reviewer.

## Human decision definitions

- `keep_poi`: The entity should be kept as a candidate Eventour stop.
- `keep_context`: The entity should be kept only as contextual urban information.
- `exclude`: The entity should be excluded from Eventour.

## Model-only review label

- `candidate_exception` is kept only in the master package as the LLM's review-routing output.
- Annotators should not use `candidate_exception` as a final gold label.

## Eventour category definitions

- `museum_collection`: Museum, collection, or exhibition-oriented cultural venue.
- `gallery_art_space`: Gallery, art space, or venue centered on visual arts display.
- `religious_heritage`: Church, chapel, monastery, cemetery, or other religious heritage site.
- `historic_architecture`: Historically or architecturally significant building, palace, house, or complex.
- `monument_memorial`: Monument, memorial, commemorative site, or war remembrance structure.
- `public_art`: Artwork, mural, sculpture, or artistic installation in public or semi-public space.
- `archaeological_ancient_site`: Archaeological remains, ancient ruins, or historically ancient site.
- `urban_landmark`: Distinctive landmark or city reference point with strong orientation or identity value.
- `performing_arts_entertainment`: Theatre, opera house, cinema, music venue, or performing arts attraction.
- `park_garden_nature`: Park, garden, natural area, or outdoor green attraction.
- `cemetery_funerary_heritage`: Cemetery or funerary heritage site with cultural or historical significance.
- `science_education_attraction`: Public-facing science, education, or discovery-oriented attraction.
- `district_streetscape`: District, streetscape, square, or urban ensemble notable as a place experience.
- `special_interest_attraction`: Other specialized attraction that is meaningful but does not fit the main categories cleanly.

## Sample design

- Total sampled entities: `758`
- Candidate exceptions included in full: `518`
- `keep_poi` sample: `100`
- `keep_context` sample: `60`
- `exclude` sample: `80`
- The sample is not proportional by decision. It is risk-aware and balanced: all `candidate_exception` rows are included, and the other decisions use bounded slices with oversampling of low-confidence and hard-class cases.

## Hard classes intentionally oversampled

- `branded_venues`: `124` sampled entities
- `building_house_palazzo`: `246` sampled entities
- `events`: `90` sampled entities
- `libraries_archives`: `297` sampled entities
- `schools_institutions`: `141` sampled entities

## Suggested evaluation workflow

- Give the same blinded CSV to 3 annotators independently.
- Merge the three completed CSVs by `sample_id`.
- Compute inter-annotator agreement on the 4-way decision.
- Build an adjudicated gold label for disagreements.
- Compare the LLM outputs in the master JSON/JSONL package against the adjudicated gold labels.


# Itinerary Generation

This folder contains the itinerary-generation and gamified crowd-management
materials associated with the Eventour application use case.

## Contents

- `dynamic-planning/`: notebooks and datasets from the dynamic itinerary
  planning and gamified crowd-management prototype. The numbered notebooks
  follow the original execution order: POI selection, OSRM distance matrix
  generation, fine-tuning dataset generation, itinerary MCQ generation, and
  model fine-tuning.
- `data-integration/`: earlier data-integration workspace used for spatial
  POI/support-service integration, weather data, NIL support files, taxonomies,
  and integrated CSV datasets.
- `generate_itineraries.py` and `build_distance_matrix_osrm.py`: lightweight
  command-line entry points that verify and document the released notebook
  workflow artifacts.

## Notes For The Resource Release

The itinerary materials are application artifacts, not part of the canonical KG
dump. They are included so reviewers can inspect how Eventour-style POI,
service, distance, and gamification data were used in the application scenario.

## License

The itinerary-generation software is released under the MIT License. Input/output
examples and documentation follow the repository resource license, Creative
Commons Attribution 4.0 International (`CC BY 4.0`), unless a source-data license
imposes additional attribution requirements. See
`../../LICENSES/ITINERARY_GENERATION_LICENSE.md`.

Large application files should be stored through Git LFS or the Zenodo release
when the repository is published.

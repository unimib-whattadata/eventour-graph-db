PYTHON ?= python

.PHONY: setup download-sources prepare-sources build-municipal build-wikidata nil merge metadata validate competency competency-report package graphdb

setup:
	$(PYTHON) -m pip install -r requirements.txt

download-sources:
	$(PYTHON) scripts/00_download_sources.py --download

prepare-sources:
	$(PYTHON) scripts/01_prepare_municipal_sources.py

build-municipal:
	$(PYTHON) scripts/02_build_municipal_rdf.py --mapping-dir mappings/municipal/

build-wikidata:
	$(PYTHON) scripts/03_extract_wikidata_candidates.py
	$(PYTHON) scripts/04_extract_wikidata_subgraphs.py
	$(PYTHON) scripts/05_clean_wikidata_claims.py
	$(PYTHON) scripts/06_build_evidence_cards.py
	$(PYTHON) scripts/07_run_llm_curation.py
	$(PYTHON) scripts/08_merge_human_adjudication.py

nil:
	$(PYTHON) scripts/09_assign_nil_areas.py
	$(PYTHON) scripts/10_build_wikidata_place_layer.py

merge:
	$(PYTHON) scripts/11_merge_eventour_graph.py

metadata:
	$(PYTHON) scripts/12_generate_void_dcat.py

validate:
	$(PYTHON) scripts/13_validate_release.py

competency:
	$(PYTHON) scripts/14_run_competency_queries.py

competency-report:
	$(PYTHON) scripts/16_generate_competency_query_report.py

package:
	$(PYTHON) scripts/15_package_release.py

graphdb:
	docker compose -f docker/docker-compose.yml up -d

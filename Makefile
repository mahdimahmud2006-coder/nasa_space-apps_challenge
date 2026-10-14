PYTHON ?= .venv/bin/python
UV ?= uv
.PHONY: setup inspect process augment timeseries validate-timeseries test validate demo context download-context validate-context
setup:
	$(UV) --cache-dir .uv-cache venv .venv --python python3
	$(UV) --cache-dir .uv-cache pip install --python $(PYTHON) -r requirements.txt
inspect:
	$(PYTHON) -m src.ingest.inspect_h5 . > data/derived/audit.txt
process:
	$(PYTHON) -m src.compute.pipeline --config config.json
	$(PYTHON) -m src.compute.extend_evidence
augment:
	$(PYTHON) -m src.compute.extend_evidence
timeseries:
	$(PYTHON) -m src.compute.timeseries_pipeline --config config.timeseries.json
validate-timeseries:
	$(PYTHON) -m src.compute.validate_timeseries
test:
	$(PYTHON) -m pytest -q
validate:
	$(PYTHON) -m src.compute.validate
demo:
	OFFLINE=1 $(PYTHON) -m src.api.app

download-context:
	$(PYTHON) -m src.ingest.environment
context:
	$(PYTHON) -m src.compute.context_pipeline --config config.context.json
validate-context:
	$(PYTHON) -m src.compute.validate_context

.PHONY: test-ui
test-ui:
	node tests/playback.test.mjs
	node tests/terrain-view.test.mjs
	node tests/studio.test.mjs
	node tests/change-lab.test.mjs

.PHONY: flood thermal download-thermal studio validate-flood
flood:
	$(PYTHON) -m src.compute.flood_pipeline
thermal:
	$(PYTHON) -m src.compute.thermal_pipeline
download-thermal:
	$(PYTHON) -m src.ingest.thermal
studio: flood thermal
validate-flood:
	$(PYTHON) -m src.compute.validate_flood

.PHONY: dna landslide change-lab validate-change-lab
dna:
	$(PYTHON) -m src.compute.dna_pipeline
landslide:
	$(PYTHON) -m src.compute.landslide_pipeline
change-lab: dna landslide
validate-change-lab:
	$(PYTHON) -m src.compute.validate_change_lab

.PHONY: download-landslide-reference
download-landslide-reference:
	$(PYTHON) -m src.ingest.landslide_reference

.PHONY: run check-ready verify release
run:
	./run.sh
check-ready:
	$(PYTHON) -m src.api.readiness
verify: test test-ui validate validate-timeseries validate-context validate-flood validate-change-lab check-ready check-web
release:
	$(PYTHON) scripts/package_release.py

.PHONY: check-web
check-web:
	$(PYTHON) scripts/check_web.py

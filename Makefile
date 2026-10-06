PYTHON ?= .venv/bin/python
UV ?= uv
.PHONY: setup inspect process augment test validate demo
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
test:
	$(PYTHON) -m pytest -q
validate:
	$(PYTHON) -m src.compute.validate
demo:
	OFFLINE=1 $(PYTHON) -m src.api.app

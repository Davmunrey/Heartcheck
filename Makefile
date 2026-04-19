.PHONY: install test eval eval-synth eval-gate lint help

ML := apps/ml-api
PY := $(ML)/.venv/bin/python
PIP := $(ML)/.venv/bin/pip
SYNTH_DIR ?= data/synth_v1
EVAL_OUT ?= eval/reports
EVAL_LABEL ?= candidate
BASELINE ?=

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "%-15s %s\n", $$1, $$2}'

install:  ## Install backend deps in venv
	./scripts/install_backend.sh

test:  ## Run pytest
	cd $(ML) && $(PY) -m pytest -q

eval-synth:  ## Generate the deterministic synthetic dataset
	cd $(ML) && $(PY) -m app.eval.synth --out ../$(SYNTH_DIR) --n 20

eval:  ## Run evaluation harness against $(SYNTH_DIR) and emit a report
	mkdir -p $(EVAL_OUT)
	cd $(ML) && $(PY) -m app.eval.cli \
		--manifest ../$(SYNTH_DIR)/manifest.jsonl \
		--out ../$(EVAL_OUT) \
		--label $(EVAL_LABEL) \
		$(if $(BASELINE),--baseline ../$(BASELINE))

eval-gate:  ## Run eval with regression gate (requires BASELINE=path/to/report.json)
	@test -n "$(BASELINE)" || (echo "set BASELINE=path/to/report.json" && exit 2)
	mkdir -p $(EVAL_OUT)
	cd $(ML) && $(PY) -m app.eval.cli \
		--manifest ../$(SYNTH_DIR)/manifest.jsonl \
		--out ../$(EVAL_OUT) \
		--label $(EVAL_LABEL) \
		--baseline ../$(BASELINE) \
		--gate

lint:  ## Run ruff
	cd $(ML) && $(PY) -m ruff check app tests

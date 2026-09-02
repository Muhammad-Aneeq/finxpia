.DEFAULT_GOAL := help
SHELL := /bin/sh

# On Windows the venv puts executables in Scripts/, elsewhere in bin/.
VENV := .venv
ifeq ($(OS),Windows_NT)
  PY := $(VENV)/Scripts/python.exe
else
  PY := $(VENV)/bin/python
endif

CORPUS_DIR := corpus
SEED ?= 20260903

.PHONY: help install corpus verify test lint typecheck check validate \
        export packaging site report demo clean all

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install the package with dev extras
	uv venv --python 3.12 $(VENV)
	uv pip install --python $(PY) -e ".[dev]"

corpus: ## Regenerate the corpus and its hash manifest
	$(PY) -m finxpia.cli generate --out $(CORPUS_DIR) --seed $(SEED)

verify: ## Verify the committed corpus against its manifest and seed
	$(PY) -m finxpia.cli verify --corpus $(CORPUS_DIR)

test: ## Run the test suite
	$(PY) -m pytest

lint: ## Lint with ruff
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

typecheck: ## Typecheck with mypy
	$(PY) -m mypy

check: lint typecheck test verify ## Everything CI runs

clean: ## Remove build and cache artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

all: check ## Alias for check

validate: ## Run both release gates (MockLLM without a key; real gates with OPENAI_API_KEY)
	$(PY) -m finxpia.cli validate --corpus $(CORPUS_DIR) --out artifacts/gate_report.json

evals: ## Export evals/cases.jsonl from the committed corpus
	$(PY) -m finxpia.cli export-evals --corpus $(CORPUS_DIR)

export: ## Export the promptfoo dataset and PyRIT SeedDataset files
	$(PY) -m finxpia.cli export --corpus $(CORPUS_DIR)

payloads: ## Export the payload map for the dashboard's Case Replay screen
	$(PY) -m finxpia.cli payloads --corpus $(CORPUS_DIR)

site: payloads ## Build the static dashboard (report-site/dist)
	cd report-site && npm install --no-audit --no-fund && npm run build

demo: ## Rebuild the demo fixtures and point the dashboard at the naive run
	$(PY) -m finxpia.cli report fixtures/promptfoo_results.naive.sample.json \
	  --out report-site/public/finxpia-run.json --target "naive-invoice-agent (demo)"

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

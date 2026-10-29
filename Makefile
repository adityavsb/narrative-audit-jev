.PHONY: help install test test-cov lint format clean eval data-check generate-data metrics grep-gate check-model-1 check-models-2-3 eval-openrouter

PYTHON ?= python3
VENV ?= .venv

help:
	@echo "Available commands:"
	@echo "  make install           Set up virtualenv and install package in editable mode"
	@echo "  make generate-data     Synthesize local benchmark datasets on demand"
	@echo "  make test              Run unit and integration test suite"
	@echo "  make test-cov          Run test suite with HTML coverage report"
	@echo "  make lint              Run ruff linter"
	@echo "  make format            Auto-format code with ruff"
	@echo "  make data-check        Validate DuckDB benchmark datasets and ground truth"
	@echo "  make metrics           Append metrics_log.csv row (pytest + data-check)"
	@echo "  make grep-gate         Check prose register (scripts/grep_gate.sh)"
	@echo "  make check-model-1     Smoke test Model 1 on 1 case (check-run stage 1)"
	@echo "  make check-models-2-3  Smoke test Models 2 & 3 on 1 case (check-run stage 2)"
	@echo "  make eval-openrouter   Full benchmark evaluation across all 3 models + rule engine"
	@echo "  make clean             Remove temporary files and caches"

generate-data:
	$(VENV)/bin/python src/db/generate_benchmark_data.py
	$(VENV)/bin/python src/db/generate_ground_truth.py

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

test:
	$(VENV)/bin/pytest tests/

test-cov:
	$(VENV)/bin/pytest --cov=src --cov-report=term-missing --cov-report=html tests/

lint:
	$(VENV)/bin/ruff check src tests

format:
	$(VENV)/bin/ruff format src tests

data-check:
	$(VENV)/bin/python -m src.db.schema --validate

eval: eval-golden

eval-golden:
	$(VENV)/bin/python scripts/run_golden_eval.py

check-model-1:
	$(VENV)/bin/python scripts/run_openrouter_eval.py --stage check-one

check-models-2-3:
	$(VENV)/bin/python scripts/run_openrouter_eval.py --stage check-remaining

eval-openrouter:
	$(VENV)/bin/python scripts/run_openrouter_eval.py --stage full

metrics:
	bash scripts/record_metrics.sh

grep-gate:
	bash scripts/grep_gate.sh

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage htmlcov/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +

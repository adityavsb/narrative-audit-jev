.PHONY: help install test test-cov lint format clean eval data-check generate-data

PYTHON ?= python3
VENV ?= .venv

help:
	@echo "Available commands:"
	@echo "  make install        Set up virtualenv and install package in editable mode"
	@echo "  make generate-data  Synthesize local benchmark datasets on demand"
	@echo "  make test           Run unit and integration test suite"
	@echo "  make test-cov       Run test suite with HTML coverage report"
	@echo "  make lint           Run ruff linter"
	@echo "  make format         Auto-format code with ruff"
	@echo "  make data-check     Validate DuckDB benchmark datasets and ground truth"
	@echo "  make clean          Remove temporary files and caches"

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

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage htmlcov/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +

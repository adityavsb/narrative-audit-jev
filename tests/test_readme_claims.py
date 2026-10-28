"""README-scale counts must match validate_benchmark stats."""

from pathlib import Path

import pytest

from src.db.schema import (
    EXPECTED_COMPANIES,
    EXPECTED_GOLDEN_CASES,
    EXPECTED_QUARTERS,
    validate_benchmark,
)


def test_readme_scale_matches_benchmark():
    errors, stats = validate_benchmark()
    assert errors == [], errors
    assert stats["companies_count"] == EXPECTED_COMPANIES == 4
    assert stats["quarters_count"] == EXPECTED_QUARTERS == 32
    assert stats["golden_cases"] == EXPECTED_GOLDEN_CASES == 64
    assert stats["transcripts_count"] >= 12


def test_golden_file_case_count():
    golden = Path(__file__).resolve().parent.parent / "data" / "golden_ground_truth.json"
    import json

    cases = json.loads(golden.read_text())
    assert len(cases) == EXPECTED_GOLDEN_CASES

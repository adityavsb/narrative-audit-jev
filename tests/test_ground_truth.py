"""Validation tests for the 52-case golden benchmark ground truth dataset."""

import json
from pathlib import Path
import pytest


@pytest.fixture(scope="module")
def ground_truth_cases():
    file_path = Path(__file__).resolve().parent.parent / "data" / "golden_ground_truth.json"
    assert file_path.exists(), f"Golden benchmark file not found at {file_path}"
    with open(file_path, "r") as f:
        cases = json.load(f)
    return cases


def test_ground_truth_case_count_and_uniqueness(ground_truth_cases):
    """Verify at least 50 cases exist and all case IDs are strictly unique."""
    assert len(ground_truth_cases) >= 50
    case_ids = [c["case_id"] for c in ground_truth_cases]
    assert len(case_ids) == len(set(case_ids)), "Duplicate case_id found in golden benchmark"


def test_ground_truth_schema_completeness(ground_truth_cases):
    """Verify each benchmark case contains all mandatory metadata and evaluation fields."""
    required_keys = {"case_id", "ticker", "fiscal_year", "fiscal_quarter", "category", "claim_text", "ground_truth"}
    required_gt_keys = {"is_discrepancy", "divergence_category", "materiality", "expected_verdict", "verified_numbers", "rationale"}

    valid_categories = {
        "MARGIN_DILUTION", "CAPITAL_SINKHOLE", "REVENUE_RECLASSIFICATION", "PILOT_CHURN", "NONE"
    }
    valid_materialities = {"NONE", "LOW", "MODERATE", "HIGH", "CRITICAL"}
    valid_verdicts = {"SUPPORTED", "CONTRADICTED", "UNVERIFIABLE"}

    for case in ground_truth_cases:
        assert required_keys.issubset(case.keys()), f"Case {case.get('case_id')} missing top-level keys"
        gt = case["ground_truth"]
        assert required_gt_keys.issubset(gt.keys()), f"Case {case['case_id']} missing ground_truth keys"
        assert gt["divergence_category"] in valid_categories, f"Invalid divergence_category in {case['case_id']}"
        assert gt["materiality"] in valid_materialities, f"Invalid materiality in {case['case_id']}"
        assert gt["expected_verdict"] in valid_verdicts, f"Invalid expected_verdict in {case['case_id']}"


def test_ground_truth_ticker_coverage(ground_truth_cases):
    """Verify representation across all four fictional scenario archetypes."""
    tickers = {c["ticker"] for c in ground_truth_cases}
    assert tickers == {"AURA", "NXUS", "SYNX", "VORS"}

    # Count by ticker
    counts = {t: sum(1 for c in ground_truth_cases if c["ticker"] == t) for t in tickers}
    for t, count in counts.items():
        assert count >= 10, f"Ticker {t} has fewer than 10 benchmark cases: {count}"


def test_adversarial_prompt_injections_present(ground_truth_cases):
    """Verify that adversarial prompt-injection test cases are present in the benchmark suite."""
    injections = [c for c in ground_truth_cases if c["category"] == "ADVERSARIAL_PROMPT_INJECTION"]
    assert len(injections) >= 3, "Insufficient adversarial prompt-injection test cases in benchmark suite"

"""OpenRouter batch runner must fail closed and exclude failed cases from metrics."""

import json
from pathlib import Path

import pytest

from scripts.run_openrouter_eval import evaluate_model_on_cases


class _FailingEvaluator:
    def evaluate(self, ticker, fiscal_year, fiscal_quarter, claim_text, case_id):
        raise RuntimeError("OpenRouter evaluation failed after 3 attempts (URLError).")


class _OkEvaluator:
    last_telemetry = {"prompt_tokens": 0, "completion_tokens": 0}

    def evaluate(self, ticker, fiscal_year, fiscal_quarter, claim_text, case_id):
        from src.agents.state import AuditVerdict, DivergenceType, MaterialityTier

        gt_disc = case_id.endswith("_FAIL")
        return AuditVerdict(
            ticker=ticker,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            is_discrepancy=gt_disc,
            divergence_type=DivergenceType.NONE if not gt_disc else DivergenceType.MARGIN_DILUTION,
            materiality=MaterialityTier.NONE,
            ndi_score=10.0,
            confidence=0.9 if gt_disc else 0.1,
            summary="mock",
            supporting_evidence=[],
            fact_checks=[],
            audit_trail_ids=[f"mock:{case_id}"],
        )


def _mini_cases():
    repo = Path(__file__).resolve().parent.parent
    golden = json.loads((repo / "data" / "golden_ground_truth.json").read_text())
    return golden[:2]


def test_evaluate_model_on_cases_excludes_failed_from_metrics(tmp_path):
    cases = _mini_cases()
    results = evaluate_model_on_cases(
        evaluator=_FailingEvaluator(),
        cases=cases,
        model_name="mock/fail",
        checkpoint_dir=tmp_path,
    )
    assert results["attempted"] == len(cases)
    assert results["failed"] == len(cases)
    assert results["succeeded"] == 0
    assert results["total_cases"] == 0
    assert all(c.get("status") == "FAILED" for c in results["cases"])


def test_evaluate_model_on_cases_counts_successes(tmp_path):
    cases = _mini_cases()
    results = evaluate_model_on_cases(
        evaluator=_OkEvaluator(),
        cases=cases,
        model_name="mock/ok",
        checkpoint_dir=tmp_path,
    )
    assert results["failed"] == 0
    assert results["succeeded"] == len(cases)
    assert all(c.get("status") == "SUCCEEDED" for c in results["cases"])

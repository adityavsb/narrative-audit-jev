"""Unit tests for the golden evaluation runner."""

import json
from pathlib import Path
import subprocess
import sys

from scripts.run_golden_eval import evaluate_benchmark


def test_evaluate_benchmark_function(tmp_path):
    repo_root = Path(__file__).resolve().parent.parent
    bench_dir = repo_root / "data" / "benchmark"
    golden_path = repo_root / "data" / "golden_ground_truth.json"
    out_file = tmp_path / "test_eval_output.json"

    results = evaluate_benchmark(
        benchmark_dir=bench_dir,
        golden_path=golden_path,
        output_path=out_file,
        verbose=False,
    )

    assert results["total_cases"] == 64
    assert "metrics" in results
    m = results["metrics"]
    assert m["verdict_accuracy"] >= 0.65
    assert m["divergence_category_accuracy"] >= 0.65
    assert m["balanced_accuracy"] >= 0.65
    assert m["f1_score"] >= 0.55
    assert m["brier_score"] <= 0.30
    assert m["expected_calibration_error"] <= 0.25
    assert "maximum_calibration_error" in m
    assert "binary_log_loss" in m
    assert "materiality_weighted_penalty" in m
    assert "adversarial_resistance_rate" in m
    assert m["adversarial_resistance_rate"] >= 0.75
    assert "specificity" in m
    assert "false_discovery_rate" in m
    assert "false_negative_rate" in m

    assert results["by_category"]["ANALYST_QA_DEFLECTION"]["total"] == 9
    assert results["by_category"]["SEGMENT_ANALYSIS"]["total"] == 9

    assert out_file.exists()
    saved = json.loads(out_file.read_text())
    assert saved["total_cases"] == 64
    assert len(saved["cases"]) == 64


def test_run_golden_eval_cli(tmp_path):
    repo_root = Path(__file__).resolve().parent.parent
    out_file = tmp_path / "cli_eval_output.json"

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_golden_eval.py"),
        "--output",
        str(out_file),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
    assert res.returncode == 0
    assert "NARRATIVE AUDIT JEV — GOLDEN BENCHMARK EVALUATION" in res.stdout
    assert "Verdict Accuracy:" in res.stdout
    assert out_file.exists()

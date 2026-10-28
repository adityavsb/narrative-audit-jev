#!/usr/bin/env python3
"""Run automated evaluation of the narrative-audit-jev pipeline over the golden benchmark."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db.schema import FinancialDatabase, default_benchmark_dir, default_golden_path, get_default_db
from src.eval.calibration import (
    binary_log_loss,
    brier_score,
    expected_calibration_error,
    materiality_weighted_loss,
    maximum_calibration_error,
)
from src.evaluators.local_decider import LocalDecisionEvaluator


def evaluate_benchmark(
    benchmark_dir: Optional[Path] = None,
    golden_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Execute end-to-end evaluation against golden ground truth."""
    bench = Path(benchmark_dir) if benchmark_dir else default_benchmark_dir()
    golden_file = Path(golden_path) if golden_path else default_golden_path()
    out_file = Path(output_path) if output_path else REPO_ROOT / "data" / "eval_results.json"

    if not golden_file.exists():
        raise FileNotFoundError(f"Golden benchmark file not found: {golden_file}")

    with open(golden_file, "r") as f:
        cases = json.load(f)

    db = get_default_db(bench)
    evaluator = LocalDecisionEvaluator(db)

    y_true: List[int] = []
    y_pred: List[int] = []
    y_prob: List[float] = []
    materialities: List[str] = []

    verdict_correct = 0
    divergence_correct = 0

    adv_total = 0
    adv_correct = 0

    tp = fp = tn = fn = 0
    by_ticker: Dict[str, Dict[str, int]] = {}
    by_category: Dict[str, Dict[str, int]] = {}
    case_results: List[Dict[str, Any]] = []

    for case in cases:
        cid = case["case_id"]
        ticker = case["ticker"]
        year = int(case["fiscal_year"])
        quarter = str(case["fiscal_quarter"])
        claim_text = case["claim_text"]
        gt = case["ground_truth"]

        expected_verdict = gt["expected_verdict"]
        expected_div = gt["divergence_category"]
        gt_is_disc = bool(gt["is_discrepancy"])

        verdict = evaluator.evaluate(ticker, year, quarter, claim_text, cid)
        pred_is_disc = verdict.is_discrepancy
        pred_verdict = "CONTRADICTED" if pred_is_disc else "SUPPORTED"
        pred_div = verdict.divergence_type.value

        v_match = pred_verdict == expected_verdict
        d_match = pred_div == expected_div
        if v_match:
            verdict_correct += 1
        if d_match:
            divergence_correct += 1

        # Binary confusion matrix for divergence detection
        if gt_is_disc and pred_is_disc:
            tp += 1
        elif not gt_is_disc and pred_is_disc:
            fp += 1
        elif not gt_is_disc and not pred_is_disc:
            tn += 1
        else:
            fn += 1

        # Calibration and loss tracking
        p_disc = verdict.confidence if pred_is_disc else (1.0 - verdict.confidence)
        y_true.append(1 if gt_is_disc else 0)
        y_pred.append(1 if pred_is_disc else 0)
        y_prob.append(p_disc)
        materialities.append(gt.get("materiality", "MEDIUM"))

        # Category and adversarial tracking
        cat = case.get("category", "OTHER")
        if cat == "ADVERSARIAL_PROMPT_INJECTION":
            adv_total += 1
            if v_match and d_match:
                adv_correct += 1

        # Company breakdown
        if ticker not in by_ticker:
            by_ticker[ticker] = {"total": 0, "correct": 0}
        by_ticker[ticker]["total"] += 1
        if v_match and d_match:
            by_ticker[ticker]["correct"] += 1

        # Category breakdown
        if cat not in by_category:
            by_category[cat] = {"total": 0, "correct": 0}
        by_category[cat]["total"] += 1
        if v_match and d_match:
            by_category[cat]["correct"] += 1

        case_results.append({
            "case_id": cid,
            "ticker": ticker,
            "category": cat,
            "expected_verdict": expected_verdict,
            "predicted_verdict": pred_verdict,
            "expected_divergence": expected_div,
            "predicted_divergence": pred_div,
            "confidence": round(verdict.confidence, 4),
            "is_correct": v_match and d_match,
        })

        if verbose:
            status = "PASS" if (v_match and d_match) else "FAIL"
            print(f"[{status}] {cid:10s} ({ticker}) | Exp: {expected_verdict:12s}/{expected_div:24s} | Got: {pred_verdict:12s}/{pred_div:24s}")

    db.close()

    total_n = len(cases)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_acc = (recall + specificity) / 2.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fdr = fp / (tp + fp) if (tp + fp) > 0 else 0.0
    fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0

    bs = brier_score(y_true, y_prob)
    ece = expected_calibration_error(y_true, y_prob, n_bins=10)
    mce = maximum_calibration_error(y_true, y_prob, n_bins=10)
    log_loss = binary_log_loss(y_true, y_prob)
    mat_loss = materiality_weighted_loss(y_true, y_pred, materialities)
    adv_resistance = (adv_correct / adv_total) if adv_total > 0 else 1.0

    results_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total_n,
        "metrics": {
            "verdict_accuracy": round(verdict_correct / total_n, 4),
            "divergence_category_accuracy": round(divergence_correct / total_n, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "specificity": round(specificity, 4),
            "balanced_accuracy": round(balanced_acc, 4),
            "f1_score": round(f1, 4),
            "false_discovery_rate": round(fdr, 4),
            "false_negative_rate": round(fnr, 4),
            "brier_score": round(bs, 4),
            "expected_calibration_error": round(ece, 4),
            "maximum_calibration_error": round(mce, 4),
            "binary_log_loss": round(log_loss, 4),
            "materiality_weighted_penalty": round(mat_loss, 4),
            "adversarial_resistance_rate": round(adv_resistance, 4),
        },
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "by_company": {
            t: {"total": d["total"], "accuracy": round(d["correct"] / d["total"], 4)}
            for t, d in sorted(by_ticker.items())
        },
        "by_category": {
            c: {"total": d["total"], "accuracy": round(d["correct"] / d["total"], 4)}
            for c, d in sorted(by_category.items())
        },
        "cases": case_results,
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results_payload, f, indent=2)

    return results_payload


def print_report(results: Dict[str, Any]) -> None:
    """Print a clean tabular evaluation report."""
    m = results["metrics"]
    cm = results["confusion_matrix"]
    n = results["total_cases"]

    print("=" * 72)
    print("        NARRATIVE AUDIT JEV — GOLDEN BENCHMARK EVALUATION")
    print("=" * 72)
    print(f"Timestamp:       {results.get('timestamp')}")
    print(f"Total Cases:     {n}")
    print("-" * 72)
    print("CLASSIFICATION PERFORMANCE:")
    print(f"  Verdict Accuracy:            {m['verdict_accuracy'] * 100:6.2f}%")
    print(f"  Divergence Category Accuracy:{m['divergence_category_accuracy'] * 100:6.2f}%")
    print(f"  Precision (PPV):             {m['precision'] * 100:6.2f}%")
    print(f"  Recall / Sensitivity (TPR):  {m['recall'] * 100:6.2f}%")
    print(f"  Specificity (TNR):           {m['specificity'] * 100:6.2f}%")
    print(f"  Balanced Accuracy:           {m['balanced_accuracy'] * 100:6.2f}%")
    print(f"  Macro F1 Score:              {m['f1_score'] * 100:6.2f}%")
    print("-" * 72)
    print("ERROR DIAGNOSTICS & CONFUSION MATRIX:")
    print(f"  Confusion Matrix:            TP={cm['tp']}, FP={cm['fp']}, TN={cm['tn']}, FN={cm['fn']}")
    print(f"  False Discovery Rate (FDR):  {m['false_discovery_rate'] * 100:6.2f}%")
    print(f"  False Negative Rate (FNR):   {m['false_negative_rate'] * 100:6.2f}%")
    print("-" * 72)
    print("PROBABILISTIC CALIBRATION & LOSS:")
    print(f"  Brier Score:                 {m['brier_score']:6.4f}  (Brier 1950, lower is better)")
    print(f"  Expected Calibration Error:  {m['expected_calibration_error']:6.4f}  (ECE, Guo et al. 2017)")
    print(f"  Maximum Calibration Error:   {m['maximum_calibration_error']:6.4f}  (MCE worst-bin error)")
    print(f"  Binary Log Loss (NLL):       {m['binary_log_loss']:6.4f}  (cross-entropy penalty)")
    print("-" * 72)
    print("GOVERNANCE & ROBUSTNESS:")
    print(f"  SAB 99 Materiality Penalty:  {m['materiality_weighted_penalty']:6.4f}  (SEC materiality weighting)")
    print(f"  Adversarial Resistance:      {m['adversarial_resistance_rate'] * 100:6.2f}% (corporate directive override defense)")
    print("-" * 72)
    print("BREAKDOWN BY COMPANY:")
    for ticker, d in sorted(results["by_company"].items()):
        print(f"  {ticker:6s}: {d['accuracy'] * 100:6.2f}% ({d['total']} cases)")
    print("-" * 72)
    print("BREAKDOWN BY CATEGORY:")
    for cat, d in sorted(results["by_category"].items()):
        print(f"  {cat:32s}: {d['accuracy'] * 100:6.2f}% ({d['total']} cases)")
    print("=" * 72)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run benchmark evaluation over golden test cases for narrative-audit-jev."
    )
    parser.add_argument("--benchmark-dir", type=Path, default=None, help="Benchmark directory")
    parser.add_argument("--golden-path", type=Path, default=None, help="Golden ground truth path")
    parser.add_argument("--output", type=Path, default=None, help="Output metrics JSON path")
    parser.add_argument("--fail-under", type=float, default=0.65, help="Minimum verdict accuracy required to exit 0 (default: 0.65)")
    parser.add_argument("--verbose", action="store_true", help="Print per-case evaluations")
    args = parser.parse_args(argv)

    results = evaluate_benchmark(
        benchmark_dir=args.benchmark_dir,
        golden_path=args.golden_path,
        output_path=args.output,
        verbose=args.verbose,
    )
    print_report(results)

    acc = results["metrics"]["verdict_accuracy"]
    return 0 if acc >= args.fail_under else 1


if __name__ == "__main__":
    sys.exit(main())

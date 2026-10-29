#!/usr/bin/env python3
"""Multi-model staged OpenRouter evaluation harness for narrative-audit-jev."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db.schema import default_benchmark_dir, default_golden_path, get_default_db
from src.eval.calibration import (
    binary_log_loss,
    brier_score,
    expected_calibration_error,
    materiality_weighted_loss,
    maximum_calibration_error,
)
from src.evaluators.local_decider import LocalDecisionEvaluator
from src.evaluators.openrouter_decider import (
    OpenRouterDecisionEvaluator,
    load_openrouter_env,
    mask_secret,
)


def sanitize_slug(model_id: str) -> str:
    """Sanitize model slug for filesystem paths."""
    return model_id.replace("/", "_").replace(":", "_")


def run_single_case_smoke_test(
    evaluator: OpenRouterDecisionEvaluator,
    case: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a single test case smoke check."""
    cid = case["case_id"]
    ticker = case["ticker"]
    fy = int(case["fiscal_year"])
    fq = str(case["fiscal_quarter"])
    claim = case["claim_text"]
    gt = case["ground_truth"]

    print(f"\n[*] DISPATCHING CHECK-RUN:")
    print(f"    Model:      {evaluator.model}")
    print(f"    Case ID:    {cid} ({ticker} FY{fy} {fq})")
    print(f"    Claim:      \"{claim}\"")
    print(f"    Expected:   {gt['expected_verdict']} / {gt['divergence_category']}")

    start = time.time()
    verdict = evaluator.evaluate(ticker, fy, fq, claim, cid)
    latency = (time.time() - start) * 1000.0

    pred_verdict = "CONTRADICTED" if verdict.is_discrepancy else "SUPPORTED"
    pred_div = verdict.divergence_type.value
    v_match = pred_verdict == gt["expected_verdict"]
    d_match = pred_div == gt["divergence_category"]

    telem = evaluator.last_telemetry
    print(f"\n[+] API CHECK-RUN SUCCEEDED:")
    print(f"    Predicted:  {pred_verdict} / {pred_div} (Confidence: {verdict.confidence:.4f})")
    print(f"    Match:      {'PASS' if (v_match and d_match) else 'DIVERGED'}")
    print(f"    Latency:    {latency:.1f} ms")
    print(f"    Tokens:     In={telem.get('prompt_tokens', 0)}, Out={telem.get('completion_tokens', 0)}")
    print(f"    Summary:    {verdict.summary[:140]}...")
    print(f"    FactChecks: {len(verdict.fact_checks)} items reconciled")

    return {
        "model": evaluator.model,
        "case_id": cid,
        "is_correct": v_match and d_match,
        "verdict_match": v_match,
        "divergence_match": d_match,
        "predicted_verdict": pred_verdict,
        "predicted_divergence": pred_div,
        "confidence": verdict.confidence,
        "telemetry": telem,
    }


def evaluate_model_on_cases(
    evaluator: Any,
    cases: List[Dict[str, Any]],
    model_name: str,
    checkpoint_dir: Path,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Evaluate one model across all cases with incremental checkpoint caching."""
    checkpoint_file = checkpoint_dir / f"checkpoint_{sanitize_slug(model_name)}.json"
    cached_results: Dict[str, Dict[str, Any]] = {}

    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r") as f:
                cached_results = json.load(f)
            print(f"[*] Resumed from checkpoint: {len(cached_results)}/{len(cases)} cases cached for {model_name}")
        except Exception:
            cached_results = {}

    y_true: List[int] = []
    y_pred: List[int] = []
    y_prob: List[float] = []
    materialities: List[str] = []

    verdict_correct = 0
    divergence_correct = 0
    adv_total = 0
    adv_correct = 0
    tp = fp = tn = fn = 0

    by_category: Dict[str, Dict[str, int]] = {}
    latencies: List[float] = []
    total_prompt_tokens = 0
    total_comp_tokens = 0
    all_case_results: List[Dict[str, Any]] = []

    for idx, case in enumerate(cases, 1):
        cid = case["case_id"]
        ticker = case["ticker"]
        fy = int(case["fiscal_year"])
        fq = str(case["fiscal_quarter"])
        claim = case["claim_text"]
        gt = case["ground_truth"]
        cat = case.get("category", "OTHER")

        gt_is_disc = bool(gt["is_discrepancy"])
        expected_verdict = gt["expected_verdict"]
        expected_div = gt["divergence_category"]

        # Check if cached
        if cid in cached_results:
            res = cached_results[cid]
            pred_is_disc = res["is_discrepancy"]
            pred_verdict = res["predicted_verdict"]
            pred_div = res["predicted_divergence"]
            conf = res["confidence"]
            p_disc = conf if pred_is_disc else (1.0 - conf)
            lat = res.get("latency_ms", 0.0)
            in_tok = res.get("prompt_tokens", 0)
            out_tok = res.get("completion_tokens", 0)
            v_match = pred_verdict == expected_verdict
            d_match = pred_div == expected_div
            is_pass = v_match and d_match
            print(f"  [CACHE] {idx:02d}/{len(cases)} {cid:10s} -> {pred_verdict}/{pred_div} ({'PASS' if is_pass else 'FAIL'})", flush=True)
        else:
            print(f"  [EVAL]  {idx:02d}/{len(cases)} {cid:10s} ({ticker} FY{fy} {fq})...", end=" ", flush=True)
            t0 = time.time()
            verdict = evaluator.evaluate(ticker, fy, fq, claim, cid)
            lat = (time.time() - t0) * 1000.0

            pred_is_disc = verdict.is_discrepancy
            pred_verdict = "CONTRADICTED" if pred_is_disc else "SUPPORTED"
            pred_div = verdict.divergence_type.value
            conf = verdict.confidence
            p_disc = conf if pred_is_disc else (1.0 - conf)

            telem = getattr(evaluator, "last_telemetry", {})
            in_tok = telem.get("prompt_tokens", 0)
            out_tok = telem.get("completion_tokens", 0)

            v_match = pred_verdict == expected_verdict
            d_match = pred_div == expected_div
            is_pass = v_match and d_match
            print(f"[{'PASS' if is_pass else 'FAIL'}] ({lat/1000.0:.1f}s) -> {pred_verdict}/{pred_div} (Conf: {conf:.2f})", flush=True)

            # Save to checkpoint with complete reproducibility metadata
            cached_results[cid] = {
                "case_id": cid,
                "ticker": ticker,
                "category": cat,
                "claim_text": claim,
                "expected_verdict": expected_verdict,
                "expected_divergence": expected_div,
                "is_discrepancy": pred_is_disc,
                "predicted_verdict": pred_verdict,
                "predicted_divergence": pred_div,
                "confidence": round(conf, 4),
                "is_correct": is_pass,
                "summary": getattr(verdict, "summary", ""),
                "supporting_evidence": getattr(verdict, "supporting_evidence", []),
                "fact_checks": [fc.model_dump() for fc in getattr(verdict, "fact_checks", [])],
                "latency_ms": round(lat, 1),
                "prompt_tokens": in_tok,
                "completion_tokens": out_tok,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(checkpoint_file, "w") as f:
                json.dump(cached_results, f, indent=2)

        latencies.append(lat)
        total_prompt_tokens += in_tok
        total_comp_tokens += out_tok

        if v_match:
            verdict_correct += 1
        if d_match:
            divergence_correct += 1

        if gt_is_disc and pred_is_disc:
            tp += 1
        elif not gt_is_disc and pred_is_disc:
            fp += 1
        elif not gt_is_disc and not pred_is_disc:
            tn += 1
        else:
            fn += 1

        y_true.append(1 if gt_is_disc else 0)
        y_pred.append(1 if pred_is_disc else 0)
        y_prob.append(p_disc)
        materialities.append(gt.get("materiality", "MEDIUM"))

        if cat == "ADVERSARIAL_PROMPT_INJECTION":
            adv_total += 1
            if is_pass:
                adv_correct += 1

        if cat not in by_category:
            by_category[cat] = {"total": 0, "correct": 0}
        by_category[cat]["total"] += 1
        if is_pass:
            by_category[cat]["correct"] += 1

        all_case_results.append({
            "case_id": cid,
            "category": cat,
            "is_correct": is_pass,
            "pred_verdict": pred_verdict,
            "pred_divergence": pred_div,
            "confidence": round(conf, 4),
        })

    total_n = len(cases)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_acc = (recall + specificity) / 2.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "model": model_name,
        "total_cases": total_n,
        "metrics": {
            "verdict_accuracy": round(verdict_correct / total_n, 4),
            "divergence_accuracy": round(divergence_correct / total_n, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "specificity": round(specificity, 4),
            "balanced_accuracy": round(balanced_acc, 4),
            "f1_score": round(f1, 4),
            "brier_score": round(brier_score(y_true, y_prob), 4),
            "ece": round(expected_calibration_error(y_true, y_prob, n_bins=10), 4),
            "mce": round(maximum_calibration_error(y_true, y_prob, n_bins=10), 4),
            "binary_log_loss": round(binary_log_loss(y_true, y_prob), 4),
            "sab99_penalty": round(materiality_weighted_loss(y_true, y_pred, materialities), 4),
            "adversarial_resistance": round((adv_correct / adv_total) if adv_total > 0 else 1.0, 4),
        },
        "by_category": {
            c: {"total": d["total"], "accuracy": round(d["correct"] / d["total"], 4)}
            for c, d in sorted(by_category.items())
        },
        "telemetry": {
            "mean_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_comp_tokens,
        },
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "cases": all_case_results,
    }


def print_comparison_table(results: List[Dict[str, Any]]) -> None:
    """Print clean comparison table comparing local baseline against OpenRouter models."""
    print("\n" + "=" * 90)
    print("      NARRATIVE AUDIT JEV — MULTI-MODEL BENCHMARK COMPARISON LEADERBOARD")
    print("=" * 90)
    header = f"{'Model':<32} | {'Accuracy':<10} | {'Brier':<8} | {'ECE':<8} | {'QA Deflect':<12} | {'Footnotes':<10}"
    print(header)
    print("-" * 90)

    for r in results:
        m = r["metrics"]
        cats = r["by_category"]
        qa_acc = cats.get("ANALYST_QA_DEFLECTION", {}).get("accuracy", 0.0) * 100
        seg_acc = cats.get("SEGMENT_ANALYSIS", {}).get("accuracy", 0.0) * 100
        print(
            f"{r['model']:<32} | "
            f"{m['verdict_accuracy'] * 100:6.2f}%    | "
            f"{m['brier_score']:6.4f}   | "
            f"{m['ece']:6.4f}   | "
            f"{qa_acc:6.1f}%       | "
            f"{seg_acc:6.1f}%"
        )
    print("=" * 90)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run staged OpenRouter multi-model evaluation for narrative-audit-jev."
    )
    parser.add_argument(
        "--stage",
        choices=["check-one", "check-remaining", "full"],
        default="check-one",
        help="Evaluation stage: check-one (Model 1 x 1 case), check-remaining (Models 2&3 x 1 case), full (All models x 64 cases)",
    )
    parser.add_argument("--case-id", type=str, default="AURA_001", help="Case ID to use for check runs (default: AURA_001)")
    parser.add_argument("--model1", type=str, default=None, help="Model 1 ID (overrides OPENROUTER_MODEL_1)")
    parser.add_argument("--model2", type=str, default=None, help="Model 2 ID (overrides OPENROUTER_MODEL_2)")
    parser.add_argument("--model3", type=str, default=None, help="Model 3 ID (overrides OPENROUTER_MODEL_3)")
    parser.add_argument("--delay", type=float, default=None, help="Delay between requests in seconds")
    parser.add_argument("--verbose", action="store_true", help="Print per-case logs")
    args = parser.parse_args()

    env_cfg = load_openrouter_env()
    api_key = env_cfg.get("OPENROUTER_API_KEY", "")

    m1 = args.model1 or env_cfg.get("OPENROUTER_MODEL_1", "deepseek/deepseek-v4.1-flash")
    m2 = args.model2 or env_cfg.get("OPENROUTER_MODEL_2", "qwen/qwen3.7-flash")
    m3 = args.model3 or env_cfg.get("OPENROUTER_MODEL_3", "perplexity/pplx-decider-flash-v1.2")
    delay = args.delay if args.delay is not None else float(env_cfg.get("OPENROUTER_REQUEST_DELAY_SEC", 1.0))

    golden_file = default_golden_path()
    with open(golden_file, "r") as f:
        cases = json.load(f)

    # Find target check case
    check_case = next((c for c in cases if c["case_id"] == args.case_id), cases[0])

    print("=" * 70)
    print("      NARRATIVE AUDIT JEV — OPENROUTER MULTI-MODEL HARNESS")
    print("=" * 70)
    print(f"[*] Stage:           {args.stage}")
    print(f"[*] API Key Status:  {mask_secret(api_key)}")
    print(f"[*] Model 1 (Std):   {m1}")
    print(f"[*] Model 2 (Reason):{m2}")
    print(f"[*] Model 3 (Decide):{m3}")
    print(f"[*] Total Benchmark: {len(cases)} golden cases")
    print("-" * 70)

    if not api_key or api_key.startswith("PASTE_YOUR_"):
        print("[!] ERROR: OPENROUTER_API_KEY is not set.")
        print("    Please paste your OpenRouter key into .env:")
        print("    OPENROUTER_API_KEY=sk-or-v1-...")
        return 1

    db = get_default_db()
    checkpoint_dir = REPO_ROOT / "data" / "eval_runs"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    if args.stage == "check-one":
        evaluator = OpenRouterDecisionEvaluator(db, model=m1, api_key=api_key, request_delay_sec=delay)
        run_single_case_smoke_test(evaluator, check_case)
        print("\n[✓] Stage 1 (Check-Run Model 1) completed successfully!")
        print("    Next step: Run 'make check-models-2-3' to check the remaining 2 models.")
        return 0

    elif args.stage == "check-remaining":
        for mid in [m2, m3]:
            evaluator = OpenRouterDecisionEvaluator(db, model=mid, api_key=api_key, request_delay_sec=delay)
            run_single_case_smoke_test(evaluator, check_case)
        print("\n[✓] Stage 2 (Check-Run Models 2 & 3) completed successfully!")
        print("    All 3 models are verified. Next step: Run 'make eval-openrouter' for the full 64-case sweep.")
        return 0

    elif args.stage == "full":
        # 1. Evaluate Local Heuristic Baseline first
        print("\n[*] Evaluating 1/4: Local Deterministic Rule Baseline...")
        local_evaluator = LocalDecisionEvaluator(db)
        local_results = evaluate_model_on_cases(
            evaluator=local_evaluator,
            cases=cases,
            model_name="Local Rule Engine (Heuristic)",
            checkpoint_dir=checkpoint_dir,
            verbose=args.verbose,
        )

        all_results = [local_results]

        # 2. Evaluate the 3 OpenRouter Models
        models_to_run = [m1, m2, m3]
        for idx, mid in enumerate(models_to_run, 2):
            print(f"\n[*] Evaluating {idx}/4: OpenRouter Model '{mid}'...")
            evaluator = OpenRouterDecisionEvaluator(db, model=mid, api_key=api_key, request_delay_sec=delay)
            m_res = evaluate_model_on_cases(
                evaluator=evaluator,
                cases=cases,
                model_name=mid,
                checkpoint_dir=checkpoint_dir,
                verbose=args.verbose,
            )
            all_results.append(m_res)

        print_comparison_table(all_results)

        summary_file = checkpoint_dir / "openrouter_comparison_summary.json"
        with open(summary_file, "w") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cohort": models_to_run,
                "results": all_results,
            }, f, indent=2)
        print(f"\n[✓] Full evaluation report saved to: {summary_file}")

        # Generate clean Markdown summary table for publication / replication docs
        md_file = checkpoint_dir / "openrouter_comparison_report.md"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        md_lines = [
            f"# Multi-Model Benchmark Comparison Report",
            f"",
            f"**Evaluation Timestamp:** {now_str}  ",
            f"**Benchmark Corpus:** 64 Synthetic Golden Cases (`data/golden_ground_truth.json`)  ",
            f"**Deterministic Parameters:** `temperature=0.0`, `seed=42`  ",
            f"",
            f"## 1. Comparative Leaderboard",
            f"",
            f"| Model | Verdict Accuracy | Category Accuracy | Brier Score | ECE | Log Loss | Q&A Deflections | Footnote Reclasses | Mean Latency |",
            f"|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]
        for r in all_results:
            m = r["metrics"]
            t = r["telemetry"]
            cats = r["by_category"]
            qa_acc = cats.get("ANALYST_QA_DEFLECTION", {}).get("accuracy", 0.0) * 100
            seg_acc = cats.get("SEGMENT_ANALYSIS", {}).get("accuracy", 0.0) * 100
            md_lines.append(
                f"| **{r['model']}** | {m['verdict_accuracy']*100:.2f}% | {m['divergence_accuracy']*100:.2f}% | {m['brier_score']:.4f} | {m['ece']:.4f} | {m['binary_log_loss']:.4f} | {qa_acc:.1f}% | {seg_acc:.1f}% | {t['mean_latency_ms']:.0f} ms |"
            )

        md_lines.extend([
            f"",
            f"## 2. Reproduction Instructions",
            f"",
            f"To replicate these results with identical prompts, financials, and ground truth:",
            f"```bash",
            f"# Verify data integrity",
            f"python narrative-audit-jev/src/db/schema.py --validate",
            f"",
            f"# Re-run multi-model benchmark evaluation",
            f"python narrative-audit-jev/scripts/run_openrouter_eval.py --stage full",
            f"```",
            f"",
            f"All per-case API responses, predicted verdicts, confidence scores, and token telemetry are versioned in `data/eval_runs/checkpoint_*.json`.",
        ])
        with open(md_file, "w") as f:
            f.write("\n".join(md_lines) + "\n")
        print(f"[✓] Markdown comparison report saved to: {md_file}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

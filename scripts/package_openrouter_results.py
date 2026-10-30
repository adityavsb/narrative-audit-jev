#!/usr/bin/env python3
"""Package local OpenRouter eval_runs into a redacted, git-tracked evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb

FALLBACK_MARKER = "Evaluation fallback after"
EXPECTED_CASES = 64

PUBLISH_CHECKPOINTS: Dict[str, str] = {
    "deepseek_deepseek-v4.1-flash": "checkpoint_deepseek_deepseek-v4.1-flash.json",
    "perplexity_pplx-decider-flash-v1.2": "checkpoint_perplexity_pplx-decider-flash-v1.2.json",
    "qwen_qwen3.7-flash": "checkpoint_qwen_qwen3.7-flash.json",
    "local_rule_engine_heuristic": "checkpoint_Local Rule Engine (Heuristic).json",
}

RESULT_MODEL_TO_SLUG: Dict[str, str] = {
    "Local Rule Engine (Heuristic)": "local_rule_engine_heuristic",
    "deepseek/deepseek-v4.1-flash": "deepseek_deepseek-v4.1-flash",
    "qwen/qwen3.7-flash": "qwen_qwen3.7-flash",
    "perplexity/pplx-decider-flash-v1.2": "perplexity_pplx-decider-flash-v1.2",
}

SECRET_PATTERNS = [
    re.compile(r"sk-or-v1-[a-zA-Z0-9_-]{10,}"),
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
]


def _token_stats_from_checkpoint(checkpoint: Dict[str, Any]) -> Tuple[float, float]:
    totals = [
        int(rec.get("prompt_tokens", 0)) + int(rec.get("completion_tokens", 0))
        for rec in checkpoint.values()
        if isinstance(rec, dict)
    ]
    if not totals:
        return 0.0, 0.0
    return round(statistics.mean(totals), 1), round(statistics.median(totals), 1)


def _enrich_summary_token_telemetry(
    summary: Dict[str, Any], checkpoints_by_slug: Dict[str, Dict[str, Any]]
) -> None:
    for block in summary.get("results", []):
        slug = RESULT_MODEL_TO_SLUG.get(str(block.get("model", "")))
        if not slug or slug not in checkpoints_by_slug:
            continue
        mean_t, med_t = _token_stats_from_checkpoint(checkpoints_by_slug[slug])
        telem = block.setdefault("telemetry", {})
        telem["mean_tokens_per_case"] = mean_t
        telem["median_tokens_per_case"] = med_t


def _git_head() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _run_id_from_summary(summary: Dict[str, Any]) -> str:
    ts = summary.get("timestamp")
    if ts:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _scan_fallbacks(checkpoint: Dict[str, Any]) -> List[str]:
    hits: List[str] = []
    for case_id, rec in checkpoint.items():
        summary = rec.get("summary") if isinstance(rec, dict) else None
        if isinstance(summary, str) and FALLBACK_MARKER in summary:
            hits.append(str(case_id))
    return hits


def _redact_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_obj(v) for v in obj]
    if isinstance(obj, str):
        redacted = obj
        for pat in SECRET_PATTERNS:
            redacted = pat.sub("[REDACTED]", redacted)
        return redacted
    return obj


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_sha256sums(bundle_dir: Path, rel_paths: List[str]) -> None:
    lines: List[str] = []
    for rel in sorted(rel_paths):
        digest = _sha256_file(bundle_dir / rel)
        lines.append(f"{digest}  {rel}")
    (bundle_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_report_md(bundle_dir: Path, summary: Dict[str, Any]) -> None:
    ts = summary.get("timestamp", "")
    lines = [
        "# Multi-Model Benchmark Comparison Report",
        "",
        f"**Evaluation Timestamp:** {ts}  ",
        "**Benchmark Corpus:** 64 Synthetic Golden Cases (`data/golden_ground_truth.json`)  ",
        "**Deterministic Parameters:** `temperature=0.0`, `seed=42`  ",
        "",
        "## 1. Comparative Leaderboard",
        "",
        "| Model | Verdict Accuracy | Category Accuracy | Brier Score | ECE | Log Loss | "
        "Q&A Deflections | Footnote Reclasses | Mean Latency | Avg Tokens / Case | Median Tokens / Case |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for block in summary.get("results", []):
        m = block.get("metrics", {})
        t = block.get("telemetry", {})
        cats = block.get("by_category", {})
        qa = cats.get("ANALYST_QA_DEFLECTION", {}).get("accuracy", 0.0) * 100
        seg = cats.get("SEGMENT_ANALYSIS", {}).get("accuracy", 0.0) * 100
        lines.append(
            f"| **{block.get('model', '')}** | "
            f"{m.get('verdict_accuracy', 0) * 100:.2f}% | "
            f"{m.get('divergence_accuracy', 0) * 100:.2f}% | "
            f"{m.get('brier_score', 0):.4f} | "
            f"{m.get('ece', 0):.4f} | "
            f"{m.get('binary_log_loss', 0):.4f} | "
            f"{qa:.1f}% | {seg:.1f}% | "
            f"{t.get('mean_latency_ms', 0):.0f} ms | "
            f"{t.get('mean_tokens_per_case', 0):.0f} | "
            f"{t.get('median_tokens_per_case', 0):.0f} |"
        )
    lines.extend(
        [
            "",
            "Token counts are prompt + completion tokens per golden case (mean and median over 64 cases).",
            "",
            "## 2. Reproduction Instructions",
            "",
            "See `make package-openrouter-results` and tracked files in this bundle directory.",
            "",
        ]
    )
    (bundle_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def package_results(source_dir: Path, dest_root: Path) -> Path:
    summary_path = source_dir / "openrouter_comparison_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Missing {summary_path}")

    summary_raw = json.loads(summary_path.read_text(encoding="utf-8"))
    run_id = _run_id_from_summary(summary_raw)
    bundle_dir = dest_root / run_id
    predictions_dir = bundle_dir / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)

    fallback_by_slug: Dict[str, List[str]] = {}
    source_files: List[str] = [str(summary_path.relative_to(REPO_ROOT))]
    checkpoints_by_slug: Dict[str, Dict[str, Any]] = {}

    for slug, filename in PUBLISH_CHECKPOINTS.items():
        ck_path = source_dir / filename
        if not ck_path.is_file():
            raise FileNotFoundError(f"Missing checkpoint {ck_path}")
        checkpoint = json.loads(ck_path.read_text(encoding="utf-8"))
        if len(checkpoint) != EXPECTED_CASES:
            raise ValueError(f"{filename}: expected {EXPECTED_CASES} cases, got {len(checkpoint)}")
        fallback_by_slug[slug] = _scan_fallbacks(checkpoint)
        checkpoints_by_slug[slug] = checkpoint
        redacted = _redact_obj(checkpoint)
        out_path = predictions_dir / f"{slug}.json"
        out_path.write_text(json.dumps(redacted, indent=2), encoding="utf-8")
        source_files.append(str(ck_path.relative_to(REPO_ROOT)))

    _enrich_summary_token_telemetry(summary_raw, checkpoints_by_slug)
    summary_redacted = _redact_obj(summary_raw)
    (bundle_dir / "summary.json").write_text(json.dumps(summary_redacted, indent=2), encoding="utf-8")

    rel_paths = ["summary.json", "manifest.json"]
    _write_report_md(bundle_dir, summary_redacted)
    rel_paths.append("report.md")

    for slug in PUBLISH_CHECKPOINTS:
        rel_paths.append(f"predictions/{slug}.json")

    all_fallback_ids: Set[str] = set()
    for ids in fallback_by_slug.values():
        all_fallback_ids.update(ids)

    manifest: Dict[str, Any] = {
        "source": "local_eval_runs_import",
        "no_api_rerun": True,
        "synthetic_corpus": True,
        "git_commit_at_import": _git_head(),
        "import_utc": datetime.now(timezone.utc).isoformat(),
        "summary_timestamp": summary_raw.get("timestamp"),
        "source_files": source_files,
        "python_version": platform.python_version(),
        "duckdb_version": duckdb.__version__,
        "model_ids": summary_raw.get("cohort", []),
        "openrouter_defaults": {
            "temperature": 0.0,
            "seed": 42,
            "max_retries": 3,
        },
        "cases_per_publish_checkpoint": EXPECTED_CASES,
        "contains_fail_open_fallbacks": bool(all_fallback_ids),
        "fallback_case_ids": sorted(all_fallback_ids),
        "fallback_by_model": fallback_by_slug,
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _write_sha256sums(bundle_dir, rel_paths)
    rel_paths.append("SHA256SUMS")
    return bundle_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Package local eval_runs into data/results/openrouter/")
    parser.add_argument(
        "--source",
        type=Path,
        default=REPO_ROOT / "data" / "eval_runs",
        help="Directory containing openrouter_comparison_summary.json and checkpoints",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=REPO_ROOT / "data" / "results" / "openrouter",
        help="Output root for versioned bundles",
    )
    args = parser.parse_args()

    bundle = package_results(args.source.resolve(), args.dest.resolve())
    print(f"[ok] Wrote evidence bundle: {bundle.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

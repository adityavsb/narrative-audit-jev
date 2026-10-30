# Multi-Model Benchmark Comparison Report

**Evaluation Timestamp:** 2026-10-29T13:42:11.989522+00:00  
**Benchmark Corpus:** 64 Synthetic Golden Cases (`data/golden_ground_truth.json`)  
**Deterministic Parameters:** `temperature=0.0`, `seed=42`  

## 1. Comparative Leaderboard

| Model | Verdict Accuracy | Category Accuracy | Brier Score | ECE | Log Loss | Q&A Deflections | Footnote Reclasses | Mean Latency | Avg Tokens / Case | Median Tokens / Case |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Local Rule Engine (Heuristic)** | 68.75% | 68.75% | 0.2186 | 0.1103 | 0.6293 | 22.2% | 22.2% | 3 ms | 0 | 0 |
| **deepseek/deepseek-v4.1-flash** | 90.62% | 89.06% | 0.0845 | 0.0859 | 0.2927 | 100.0% | 88.9% | 26393 ms | 6639 | 6168 |
| **qwen/qwen3.7-flash** | 84.38% | 79.69% | 0.1387 | 0.1420 | 0.4762 | 100.0% | 77.8% | 38529 ms | 6580 | 6462 |
| **perplexity/pplx-decider-flash-v1.2** | 85.94% | 84.38% | 0.1263 | 0.1396 | 0.3681 | 100.0% | 88.9% | 1438 ms | 5284 | 5308 |

Token counts are prompt + completion tokens per golden case (mean and median over 64 cases).

## 2. Reproduction Instructions

See `make package-openrouter-results` and tracked files in this bundle directory.


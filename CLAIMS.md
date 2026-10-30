# Verified claims ledger

Numbers in README and public docs must appear here with traceable evidence. `[unverified]` means not measured in this repo yet.

| Claim as written | Where used | Evidence | Git commit | Verification command | Reviewed by | Reviewed UTC |
|---|---|---|---|---|---|---|
| 4 fictional companies (AURA, NXUS, SYNX, VORS) | README, DATA_CATALOG | `make data-check` / `tests/test_schema.py::test_companies_loaded` | 740e670 | `.venv/bin/pytest tests/test_schema.py::test_companies_loaded` | Aditya Bhadoria | 2026-10-30 |
| 32 quarterly financial rows (8 per company) | README, DATA_CATALOG | `src/db/schema.py` `EXPECTED_QUARTERS`; `tests/test_schema.py::test_quarterly_financials_count_and_accounting_identities` | 740e670 | `.venv/bin/pytest tests/test_schema.py::test_quarterly_financials_count_and_accounting_identities` | Aditya Bhadoria | 2026-10-30 |
| 64 golden evaluation cases | README, data-check | `data/golden_ground_truth.json` (64 objects); `tests/test_ground_truth.py`; `src/db/schema.py` `EXPECTED_GOLDEN_CASES` | 740e670 | `.venv/bin/pytest tests/test_ground_truth.py` | Aditya Bhadoria | 2026-10-30 |
| 12 transcript snippets (3 per company) | DATA_CATALOG | `make data-check` stats; `tests/test_schema.py::test_transcripts_presence` (≥12) | 740e670 | `.venv/bin/make data-check` | Aditya Bhadoria | 2026-10-30 |
| 9 segment disclosure rows | metrics_log / data-check | `FinancialDatabase.get_summary_stats()` segments_count | 740e670 | `.venv/bin/make data-check` | Aditya Bhadoria | 2026-10-30 |
| Aura gross margin Q1 2024 ≈ 79% | scenario prose | `tests/test_semantic_metrics.py` (0.79); `data/benchmark/auracloud/financials.json` | 740e670 | `.venv/bin/pytest tests/test_semantic_metrics.py` | Aditya Bhadoria | 2026-10-30 |
| Aura gross margin Q4 2025 ≈ 61% | scenario prose | `tests/test_semantic_metrics.py` (0.61); golden `AURA_001` verified_numbers | 740e670 | `.venv/bin/pytest tests/test_semantic_metrics.py` | Aditya Bhadoria | 2026-10-30 |
| Aura gross margin delta ≈ −1800 bps (Q1 2024 → Q4 2025) | README scenario | `data/golden_ground_truth.json` `AURA_001` `gross_margin_delta_bps`: -1800 | 740e670 | `.venv/bin/pytest tests/test_semantic_metrics.py` | Aditya Bhadoria | 2026-10-30 |
| Nexus Q4 capex YoY growth ≈ 128.6% (42→96M) | golden / transcript | `data/golden_ground_truth.json` `NXUS_001` `capex_growth_yoy`: 1.2857 | 740e670 | `tests/test_ground_truth.py` | Aditya Bhadoria | 2026-10-30 |
| Nexus FY2025 FCF total −$144M | golden | `data/golden_ground_truth.json` `NXUS_002` `total_fy2025_fcf`: -144 | 740e670 | `data/golden_ground_truth.json` | Aditya Bhadoria | 2026-10-30 |
| Synthetix claimed AI ARR $80M; $65M reclassified (81.25%) | scenario | `data/golden_ground_truth.json` `SYNX_001` verified_numbers | 740e670 | `data/golden_ground_truth.json` | Aditya Bhadoria | 2026-10-30 |
| Vortex control gross margin Q4 2025 ≈ 79.14% | tests | `tests/test_numeric_guardrail.py::test_verify_vortex_clean_control` | 740e670 | `.venv/bin/pytest tests/test_numeric_guardrail.py::test_verify_vortex_clean_control` | Aditya Bhadoria | 2026-10-30 |
| pytest suite size (112 tests) | README badge | `.venv/bin/pytest tests/ --co -q` | unreviewed | `.venv/bin/pytest tests/` | unreviewed | — |
| Local baseline verdict accuracy (68.75%) | README leaderboard | `data/eval_results.json` | 740e670 | `.venv/bin/python scripts/run_golden_eval.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline Analyst Q&A Deflection accuracy (22.22%) | README leaderboard | `data/eval_results.json` | 740e670 | `.venv/bin/python scripts/run_golden_eval.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline Segment Footnote accuracy (22.22%) | README leaderboard | `data/eval_results.json` | 740e670 | `.venv/bin/python scripts/run_golden_eval.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline Brier score (0.2186) | README leaderboard | `data/eval_results.json` | 740e670 | `src/eval/calibration.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline Expected Calibration Error (0.1103) | README leaderboard | `data/eval_results.json` | 740e670 | `src/eval/calibration.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline Maximum Calibration Error (0.2500) | README leaderboard | `data/eval_results.json` | 740e670 | `src/eval/calibration.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline Binary Log Loss (0.6293) | README leaderboard | `data/eval_results.json` | 740e670 | `src/eval/calibration.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline SAB 99 Materiality Penalty (0.3688) | README leaderboard | `data/eval_results.json` | 740e670 | `src/eval/calibration.py` | Aditya Bhadoria | 2026-10-30 |
| Local baseline Adversarial Resistance (100.00%) | README leaderboard | `data/eval_results.json` | 740e670 | `.venv/bin/python scripts/run_golden_eval.py` | Aditya Bhadoria | 2026-10-30 |
| OpenRouter multi-model leaderboard (64-case sweep) | README §117–150 | `data/results/openrouter/2026-10-29T134211Z/summary.json` + `SHA256SUMS` | unreviewed | `make package-openrouter-results`; `sha256sum -c data/results/openrouter/2026-10-29T134211Z/SHA256SUMS` | Aditya Bhadoria | 2026-10-30 |
| Public markdown overclaiming grep hits (0) | CI / Makefile | `make grep-gate` / `scripts/grep_gate.sh` (0 hits) | 740e670 | `make grep-gate` | Aditya Bhadoria | 2026-10-30 |
| AST validation ~1.2 ms per query | docs/decisions.md ADR-01 | `[unverified]` — no benchmark script in repo | — | — | unreviewed | — |
| LLM inference 500–2000 ms | removed from README | `[unverified]` — not measured here | — | — | unreviewed | — |

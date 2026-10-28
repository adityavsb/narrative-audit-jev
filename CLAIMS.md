# Verified claims ledger

Numbers in README and public docs must appear here with a traceable source. `[unverified]` means not measured in this repo yet.

| Claim as written | Where used | Source artefact / lookup | Verified by | Date |
|---|---|---|---|---|
| 4 fictional companies (AURA, NXUS, SYNX, VORS) | README, DATA_CATALOG | `make data-check` / `tests/test_schema.py::test_companies_loaded` | agent | 2026-10-26 |
| 32 quarterly financial rows (8 per company) | README, DATA_CATALOG | `src/db/schema.py` `EXPECTED_QUARTERS`; `tests/test_schema.py::test_quarterly_financials_count_and_accounting_identities` | agent | 2026-10-26 |
| 52 golden evaluation cases | README, data-check | `data/golden_ground_truth.json` (52 objects); `tests/test_ground_truth.py`; `src/db/schema.py` `EXPECTED_GOLDEN_CASES` | agent | 2026-10-26 |
| 12 transcript snippets (3 per company) | DATA_CATALOG | `make data-check` stats; `tests/test_schema.py::test_transcripts_presence` (≥12) | agent | 2026-10-26 |
| 9 segment disclosure rows | metrics_log / data-check | `FinancialDatabase.get_summary_stats()` segments_count | agent | 2026-10-26 |
| Aura gross margin Q1 2024 ≈ 79% | scenario prose | `tests/test_semantic_metrics.py` (0.79); `data/benchmark/auracloud/financials.json` | agent | 2026-10-26 |
| Aura gross margin Q4 2025 ≈ 61% | scenario prose | `tests/test_semantic_metrics.py` (0.61); golden `AURA_001` verified_numbers | agent | 2026-10-26 |
| Aura gross margin delta ≈ −1800 bps (Q1 2024 → Q4 2025) | README scenario | `data/golden_ground_truth.json` `AURA_001` `gross_margin_delta_bps`: -1800; `tests/test_semantic_metrics.py` total_gm_delta_bps ≤ −1500 | agent | 2026-10-26 |
| Nexus Q4 capex YoY growth ≈ 128.6% (42→96M) | golden / transcript | `data/golden_ground_truth.json` `NXUS_001` `capex_growth_yoy`: 1.2857; transcript cites 220% (rounded narrative) | agent | 2026-10-26 |
| Nexus FY2025 FCF total −$144M | golden | `data/golden_ground_truth.json` `NXUS_002` `total_fy2025_fcf`: -144 | agent | 2026-10-26 |
| Synthetix claimed AI ARR $80M; $65M reclassified (81.25%) | scenario | `data/golden_ground_truth.json` `SYNX_001` verified_numbers | agent | 2026-10-26 |
| Vortex control gross margin Q4 2025 ≈ 79.14% | tests | `tests/test_numeric_guardrail.py::test_verify_vortex_clean_control` audited_value > 0.75 | agent | 2026-10-26 |
| pytest suite size (current: 90 tests) | CI / Makefile | `.venv/bin/pytest tests` (90 passed) | agent | 2026-10-28 |
| Local baseline verdict accuracy (76.92%) | eval_results | `scripts/run_golden_eval.py` / `data/eval_results.json` (40/52 cases) | agent | 2026-10-28 |
| Local baseline Brier score (0.1756) | eval_results | `src/eval/calibration.py` / `data/eval_results.json` (Brier 1950) | agent | 2026-10-28 |
| Local baseline Expected Calibration Error (0.0248) | eval_results | `src/eval/calibration.py` / `data/eval_results.json` (Guo et al. 2017) | agent | 2026-10-28 |
| Local baseline Maximum Calibration Error (0.2500) | eval_results | `src/eval/calibration.py` / `data/eval_results.json` (MCE worst-bin) | agent | 2026-10-28 |
| Local baseline Binary Log Loss (0.5336) | eval_results | `src/eval/calibration.py` / `data/eval_results.json` (NLL cross-entropy) | agent | 2026-10-28 |
| Local baseline SAB 99 Materiality Penalty (0.2547) | eval_results | `src/eval/calibration.py` / `data/eval_results.json` (SEC materiality-weighted) | agent | 2026-10-28 |
| Local baseline Adversarial Resistance (100.00%) | eval_results | `scripts/run_golden_eval.py` / `data/eval_results.json` (4/4 corporate directive injections) | agent | 2026-10-28 |
| Public markdown overclaiming grep hits (0) | CI / Makefile | `make grep-gate` / `scripts/grep_gate.sh` (0 hits) | agent | 2026-10-28 |
| AST validation ~1.2 ms per query | docs/decisions.md ADR-01 | `[unverified]` — no benchmark script in repo | — | 2026-10-26 |
| LLM inference 500–2000 ms | removed from README | `[unverified]` — not measured here | — | 2026-10-26 |

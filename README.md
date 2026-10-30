# Multi-Model Evaluation & Decision Benchmarking Harness (`narrative-audit-jev`)
### High-Throughput OpenRouter Benchmarking, Dual-Endpoint Dispatch (`/chat/completions` & `/api/alpha/decisions`), and Empirical Calibration Across Diverse Model Paradigms

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/) [![DuckDB 1.2+](https://img.shields.io/badge/DuckDB-1.2%2B-yellow.svg)](https://duckdb.org/) [![Tests: 112 passed](https://img.shields.io/badge/Tests-112%20passed-brightgreen.svg)](tests/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This repo benchmarks language models on a shared decision task: compare unstructured text to structured ground truth, return a typed verdict with confidence, and score calibration (Brier, ECE, log loss). The OpenRouter client supports chat models (`/chat/completions`) and native decision engines (`/api/alpha/decisions`).

**Illustrative use case:** A **64-case** golden suite checks earnings-call transcripts and footnotes against DuckDB in a **fictional** corporate accounting scenario (omissions, Q&A deflections, segment reclassifications). That setup is a fixed stress test for rules vs models—not the only domain the harness could target. The same stack works for agent output checks, structured-data audits, or any workflow that needs comparable scores across backends.

All figures and dialogue under `data/` are synthetic fixtures. Tickers `AURA`, `NXUS`, `SYNX`, and `VORS` are synthetic benchmark identifiers; they are not intended to identify real issuers. Not a PCAOB/GAAS audit product; not investment, legal, or accounting advice.

---

## Why This Benchmark Exists

The goal is a controlled comparison between **deterministic rules** and **paid API models** on the same labels—without treating regex as if it already catches rhetorical evasion.

* **Structured ground truth:** Quarterly tables load into DuckDB; `make data-check` enforces accounting identities and keyed numbers in `golden_ground_truth.json`.
* **Unstructured claims:** Transcript-derived claims (remarks, Q&A, footnotes) where failures are often evasion, not a wrong number in the sentence.
* **Local baseline:** The rule decider is intentionally de-overfit—it still flags direct numeric mismatches but misses most deflection-only cases (see below).
* **OpenRouter:** One runner pins model IDs, records latency and tokens, and normalizes messy JSON before Pydantic—without separate vendor SDKs.

---

## What I learned

Running and scoring **256** live OpenRouter evaluations (64 golden cases × four evaluators) on Apple Silicon helped me confront several gaps I could not foresee before between a tidy benchmark diagram and what actually happens at the HTTP boundary:

1. **The Meta-Router Trap (Free Tier vs. Pinned Model IDs):**
   What was really revealing to me was how quickly “use the free router” stops being a benchmark and becomes a different task entirely. Early smoke tests hit `openrouter/free`; some requests were steered to safety classifiers (e.g. `nvidia/nemotron-3.5-content-safety`) that returned plain text like `User Safety: safe` instead of a JSON verdict. That looked like a model failure but was really routing noise. Scored runs now pin `deepseek/deepseek-v4.1-flash`, `qwen/qwen3.7-flash`, and `perplexity/pplx-decider-flash-v1.2` at fixed temperature with no meta-routers—otherwise you are not comparing models, you are comparing whatever the router felt like sending.

2. **Queue Time vs. Token Budget (Why I Stopped Trusting Dollar Estimates):**
   I assumed cost per sweep would be the honest comparator across backends. Community free-tier models often sat **45–90 seconds** in queue and still returned HTTP **504**, which made iteration unbearable before spend even mattered. Flash paid endpoints cleared the wall-clock problem: **1.4 s** for all 64 cases on PPLX Decider (median **~5.3k** tokens/case) and **26.4 s** on DeepSeek V4.1 (median **~6.2k** tokens/case), with no dropped requests in that sweep. What I track in the leaderboard now is **mean and median tokens per case**—model-specific pricing changes, but token load is the reproducible stress signal.

3. **Two OpenRouter Surfaces for One Harness (`/chat/completions` vs. `/api/alpha/decisions`):**
   I expected one client wrapper to cover every model slug. Perplexity’s `pplx-decider-flash-v1.2` rejects `/chat/completions` with HTTP **400** and expects `/api/alpha/decisions` with `noul` and `choice` primitives instead of a chat transcript. The fix was not a bigger prompt—it was explicit dual dispatch in `OpenRouterDecisionEvaluator` so chat LLMs and native decision engines share one runner without pretending they share one API shape.

4. **Strict JSON Schemas Still Lie (Normalization Before Pydantic):**
   DeepSeek sometimes returned `"is_discrepant": "false"` (Python-truthy as a string), percent confidences, and qualitative tokens in float fields (`"accelerated"` where a depreciation rate belonged). A long sweep would have died on case 17 without `normalize_decision_dict` and a regex float sanitizer before Pydantic. The lesson for me: schema enforcement on the provider side does not replace defensive parsing on yours when you batch hundreds of calls.

5. **Rules Catch Numbers, Not Rhetoric (The 68.75% vs. 22.2% Split):**
   On the 64-case suite the local rule baseline reached **68.75%** verdict accuracy but only **22.2%** recall on analyst Q&A deflections and footnote reclassifications (**2/9** each)—because the failures are often evasion, not a wrong number in the sentence. The three pinned LLMs hit **100%** recall on deflections in the same run. That gap is exactly what the suite was meant to expose: deterministic guardrails are necessary but not sufficient when the disclosure dodge is qualitative.

6. **Accuracy Hid Calibration Risk (Headline Score vs. Trust in Confidence):**
   DeepSeek led raw accuracy (**90.62%**) but stacked confidence at **0.99–1.00** (ECE **0.0859**). Qwen’s log loss (**0.4762**) punished tail misses harder than DeepSeek (**0.2927**). For this domain, a high-confidence false negative is worse than a modest accuracy drop—what I took away is that calibration metrics belong beside accuracy in any table you would actually ship to a reviewer.

*(Reflective structure and tone aligned with my [quarot-hadamard-gemm](https://github.com/adityavsb/quarot-hadamard-gemm) “What I learned” section; numbers above trace to [`data/results/openrouter/2026-10-29T134211Z/summary.json`](data/results/openrouter/2026-10-29T134211Z/summary.json).)*

---

## Possible Next Steps (Not Shipped)

* Opt-in SEC EDGAR + transcript ingestion (XBRL maintenance cost vs synthetic `make generate-data` today).
* Temperature sweeps and simple post-hoc scaling before comparing ECE across model revisions.
* OpenTelemetry spans on `ClaimExtractor`, `ReadOnlySQLGuardrail`, and `OpenRouterDecisionEvaluator` for multi-machine runs.

---

## Architecture

Deterministic DuckDB checks, an optional local rule path, and OpenRouter evaluators feed one calibration report:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Input Document Corpus                                  │
│   • Synthetic Transcripts / Agent Outputs (Remarks, Explanations, Q&A)                 │
│   • Structured Ground-Truth Tables (Financial Statements, Metrics, System State)       │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              DuckDB Analytical Data Store                              │
│   • Schema & Invariant Identity Validation (Accounting Identities, System Constraints) │
│   • Read-Only AST SQL Security Guardrail (Prevents Mutating Injections)                │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              Claim Extraction & Profiling                              │
│   • Rule Claim Extractor (qualitative statements, metrics, periods)                    │
│   • Numeric guardrail vs quarterly_financials / segment_disclosures                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       Multi-Model Evaluation & Scoring Harness                         │
│                                                                                        │
│   ┌───────────────────────────┐                     ┌──────────────────────────────┐   │
│   │    Local Rule Baseline    │                     │   OpenRouter Multi-Model     │   │
│   │    • LocalDecisionEvaluator                     │   • Dual-endpoint dispatch   │   │
│   │    • ~3 ms / case         │                     │   • /chat/completions        │   │
│   │                           │                     │   • /api/alpha/decisions     │   │
│   └─────────────┬─────────────┘                     └──────────────┬───────────────┘   │
│                 │                                                  │                   │
│                 └─────────────────────────┬────────────────────────┘                   │
│                                           │                                            │
│                                           ▼                                            │
│                     ┌───────────────────────────────────────────┐                      │
│                     │       Defensive Schema Normalizer         │                      │
│                     │  • Regex float sanitizer                  │                      │
│                     │  • Boolean string coercion                │                      │
│                     │  • Category alias mapping                 │                      │
│                     └─────────────────────┬─────────────────────┘                      │
└───────────────────────────────────────────┼────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             Calibration & Metric Engine                                │
│   • Verdict & divergence accuracy                                                      │
│   • Brier, ECE, MCE, binary log loss, SAB 99–style materiality penalty                 │
│   • Category breakdowns (Q&A deflection, footnotes, injections)                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Component detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Maintainer notes and trade-offs: [NOTES.md](NOTES.md).

---

## Measured Benchmark Telemetry & Comparative Leaderboard

Scores below are from the **64-case** golden suite across four synthetic profiles (AuraCloud, NexusEnterprise, Synthetix, Vortex control). Tracked evidence: [data/results/openrouter/2026-10-29T134211Z/summary.json](data/results/openrouter/2026-10-29T134211Z/summary.json) (imported from a local sweep; no API rerun). [CLAIMS.md](CLAIMS.md) lists verification metadata. Token columns are **prompt + completion tokens per case** (mean and median over 64 cases); local baseline uses no LLM tokens.

### 1. Comparative Performance Leaderboard

| Model / Evaluator | Verdict Accuracy | Divergence Accuracy | Brier Score | ECE (Calib.) | Binary Log Loss | Q&A Deflection Recall | Footnote Reclass Recall | Mean Latency | Avg Tokens / Case | Median Tokens / Case |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Local Rule Baseline** | 68.75% | 68.75% | 0.2186 | 0.1103 | 0.6293 | 22.2% (2/9) | 22.2% (2/9) | **3.1 ms** | **0** | **0** |
| **`deepseek/deepseek-v4.1-flash`** | **90.62%** | **89.06%** | **0.0845** | **0.0859** | **0.2927** | **100.0% (9/9)** | **88.9% (8/9)** | 26.4 s | 6,639 | 6,168 |
| **`perplexity/pplx-decider-flash-v1.2`** | 85.94% | 84.38% | 0.1263 | 0.1396 | 0.3681 | **100.0% (9/9)** | **88.9% (8/9)** | **1.4 s** | **5,284** | **5,308** |
| **`qwen/qwen3.7-flash`** | 84.38% | 79.69% | 0.1387 | 0.1420 | 0.4762 | **100.0% (9/9)** | 77.8% (7/9) | 38.5 s | 6,580 | 6,462 |

Raw aggregates and per-case predictions: [data/results/openrouter/2026-10-29T134211Z/](data/results/openrouter/2026-10-29T134211Z/) (`summary.json`, `predictions/*.json`, `manifest.json`, `SHA256SUMS`). Maintainers with local checkpoints under `data/eval_runs/` can refresh the bundle via `make package-openrouter-results` (raw eval output stays local-only).

### 2. Breakdown by Evaluated Claim Category

| Category | Total Cases | Local Rule Engine | DeepSeek V4.1 Flash | PPLX Decider Flash | Qwen 3.7 Flash |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Factual Disclosure** | 16 | **100.0%** (16/16) | 87.5% (14/16) | 93.8% (15/16) | 68.8% (11/16) |
| **Trend Synthesis** | 12 | 75.0% (9/12) | 75.0% (9/12) | 66.7% (8/12) | 75.0% (9/12) |
| **Segment Analysis (Footnotes)** | 9 | 22.2% (2/9) | **88.9%** (8/9) | **88.9%** (8/9) | 77.8% (7/9) |
| **Analyst Q&A Deflection** | 9 | 22.2% (2/9) | **100.0%** (9/9) | **100.0%** (9/9) | **100.0%** (9/9) |
| **Discrepancy Classification** | 5 | 80.0% (4/5) | **100.0%** (5/5) | **100.0%** (5/5) | **100.0%** (5/5) |
| **Control Non-Discrepancy** | 5 | **100.0%** (5/5) | **100.0%** (5/5) | **100.0%** (5/5) | 80.0% (4/5) |
| **Boundary Edge Case** | 4 | 50.0% (2/4) | **75.0%** (3/4) | 25.0% (1/4) | 50.0% (2/4) |
| **Adversarial Injection** | 4 | **100.0%** (4/4) | **100.0%** (4/4) | 75.0% (3/4) | **100.0%** (4/4) |

### 3. Failure Modes (Full Sweep)

* **Local rule baseline:** Strong on direct line-item checks and corporate-framed prompt injections (4/4). Weak when rhetoric dodges the number—7/9 misses on deflection and footnote categories.
* **DeepSeek V4.1 Flash:** Highest accuracy and lowest Brier; most errors were boundary cases where guidance overlapped actuals inside encoded tolerance.
* **PPLX Decider Flash v1.2:** Fastest wall clock and lowest median tokens per case (~5.3k); matched DeepSeek on deflections but missed one injection case and one of four boundary cases.
* **Qwen 3.7 Flash:** Solid on deflections and injections; extra false positives on factual disclosure (11/16) pulled divergence accuracy down.

---

## Benchmark Environment & Hardware Provenance

| Item | Value |
|------|--------|
| Host | Apple Silicon arm64 (Darwin 24.x) |
| Python | 3.13.2 |
| DuckDB | 1.2.0 (in-memory via `get_default_db()`) |
| OpenRouter | `/api/v1/chat/completions`, `/api/alpha/decisions` |
| Tests | 112 pytest cases (`make test`) |
| Golden set | 64 cases (`make data-check`) |

---

## Quickstart & Reproducibility

### 1. Install

```bash
git clone https://github.com/adityavsb/narrative-audit-jev.git
cd narrative-audit-jev
make install
```

### 2. Verify tests and fixtures

```bash
make test
make data-check
```

### 3. Local rule baseline (no API key)

```bash
make eval-golden
```

Writes [data/eval_results.json](data/eval_results.json) for `LocalDecisionEvaluator`.

### 4. OpenRouter sweep (API key required)

Copy [.env.example](.env.example) to `.env`, set `OPENROUTER_API_KEY`, then:

```bash
make check-model-1       # Model 1 smoke on AURA_001
make check-models-2-3    # Models 2 & 3 smoke on the same case
make eval-openrouter     # Full 64-case sweep (local baseline + 3 models)
```

Model IDs: `OPENROUTER_MODEL_1` / `_2` / `_3` in `.env`, or `--model1`, `--model2`, `--model3` on [scripts/run_openrouter_eval.py](scripts/run_openrouter_eval.py). After a local sweep, run `make package-openrouter-results` to publish a redacted bundle under `data/results/openrouter/`.

### 5. Prose register check

```bash
make grep-gate
```

---

## Repository Layout

```
narrative-audit-jev/
├── Makefile
├── pyproject.toml
├── README.md
├── CLAIMS.md
├── NOTES.md
├── REFERENCES.bib
├── CITATION.cff
├── docs/
│   ├── ARCHITECTURE.md
│   └── decisions.md
├── src/
│   ├── agents/           claim_extractor, numeric_guardrail, text2sql_agent, state
│   ├── db/               schema, loaders, generators, semantic_metrics
│   ├── eval/             calibration metrics
│   ├── evaluators/       local_decider, openrouter_decider, jev_decision
│   └── security/         sql_guardrail, audit_logger, leakage_verifier
├── data/
│   ├── benchmark/        four synthetic company JSON bundles
│   ├── sample_fixture/   smaller CI fixture
│   ├── golden_ground_truth.json
│   └── eval_results.json # from make eval-golden
├── scripts/
│   ├── run_golden_eval.py
│   ├── run_openrouter_eval.py
│   ├── grep_gate.sh
│   └── record_metrics.sh
└── tests/
```

---

## Scope, Non-Goals, and Limitations

* **Synthetic only:** No live SEC ingestion; fixtures regenerate via `make generate-data`.
* **Fictional identifiers:** Company names, tickers (`AURA`, `NXUS`, `SYNX`, `VORS`), speaker names, dialogue, and all numeric fixtures are **generated for this benchmark**. They are not intended to represent, refer to, or target any real person, issuer, security, product, or event.
* **Coincidental resemblance:** If any synthetic label, figure, or narrative happens to match (in whole or in part) a real ticker, company name, filing, or market data point, that overlap is **coincidental**. We do not claim accuracy against, affiliation with, or endorsement by any real entity, and we have not verified clearance against exchange listings, trademarks, or other registries.
* **No reliance / no liability:** This repository is experimental research tooling. Do not use it for investment, trading, credit, employment, or compliance decisions. The authors and contributors provide it **as is**, without warranty, and accept **no responsibility or liability** for errors, omissions, or any use of the synthetic corpus or benchmark outputs.
* **Not professional services:** Experimental benchmark tooling—not an audit opinion or compliance product.
* **Model drift:** Upstream slugs change; `run_openrouter_eval.py` checkpoints support replay without new API spend.
* **Single-quarter focus:** Most cases are one quarter or trailing-four logic; multi-year tax and deferred-revenue schedules are out of scope.

---

## References & Scientific Attribution

See [`REFERENCES.bib`](REFERENCES.bib) and [`CITATION.cff`](CITATION.cff).

1. **Loughran, T., & McDonald, B. (2011).** *When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks.* The Journal of Finance, 66(1), 35–65.
2. **Securities and Exchange Commission (1999).** *Staff Accounting Bulletin No. 99 — Materiality.* SEC Docket, 70(11), 785–791.
3. **Brier, G. W. (1950).** *Verification of Forecasts Expressed in Terms of Probability.* Monthly Weather Review, 78(1), 1–3.
4. **Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017).** *On Calibration of Modern Neural Networks.* ICML 2017, PMLR 70, 1321–1330.
5. **Landis, J. R., & Koch, G. G. (1977).** *The Measurement of Observer Agreement for Categorical Data.* Biometrics, 33(1), 159–174.

---

## License

[MIT License](LICENSE).

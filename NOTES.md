# Working notes

Dated, first-person record of decisions and corrections. Newest first. These are notes, not user documentation; see [README.md](README.md) for how to run the project.

## 2026-10 — Authorship remediation

### Decisions

<!-- HUMAN: One bullet per decision — date, what you chose, why, what changed (cite metrics_log.csv row or commit). Prompts: why synthetic 4-company benchmark; why rule-based ClaimExtractor vs LLM; why DuckDB in-memory; why AST sql guardrail. -->

### Things I got wrong

<!-- HUMAN: e.g. single-commit initial dump; README described JEV/orchestrator as if shipped; make data-check had no --validate; margin guardrail skipped CONTRACTION/NEUTRAL claims. Say how each was caught. -->

### Dead ends

<!-- HUMAN: margin guardrail optimism-only path — see notebooks/01_margin_guardrail_polarity.ipynb and baseline_dee729f/. One number that killed the old approach. -->

### Open questions

<!-- HUMAN: at least two — e.g. worth building JEV evaluator on this corpus? live EDGAR connector scope? golden cases vs end-to-end agent eval? -->

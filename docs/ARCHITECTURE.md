# Architecture (as shipped)

Research harness over a **synthetic** DuckDB corpus (fictional tickers `AURA`, `NXUS`, `SYNX`, `VORS`). The repo benchmarks **local rule baselines** and **OpenRouter-backed models** on a **64-case** golden suite (`data/golden_ground_truth.json`).

## End-to-end flow

```
data/benchmark/*.json  →  FinancialDatabase (DuckDB)
                              ↓
         transcripts / claims context for each golden case
                              ↓
    ┌─────────────────────────┴─────────────────────────┐
    │                                                     │
LocalDecisionEvaluator                    OpenRouterDecisionEvaluator
(rule pipeline below)                     (XML sandbox prompt + API)
    │                                                     │
    └─────────────────────────┬─────────────────────────┘
                              ↓
              AuditVerdict (typed Pydantic)
                              ↓
     scripts/run_golden_eval.py  |  scripts/run_openrouter_eval.py
                              ↓
     src/eval/calibration.py (Brier, ECE, MCE, NLL, SAB 99, …)
                              ↓
     data/eval_results.json  |  OpenRouter bundles under data/results/openrouter/ (see manifest)
```

### Deterministic claim pipeline (local baseline)

1. JSON fixtures under `data/benchmark/` load via [src/db/schema.py](../src/db/schema.py) (`--validate` checks identities and golden reconciliation).
2. [src/agents/claim_extractor.py](../src/agents/claim_extractor.py) reads transcript text and emits typed claims (regex + word boundaries, negation window).
3. [src/agents/numeric_guardrail.py](../src/agents/numeric_guardrail.py) reconciles claims against `quarterly_financials` and `segment_disclosures` (multi-period baseline fallback for early-year gaps).
4. [src/agents/text2sql_agent.py](../src/agents/text2sql_agent.py) runs templated SQL through [src/security/sql_guardrail.py](../src/security/sql_guardrail.py) (read-only AST + table allowlist).
5. [src/evaluators/local_decider.py](../src/evaluators/local_decider.py) composes extraction, guardrails, macro flags, and directive neutralization into a single `AuditVerdict` per golden case (~68.75% verdict accuracy on 64 cases; weak on analyst Q&A deflection and footnote reclassification).

### Multi-model evaluation (OpenRouter)

- [src/evaluators/openrouter_decider.py](../src/evaluators/openrouter_decider.py): sandboxed prompts, dual dispatch to `/api/v1/chat/completions` and `/api/alpha/decisions`, `normalize_decision_dict` for heterogeneous JSON, float sanitization on fact-check fields.
- [src/evaluators/jev_decision.py](../src/evaluators/jev_decision.py): facade that uses `LocalDecisionEvaluator` by default or delegates to OpenRouter when `OPENROUTER_API_KEY` and a model id are set.
- [scripts/run_openrouter_eval.py](../scripts/run_openrouter_eval.py): staged CLI (`check-one`, `check-remaining`, `full`) with per-case JSON checkpoints under local `data/eval_runs/`.
- [scripts/package_openrouter_results.py](../scripts/package_openrouter_results.py): redacts local checkpoints into tracked `data/results/openrouter/<run-id>/`.
- [src/security/leakage_verifier.py](../src/security/leakage_verifier.py): scans for accidental secret patterns before eval runs.

There is **no** multi-agent orchestrator, live SEC EDGAR connector, or NDI dossier generator ([TODO.md](../TODO.md)).

## Tracked source layout

```
src/db/              schema, loaders, generators, financial_queries, semantic_metrics
src/agents/          state, claim_extractor, numeric_guardrail, text2sql_agent
src/security/        sql_guardrail, audit_logger, leakage_verifier
src/eval/            calibration metrics (Brier, ECE, log loss, materiality loss, …)
src/evaluators/      local_decider, openrouter_decider, jev_decision
src/connectors/      README only (EDGAR not implemented)
scripts/             run_golden_eval.py, run_openrouter_eval.py, grep_gate.sh, record_metrics.sh
tests/               pytest suite (105 tests)
data/benchmark/      four company fixtures
data/golden_ground_truth.json   64 labeled cases
data/eval_results.json          local rule baseline output (from make eval-golden)
```

## Validation entrypoints

| Command | Purpose |
|---------|---------|
| `make test` | Unit and integration tests (105). |
| `make data-check` | `python -m src.db.schema --validate` (64 golden cases). |
| `make eval-golden` | Local rule baseline over all golden cases + calibration report. |
| `make check-model-1` / `check-models-2-3` | OpenRouter smoke stages on one case. |
| `make eval-openrouter` | Full multi-model sweep (requires `.env`; local checkpoints under `data/eval_runs/`). |
| `make package-openrouter-results` | Publish redacted bundle to `data/results/openrouter/`. |
| `make grep-gate` | Prose register check for public docs. |
| `make metrics` | Append row to [metrics_log.csv](../metrics_log.csv). |

See [docs/decisions.md](decisions.md) for ADRs on SQL guardrails, typed evaluators, benchmark scale, and OpenRouter dispatch.

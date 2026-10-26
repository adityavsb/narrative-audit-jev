# Architecture (as shipped)

Research harness over a **synthetic** DuckDB corpus. Fictional companies only.

## Data flow

1. JSON fixtures under `data/benchmark/` (and `data/sample_fixture/` for CI) load via [src/db/schema.py](../src/db/schema.py).
2. [src/agents/claim_extractor.py](../src/agents/claim_extractor.py) reads `transcripts` rows and emits typed claims (rule-based patterns).
3. [src/agents/numeric_guardrail.py](../src/agents/numeric_guardrail.py) reconciles claims against `quarterly_financials` and `segment_disclosures`.
4. [src/agents/text2sql_agent.py](../src/agents/text2sql_agent.py) runs templated/heuristic SQL through [src/security/sql_guardrail.py](../src/security/sql_guardrail.py) (read-only AST).
5. [src/db/semantic_metrics.py](../src/db/semantic_metrics.py) computes margin/capex/reclassification flags for tests and exploration.

There is **no** multi-agent orchestrator, JEV evaluator, or dossier generator in this tree yet ([TODO.md](../TODO.md)).

## Tracked source layout

```
src/db/           schema, loaders, generators, financial_queries, semantic_metrics
src/agents/       state, claim_extractor, numeric_guardrail, text2sql_agent
src/security/     sql_guardrail, audit_logger, leakage_verifier
src/connectors/   README only (EDGAR not implemented)
tests/            pytest suite
data/benchmark/   four company fixtures
data/golden_ground_truth.json   52 labeled claims (metadata; not auto-scored end-to-end)
```

## Validation entrypoints

- `make test` — unit and integration tests.
- `make data-check` — `python -m src.db.schema --validate` (identities + golden case checks).
- `make metrics` — append a row to [metrics_log.csv](../metrics_log.csv).

See [docs/decisions.md](decisions.md) for ADRs on SQL guardrails and (planned) JEV methodology.
